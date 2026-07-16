import uuid

from app.services.retrieval_service import reciprocal_rank_fusion


def test_rrf_merges_ranked_lists():
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()
    scores = reciprocal_rank_fusion([[a, b], [b, c]])
    assert scores[b] > scores[a]
    assert scores[b] > scores[c]
