import json

from app.models import Experience
from app.services.retrieval_service import RetrievalService


def make_experience(experience_id: int, embedding: list[float] | None) -> Experience:
    return Experience(
        id=experience_id,
        task=f"Task {experience_id}",
        proposed_action=f"Action {experience_id}",
        tool_name="browser",
        embedding=json.dumps(embedding) if embedding is not None else None,
    )


def test_returns_at_most_limit_results() -> None:
    query = [1.0, 0.0, 0.0]
    experiences = [make_experience(i, [1.0, 0.0, 0.0]) for i in range(1, 11)]
    results = RetrievalService(min_similarity=0.0).find_similar(query, experiences, limit=3)
    assert len(results) == 3


def test_results_ordered_by_similarity_descending() -> None:
    query = [1.0, 0.0]
    experiences = [
        make_experience(1, [0.6, 0.8]),   # cos = 0.6
        make_experience(2, [1.0, 0.0]),   # cos = 1.0
        make_experience(3, [0.8, 0.6]),   # cos = 0.8
    ]
    results = RetrievalService(min_similarity=0.0).find_similar(query, experiences, limit=5)
    assert [r.experience.id for r in results] == [2, 3, 1]
    similarities = [r.similarity for r in results]
    assert similarities == sorted(similarities, reverse=True)


def test_empty_experience_list_returns_empty() -> None:
    results = RetrievalService().find_similar([1.0, 0.0], [], limit=5)
    assert results == []


def test_experiences_without_embeddings_are_skipped() -> None:
    experiences = [make_experience(1, None), make_experience(2, [1.0, 0.0])]
    results = RetrievalService(min_similarity=0.0).find_similar([1.0, 0.0], experiences, limit=5)
    assert [r.experience.id for r in results] == [2]


def test_min_similarity_threshold_filters_low_matches() -> None:
    query = [1.0, 0.0]
    experiences = [
        make_experience(1, [1.0, 0.0]),    # cos = 1.0
        make_experience(2, [0.0, 1.0]),    # cos = 0.0
        make_experience(3, [-1.0, 0.0]),   # cos = -1.0
    ]
    results = RetrievalService(min_similarity=0.5).find_similar(query, experiences, limit=5)
    assert [r.experience.id for r in results] == [1]


def test_duplicate_experiences_share_similarity() -> None:
    query = [1.0, 0.0]
    experiences = [make_experience(1, [1.0, 0.0]), make_experience(2, [1.0, 0.0])]
    results = RetrievalService(min_similarity=0.0).find_similar(query, experiences, limit=5)
    assert len(results) == 2
    assert results[0].similarity == results[1].similarity


def test_zero_query_vector_returns_empty() -> None:
    experiences = [make_experience(1, [1.0, 0.0])]
    results = RetrievalService(min_similarity=0.0).find_similar([0.0, 0.0], experiences, limit=5)
    assert results == []


def test_zero_stored_vector_is_not_matched() -> None:
    experiences = [make_experience(1, [0.0, 0.0]), make_experience(2, [1.0, 0.0])]
    results = RetrievalService(min_similarity=0.1).find_similar([1.0, 0.0], experiences, limit=5)
    assert [r.experience.id for r in results] == [2]
