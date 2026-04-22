import anthropic

from app.core.config import settings

_client = None


def get_client():
    """Anthropic API 클라이언트를 반환한다."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
