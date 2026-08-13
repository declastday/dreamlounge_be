import random
import secrets
import string
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.models.club_member import ClubMember
from src.models.user import User, PrivacyConsent, EmailVerification
from src.schemas.user import UserCreate
from src.utils.email import send_verification_email
from src.utils.supabase_client import (
    create_supabase_auth_client,
    get_supabase_admin_client,
)


logger = logging.getLogger(__name__)
ACTIVE_PRESIDENT_WITHDRAWAL_ERROR = (
    "동아리 회장은 다른 부원에게 회장 권한을 이전한 후 회원탈퇴할 수 있습니다."
)


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _get_valid_verification(db: Session, email: str, code: str) -> EmailVerification | None:
    """미사용·미만료 레코드 중 코드가 일치하는 것을 반환."""
    return db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == code,
        EmailVerification.is_used.is_(False),
        EmailVerification.expires_at > datetime.utcnow(),
    ).first()


def send_verification_code(db: Session, email: str) -> None:
    """청주대 이메일로 6자리 인증번호 발송. 이전 대기 레코드는 모두 만료 처리."""
    if not email.lower().endswith(f"@{settings.CJU_EMAIL_DOMAIN}"):
        raise ValueError(f"청주대학교 이메일(@{settings.CJU_EMAIL_DOMAIN})만 사용할 수 있습니다.")

    code = _generate_code()

    db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.is_used.is_(False),
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

    auth_user_id = None
    if settings.SUPABASE_SERVICE_KEY:
        client = get_supabase_admin_client()
        auth_response = client.auth.admin.create_user({
            "email": email,
            "password": data.password,
            "email_confirm": True,
            "user_metadata": {"student_id": data.student_id, "name": data.name},
        })
        auth_user_id = str(auth_response.user.id)

    user = User(
        auth_user_id=auth_user_id,
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


def create_supabase_session(db: Session, user: User, password: str):
    """Supabase Auth 세션을 만들고 기존 계정은 최초 로그인 시 안전하게 연결한다."""
    if not settings.SUPABASE_SERVICE_KEY:
        return None

    auth_client = create_supabase_auth_client()
    if not user.auth_user_id:
        if not verify_password(password, user.password_hash):
            return None
        auth_response = get_supabase_admin_client().auth.admin.create_user({
            "email": user.email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"student_id": user.student_id, "name": user.name},
        })
        user.auth_user_id = str(auth_response.user.id)
        db.commit()

    return auth_client.auth.sign_in_with_password({
        "email": user.email,
        "password": password,
    }).session


def withdraw_user(db: Session, user: User) -> None:
    """인증 계정을 삭제하고 개인정보를 익명화해 동일 정보 재가입을 허용한다."""
    active_presidency = db.query(ClubMember).filter(
        ClubMember.user_id == user.id,
        ClubMember.role == "president",
        ClubMember.status == "active",
    ).first()
    if active_presidency:
        raise PermissionError(ACTIVE_PRESIDENT_WITHDRAWAL_ERROR)

    withdrawn_at = datetime.utcnow()
    active_memberships = db.query(ClubMember).filter(
        ClubMember.user_id == user.id,
        ClubMember.status == "active",
    ).all()
    for membership in active_memberships:
        membership.status = "withdrawn"
        membership.left_at = withdrawn_at

    original_email = user.email
    auth_user_id = user.auth_user_id

    # 활동 기록의 외래 키는 유지하되 개인정보와 고유값은 제거한다.
    # 따라서 기존 게시글/지원서는 탈퇴 사용자 기록으로 남고, 같은 학번과
    # 이메일은 새로운 계정에서 다시 사용할 수 있다.
    user.auth_user_id = None
    user.student_id = f"deleted_{user.id.replace('-', '')[:12]}"
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.name = "탈퇴한 사용자"
    user.phone = None
    user.department = None
    user.email = f"deleted+{user.id}@invalid.local"
    user.email_verified = False
    user.is_active = False
    user.withdrawn_at = withdrawn_at

    db.query(PrivacyConsent).filter(
        PrivacyConsent.user_id == user.id,
    ).delete(synchronize_session=False)
    db.query(EmailVerification).filter(
        EmailVerification.email == original_email,
    ).delete(synchronize_session=False)

    try:
        db.flush()
        if settings.SUPABASE_SERVICE_KEY and auth_user_id:
            get_supabase_admin_client().auth.admin.delete_user(
                auth_user_id,
                should_soft_delete=False,
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("회원탈퇴 처리 중 오류가 발생했습니다.", exc_info=True)
        raise RuntimeError("회원탈퇴 처리에 실패했습니다.") from exc
