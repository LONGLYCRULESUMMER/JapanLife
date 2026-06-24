from eval.metrics import mrr, recall_at_k


def test_recall_at_k_full_hit():
    assert recall_at_k(retrieved=["d1", "d2", "d3"], relevant={"d2"}, k=3) == 1.0


def test_recall_at_k_miss_outside_k():
    assert recall_at_k(retrieved=["d1", "d2", "d3"], relevant={"d3"}, k=2) == 0.0


def test_recall_at_k_partial():
    r = recall_at_k(retrieved=["d1", "d2"], relevant={"d1", "d9"}, k=2)
    assert r == 0.5


def test_mrr_first_relevant_at_rank_2():
    assert mrr(retrieved=["x", "d1"], relevant={"d1"}) == 0.5


def test_mrr_no_hit_is_zero():
    assert mrr(retrieved=["x", "y"], relevant={"d1"}) == 0.0
