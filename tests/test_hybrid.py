from rag.hybrid import fuse, reciprocal_rank_fusion


def test_rrf_scores_first_rank_highest():
    scores = reciprocal_rank_fusion([["a", "b", "c"]], k=60)
    assert scores["a"] > scores["b"] > scores["c"]
    assert scores["a"] == 1 / 61


def test_rrf_rewards_appearing_in_both_lists():
    scores = reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=60)
    assert round(scores["a"], 6) == round(scores["b"], 6)


def test_fuse_merges_payloads_and_orders():
    es_hits = [("a", 9.0, {"content": "A"}), ("c", 5.0, {"content": "C"})]
    qd_hits = [("a", 0.9, {"content": "A"}), ("b", 0.8, {"content": "B"})]
    fused = fuse(es_hits, qd_hits, k=60)
    ids = [cid for cid, _, _ in fused]
    assert ids[0] == "a"
    assert set(ids) == {"a", "b", "c"}
    payload_a = next(pl for cid, _, pl in fused if cid == "a")
    assert payload_a["content"] == "A"
