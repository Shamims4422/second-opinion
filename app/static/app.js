const evaluateForm = document.getElementById("evaluate-form");
const evaluateButton = document.getElementById("evaluate-button");
const evaluateError = document.getElementById("evaluate-error");

const resultCard = document.getElementById("result-card");
const decisionBadge = document.getElementById("decision-badge");
const confidenceFill = document.getElementById("confidence-fill");
const confidenceLabel = document.getElementById("confidence-label");
const reasonEl = document.getElementById("reason");
const evidenceSummary = document.getElementById("evidence-summary");
const similarTable = document.getElementById("similar-table");
const similarBody = document.getElementById("similar-body");

const outcomeCard = document.getElementById("outcome-card");
const outcomeForm = document.getElementById("outcome-form");
const outcomeButton = document.getElementById("outcome-button");
const outcomeMessage = document.getElementById("outcome-message");
const outcomeError = document.getElementById("outcome-error");
const outcomeExperienceId = document.getElementById("outcome-experience-id");

let currentExperienceId = null;

async function readError(response) {
  try {
    const body = await response.json();
    if (body.error) return body.error.message;
    if (body.detail) return JSON.stringify(body.detail);
  } catch {
    /* fall through */
  }
  return `Request failed with status ${response.status}.`;
}

evaluateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  evaluateError.hidden = true;
  evaluateButton.disabled = true;

  const data = Object.fromEntries(new FormData(evaluateForm));
  if (!data.environment_context) delete data.environment_context;

  try {
    const response = await fetch("/api/v1/evaluations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(await readError(response));
    renderResult(await response.json());
  } catch (err) {
    evaluateError.textContent = err.message;
    evaluateError.hidden = false;
  } finally {
    evaluateButton.disabled = false;
  }
});

function renderResult(result) {
  resultCard.hidden = false;

  decisionBadge.textContent = result.decision;
  decisionBadge.className = `badge ${result.decision}`;

  const pct = Math.round(result.confidence * 100);
  confidenceFill.style.width = `${pct}%`;
  confidenceLabel.textContent = `${pct}% confidence`;

  reasonEl.textContent = result.reason;
  evidenceSummary.textContent =
    `Evidence: ${result.evidence_count} experience(s) with recorded outcomes · ` +
    `scoring ${result.scoring_version}`;

  similarBody.innerHTML = "";
  similarTable.hidden = result.similar_experiences.length === 0;
  for (const item of result.similar_experiences) {
    const row = document.createElement("tr");
    const outcomeText =
      item.was_successful === null
        ? "no outcome yet"
        : item.was_successful
          ? "succeeded"
          : "failed";
    const outcomeClass =
      item.was_successful === null ? "muted" : item.was_successful ? "ok" : "fail";
    row.innerHTML =
      `<td>#${item.experience_id}</td>` +
      `<td>${(item.similarity * 100).toFixed(1)}%</td>` +
      `<td class="${outcomeClass}">${outcomeText}</td>`;
    similarBody.appendChild(row);
  }

  currentExperienceId = result.experience_id;
  outcomeExperienceId.textContent = currentExperienceId;
  outcomeCard.hidden = false;
  outcomeMessage.hidden = true;
  outcomeError.hidden = true;
  outcomeForm.reset();
  outcomeButton.disabled = false;
}

outcomeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (currentExperienceId === null) return;
  outcomeError.hidden = true;
  outcomeButton.disabled = true;

  const form = new FormData(outcomeForm);
  const payload = { was_successful: form.get("was_successful") === "true" };
  if (form.get("outcome")) payload.outcome = form.get("outcome");
  if (form.get("failure_reason")) payload.failure_reason = form.get("failure_reason");

  try {
    const response = await fetch(`/api/v1/experiences/${currentExperienceId}/outcome`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await readError(response));
    outcomeMessage.textContent =
      "Outcome recorded. Future evaluations of similar actions will use it.";
    outcomeMessage.hidden = false;
  } catch (err) {
    outcomeError.textContent = err.message;
    outcomeError.hidden = false;
    outcomeButton.disabled = false;
  }
});
