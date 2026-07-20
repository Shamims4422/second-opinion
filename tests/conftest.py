import zlib
from collections.abc import Generator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.embedding_service import get_embedding_service


class FakeEmbeddingService:
    """Deterministic bag-of-words embedding: texts sharing words get high cosine
    similarity. Keeps tests offline — no model download, no network."""

    DIMENSIONS = 64
    # Boilerplate from build_embedding_text; skipped so unrelated texts score ~0.
    STOPWORDS = {"task:", "action:"}

    def embed(self, text: str) -> list[float]:
        vector = np.zeros(self.DIMENSIONS)
        for word in text.lower().split():
            if word in self.STOPWORDS:
                continue
            vector[zlib.crc32(word.encode()) % self.DIMENSIONS] += 1.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return [float(v) for v in vector]


@pytest.fixture
def fake_embedder() -> FakeEmbeddingService:
    return FakeEmbeddingService()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(
    db_session: Session, fake_embedder: FakeEmbeddingService
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = lambda: fake_embedder
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
