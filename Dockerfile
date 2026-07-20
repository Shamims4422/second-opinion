FROM python:3.12-slim

WORKDIR /srv/criticloop

# Install dependencies first so code changes don't bust this layer.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

# Run as a non-root user; the data dir holds the SQLite file and model cache.
RUN useradd --create-home criticloop \
    && mkdir -p /srv/criticloop/data \
    && chown -R criticloop:criticloop /srv/criticloop
USER criticloop

ENV CRITICLOOP_DATABASE_URL=sqlite:////srv/criticloop/data/criticloop.db \
    HF_HOME=/srv/criticloop/data/hf-cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
