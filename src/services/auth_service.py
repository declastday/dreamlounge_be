import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.models.user import User, PrivacyConsent, EmailVerification
from src.schemas.user import UserCreate
from src.utils.email import send_verification_email


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _get_valid_verification(db: Session, email: str, code: str) -> EmailVerification | None:
    """미사용·미만료 레코드 중 코드가 일치하는 것을 반환."""
    return db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == code,
        EmailVerification.is_used == False,
        EmailVerification.expires_at > datetime.utcnow(),
    ).first()


def send_verification_code(db: Session, email: str) -> None:
    """청주대 이메일로 6자리 인증번호 발송. 이전 대기 레코드는 모두 만료 처리."""
    if not email.lower().endswith(f"@{settings.CJU_EMAIL_DOMAIN}"):
        raise ValueError(f"청주대학교 이메일(@{settings.CJU_EMAIL_DOMAIN})만 사용할 수 있습니다.")

    code = _generate_code()

    db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.is_used == False,
    ).update({"is_used": True})

    db.add(EmailVerification(
        email=email,
        code=code,
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRY_MINUTES),
    ))
    db.commit()

    if not settings.RESEND_API_KEY:
        import logging
        logging.getLogger(__name__).warning(f"[개발모드] 이메일 인증번호: {email} → {code}")
        return

    try:
        send_verification_email(email, code)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(f"[개발모드] 이메일 발송 실패, 인증번호 콘솔 출력: {email} → {code}")


def confirm_verification_code(db: Session, email: str, code: str) -> None:
    """인증번호 유효성 확인 (UX 피드백용). 상태를 변경하지 않는다."""
    if not _get_valid_verification(db, email, code):
        raise ValueError("인증번호가 올바르지 않거나 만료되었습니다.")


def register_user(db: Session, data: UserCreate) -> User:
    """인증번호 검증 → 중복 검사 → User + PrivacyConsent 생성."""
    email = str(data.email)

    # 인증번호 검증
    verification = _get_valid_verification(db, email, data.verification_code)
    if not verification:
        raise ValueError("이메일 인증번호가 올바르지 않거나 만료되었습니다. 인증번호를 다시 요청해주세요.")

    # 필수 개인정보 동의 확인
    if not data.privacy_consent.required_agreed:
        raise ValueError("필수 개인정보 수집 동의가 필요합니다.")

    # 중복 확인
    if db.query(User).filter(User.student_id == data.student_id).first():
        raise ValueError("이미 가입된 학번입니다.")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("이미 가입된 이메일입니다.")

    user = User(
        student_id=data.student_id,
        password_hash=hash_password(data.password),
        name=data.name,
        phone=data.phone,
        department=data.department,
        email=email,
        email_verified=True,
    )
    db.add(user)
    db.flush()

    db.add(PrivacyConsent(
        user_id=user.id,
        required_agreed=data.privacy_consent.required_agreed,
        optional_agreed=data.privacy_consent.optional_agreed,
    ))

    verification.is_used = True
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, student_id: str, password: str) -> User | None:
    """학번 + 비밀번호 검증. 성공 시 User 반환, 실패 시 None."""
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
