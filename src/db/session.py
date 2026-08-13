from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # ── [최적화] 커넥션 풀 튜닝 ─────────────────────────────
    # 기본값(pool_size=5, max_overflow=10 → 최대 15)으로는
    # 동시 접속 100명대에서 QueuePool 타임아웃(500 에러)이 발생
    # 25+25 = 최대 50 으로 확대 (Supabase Nano 커넥션 상한과 정렬)
    pool_size=25,          # 상시 유지 커넥션
    max_overflow=25,       # 피크 시 추가 허용 → 최대 50
    pool_timeout=30,       # 커넥션 대기 한계(초)
    pool_recycle=1800,     # 30분마다 커넥션 재생성(유휴 끊김 방지)
    pool_pre_ping=True,    # 사용 전 연결 상태 확인(죽은 커넥션 방지)
    connect_args={"prepare_threshold": None},  # Transaction mode(6543) 필수, 유지
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
