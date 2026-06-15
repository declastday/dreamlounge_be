import logging
from supabase import create_client, Client
from src.core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    """서버 사이드 전용. service_role 키를 우선 사용해 RLS를 우회한다."""
    global _client
    if _client is None:
        if settings.SUPABASE_SERVICE_KEY:
            key = settings.SUPABASE_SERVICE_KEY
            logger.info("Supabase: service_role 키 사용 중")
        else:
            key = settings.SUPABASE_ANON_KEY
            logger.warning("Supabase: SUPABASE_SERVICE_KEY 미설정 — anon 키 사용 중 (Storage 업로드 불가)")
        _client = create_client(settings.SUPABASE_URL, key)
    return _client
