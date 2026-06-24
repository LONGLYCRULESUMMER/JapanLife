import pytest
from elasticsearch import Elasticsearch

from core.config import settings


@pytest.fixture(scope="session")
def es_client():
    client = Elasticsearch(hosts=[settings.es_url])
    try:
        if not client.ping():
            pytest.skip("ElasticSearch not reachable")
    except Exception:
        pytest.skip("ElasticSearch not reachable")
    return client
