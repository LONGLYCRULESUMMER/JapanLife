import re

_JA_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")


def detect_language(text: str) -> str:
    """Return 'ja' if Japanese characters are a meaningful share of the text, else 'en'."""
    if not text:
        return "en"
    non_space = re.sub(r"\s", "", text)
    if not non_space:
        return "en"
    ja_chars = _JA_PATTERN.findall(non_space)
    return "ja" if len(ja_chars) / len(non_space) >= 0.2 else "en"
