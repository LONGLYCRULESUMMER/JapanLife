def test_get_llm_uses_configured_model(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    from core.llm import get_llm
    llm = get_llm()
    name = getattr(llm, "model_name", None) or getattr(llm, "model", "")
    assert "deepseek" in name.lower()


def test_get_llm_override(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    from core.llm import get_llm
    llm = get_llm(model="deepseek-reasoner")
    name = getattr(llm, "model_name", None) or getattr(llm, "model", "")
    assert name == "deepseek-reasoner"
