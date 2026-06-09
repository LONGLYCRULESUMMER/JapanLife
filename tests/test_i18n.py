from core.i18n import detect_language


def test_japanese_text():
    assert detect_language("確定申告について教えてください") == "ja"


def test_english_text():
    assert detect_language("How do I file my taxes?") == "en"


def test_empty_is_english():
    assert detect_language("") == "en"


def test_mixed_with_japanese_majority():
    assert detect_language("e-Taxの使い方") == "ja"
