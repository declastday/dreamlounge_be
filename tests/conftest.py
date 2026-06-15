import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from src.main import app
from src.db.base import Base
from src.db.session import get_db

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    import src.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    """각 테스트 후 모든 테이블 초기화."""
    yield
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.execute(text("PRAGMA foreign_keys = ON"))


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def register_and_login(client, db, student_id: str, email: str, password: str = "Password1!") -> str:
    """이메일 인증 → 회원가입 → 로그인 순서로 처리하고 access_token 반환."""
    from src.models.user import EmailVerification

    with patch("src.services.auth_service.send_verification_email"):
        client.post("/api/v1/auth/email-verify/send", json={"email": email})

    code = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.is_used == False,
    ).first().code

    client.post("/api/v1/auth/register", json={
        "student_id": student_id,
        "password": password,
        "name": "테스트유저",
        "phone": "010-0000-0000",
        "department": "컴퓨터공학과",
        "email": email,
        "verification_code": code,
        "privacy_consent": {"required_agreed": True, "optional_agreed": False},
    })

    resp = client.post("/api/v1/auth/login", json={"student_id": student_id, "password": password})
    return resp.json()["access_token"]


@pytest.fixture
def user_token(client, db) -> str:
    return register_and_login(client, db, "2021000001", "user@cju.ac.kr")


@pytest.fixture
def auth_headers(user_token) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def president_token(client, seeded_club) -> str:
    resp = client.post("/api/v1/auth/login", json={"student_id": "PRES0000001", "password": "Password1!"})
    return resp.json()["access_token"]


@pytest.fixture
def president_headers(president_token) -> dict:
    return {"Authorization": f"Bearer {president_token}"}


@pytest.fixture
def seeded_club(db) -> dict:
    """테스트용 동아리 + 활성 신청 폼 + 질문 1개를 DB에 직접 생성."""
    from src.models.user import User
    from src.models.club import Club
    from src.models.club_member import ClubMember
    from src.models.application import ApplicationForm, FormQuestion
    from src.core.security import hash_password

    president = User(
        student_id="PRES0000001",
        password_hash=hash_password("Password1!"),
        name="동아리회장",
        email="president@cju.ac.kr",
        email_verified=True,
    )
    db.add(president)
    db.flush()

    club = Club(
        president_id=president.id,
        name="테스트동아리",
        club_type="central",
        description="테스트용 동아리입니다.",
        is_recruiting=True,
    )
    db.add(club)
    db.flush()

    db.add(ClubMember(club_id=club.id, user_id=president.id, role="president", status="active"))

    form = ApplicationForm(club_id=club.id, title="2025년 신입부원 모집")
    db.add(form)
    db.flush()

    question = FormQuestion(
        form_id=form.id,
        question_text="지원 동기를 작성해주세요.",
        question_type="text",
        is_required=True,
        order_index=0,
    )
    db.add(question)
    db.commit()

    db.refresh(club)
    db.refresh(form)
    db.refresh(question)

    return {"club": club, "form": form, "question": question, "president": president}
