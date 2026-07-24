FROM python:3.12-slim

WORKDIR /srv/secondopinion

# Install dependencies first so code changes don't bust this layer.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

# Run as a non-root user; the data dir holds the SQLite file and model cache.
RUN useradd --create-home secondopinion \
    && mkdir -p /srv/secondopinion/data \
    && chown -R secondopinion:secondopinion /srv/secondopinion
USER secondopinion

ENV SECONDOPINION_DATABASE_URL=sqlite:////srv/secondopinion/data/secondopinion.db \
    HF_HOME=/srv/secondopinion/data/hf-cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
