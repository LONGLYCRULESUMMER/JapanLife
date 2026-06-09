from core.config import Settings


def test_defaults_without_env_file():
    s = Settings(_env_file=None)
    assert s.index_name == "japanlife_kb"
    assert s.embedding_dim == 1024
    assert s.rrf_k == 60


def test_override_via_kwargs():
    s = Settings(_env_file=None, es_url="http://es:9200")
    assert s.es_url == "http://es:9200"
