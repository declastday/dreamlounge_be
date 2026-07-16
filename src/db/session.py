from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"prepare_threshold": None},
    # ── 커넥션 풀 튜닝 ──────────────────────────────────
    # 기본값(pool_size=5, max_overflow=10 → 최대 15)으로는
    # 동시 접속 100명에서 QueuePool 타임아웃이 발생함.
    pool_size=16,          # 상시 유지 커넥션
    max_overflow=8,       # 피크 시 추가 허용 → 최대 50
    pool_timeout=30,       # 대기 한계(초). 30초는 너무 길어 사용자가 체감함
    pool_recycle=1800,     # 30분마다 재생성 (pooler가 끊는 유휴 커넥션 대비)
    pool_pre_ping=True,    # 사용 전 살아있는지 확인 (끊긴 커넥션 오류 방지)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
