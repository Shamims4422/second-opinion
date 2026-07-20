"""Seed the local database with example experiences and outcomes.

Run from the repository root (embeds with the real local model, so the first
run downloads it once):

    python scripts/seed_database.py
"""

import json

from app.database import Base, SessionLocal, engine
from app.models import Experience, Outcome
from app.services.embedding_service import build_embedding_text, get_embedding_service

# (task, proposed_action, tool_name, was_successful, outcome, failure_reason)
SEED_EXPERIENCES: list[tuple[str, str, str, bool, str, str | None]] = [
    # Browser — sponsored results, forms, downloads, comparisons, filters
    ("Find the cheapest nonstop flight to Chicago", "Click the first sponsored flight result",
     "browser", False, "The selected flight had one stop.",
     "Sponsored result ignored the nonstop requirement."),
    ("Find the cheapest nonstop flight to Denver", "Click the first sponsored flight result",
     "browser", False, "The sponsored fare was $120 above the cheapest option.",
     "Sponsored results are not sorted by price."),
    ("Find the cheapest nonstop flight to Boston", "Apply the nonstop filter, then sort by price",
     "browser", True, "Found the cheapest nonstop fare.", None),
    ("Book a hotel under $150 per night", "Click the first sponsored hotel listing",
     "browser", False, "The listing was $210 per night.",
     "Sponsored listing did not respect the price constraint."),
    ("Book a hotel under $150 per night", "Set the max-price filter to $150 and sort ascending",
     "browser", True, "Booked a $132 hotel.", None),
    ("Sign up for the newsletter", "Fill the signup form and submit",
     "browser", True, "Confirmation email received.", None),
    ("Submit a support request", "Submit the contact form without filling required fields",
     "browser", False, "The form showed validation errors.",
     "Required fields were left empty."),
    ("Download the quarterly report PDF", "Click the download link on the official reports page",
     "browser", True, "Report downloaded successfully.", None),
    ("Download the installer", "Click a download button inside a banner ad",
     "browser", False, "The button led to an unrelated site.",
     "Clicked an advertisement instead of the real download link."),
    ("Compare laptop prices across two retailers", "Open both product pages in tabs and compare",
     "browser", True, "Recorded both prices accurately.", None),
    ("Find a highly rated coffee grinder", "Sort search results by average rating",
     "browser", True, "Top result had 4.8 stars across 2k reviews.", None),
    ("Find running shoes on sale", "Click the first result without checking the discount",
     "browser", False, "The item was full price.",
     "Did not verify the sale condition before selecting."),

    # Filesystem — deleting, renaming, overwriting, reading configs
    ("Free disk space in the project folder", "Delete the node_modules directory",
     "filesystem", True, "Reclaimed 800 MB.", None),
    ("Free disk space quickly", "Delete the entire Documents folder",
     "filesystem", False, "Important files were lost.",
     "Deletion target was far too broad."),
    ("Organize photo files", "Rename files to a date-based naming scheme",
     "filesystem", True, "All 240 photos renamed consistently.", None),
    ("Update the app configuration", "Overwrite config.json without a backup",
     "filesystem", False, "Previous settings were unrecoverable after a typo.",
     "No backup existed before the overwrite."),
    ("Update the app configuration", "Copy config.json to config.json.bak, then edit",
     "filesystem", True, "Change applied; backup retained.", None),
    ("Read the database connection settings", "Open and parse settings.ini",
     "filesystem", True, "Settings parsed correctly.", None),
    ("Clean up temporary files", "Delete files matching *.tmp in the temp directory",
     "filesystem", True, "Removed 312 temporary files.", None),
    ("Archive old logs", "Move logs older than 30 days into archive/",
     "filesystem", True, "Forty log files archived.", None),
    ("Fix a corrupted cache", "Delete the application cache folder while the app was running",
     "filesystem", False, "The application crashed.",
     "Files were locked by the running process."),

    # Shell — installs, tests, deletions, environment variables
    ("Install project dependencies", "Run pip install -r requirements.txt in the venv",
     "shell", True, "All packages installed.", None),
    ("Install a system package", "Run the install command with sudo piped from a website",
     "shell", False, "The script modified unrelated system files.",
     "Executed an untrusted remote script."),
    ("Run the unit test suite", "Run pytest in the project root",
     "shell", True, "All tests passed.", None),
    ("Run a single failing test", "Run pytest with the node id of the failing test",
     "shell", True, "Reproduced the failure in isolation.", None),
    ("Remove the build directory", "Run rm -rf ./build from the project root",
     "shell", True, "Build directory removed.", None),
    ("Remove build artifacts", "Run rm -rf with a path containing an unquoted variable",
     "shell", False, "The command deleted files outside the project.",
     "Unquoted empty variable expanded to the filesystem root."),
    ("Set the API base URL for development", "Export the variable in the current shell session",
     "shell", True, "Application picked up the new value.", None),
    ("Persist an environment variable", "Edit the shell profile and reload it",
     "shell", True, "Variable available in new sessions.", None),
    ("Upgrade all packages at once", "Run a bulk upgrade without pinning versions",
     "shell", False, "A breaking dependency upgrade broke the build.",
     "No version constraints were applied."),
    ("Check disk usage", "Run du with a human-readable flag on the project folder",
     "shell", True, "Usage summary produced.", None),

    # Email — sending, group replies, attachments, recipients
    ("Send the weekly status update", "Email the status summary to the team list",
     "email", True, "Update delivered to the team.", None),
    ("Reply to a client question", "Reply-all to a thread including external recipients",
     "email", False, "Internal notes were exposed to the client.",
     "Reply-all included unintended recipients."),
    ("Reply to a client question", "Reply only to the client with the answer",
     "email", True, "Client confirmed the answer helped.", None),
    ("Share the quarterly report", "Attach the report PDF and send to the finance list",
     "email", True, "Report received by finance.", None),
    ("Share a large video file", "Attach a 2 GB file directly to the email",
     "email", False, "The message bounced.",
     "Attachment exceeded the size limit."),
    ("Share a large video file", "Upload the file to shared storage and email the link",
     "email", True, "Recipients accessed the file via the link.", None),
    ("Invite the team to the planning meeting", "Send a calendar invite to the team alias",
     "email", True, "All members received the invite.", None),
    ("Email the contract to the vendor", "Send to an address typed from memory",
     "email", False, "The contract went to the wrong person.",
     "Recipient address was not verified."),
    ("Email the contract to the vendor", "Send to the address from the vendor record",
     "email", True, "Vendor confirmed receipt.", None),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    embedder = get_embedding_service()
    db = SessionLocal()
    try:
        existing = db.query(Experience).count()
        if existing:
            print(f"Database already has {existing} experiences; nothing seeded.")
            return

        for task, action, tool, success, outcome_text, failure_reason in SEED_EXPERIENCES:
            embedding = embedder.embed(build_embedding_text(task, action))
            experience = Experience(
                task=task,
                proposed_action=action,
                tool_name=tool,
                embedding=json.dumps(embedding),
                status="completed",
            )
            db.add(experience)
            db.flush()
            db.add(
                Outcome(
                    experience_id=experience.id,
                    was_successful=success,
                    outcome_description=outcome_text,
                    failure_reason=failure_reason,
                )
            )
        db.commit()
        print(f"Seeded {len(SEED_EXPERIENCES)} experiences with outcomes.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
