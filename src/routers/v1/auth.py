import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import OperationalError as DBOperationalError
from sqlalchemy.orm import Session

from src.core.security import create_access_token
from src.core.dependencies import get_current_user
from src.db.session import get_db
from src.schemas.user import (
    EmailVerifySendRequest,
    EmailVerifyConfirmRequest,
    UserCreate,
    LoginRequest,
    TokenResponse,
    UserInfo,
    UserResponse,
)
from src.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/email-verify/send", status_code=status.HTTP_200_OK)
def send_email_verification(body: EmailVerifySendRequest, db: Session = Depends(get_db)):
    """청주대 이메일로 6자리 인증번호 발송."""
    try:
        auth_service.send_verification_code(db, str(body.email))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DBOperationalError as e:
        logger.error(f"DB 연결 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 연결에 실패했습니다. 서버 설정을 확인해주세요.",
        )
    except Exception as e:
        logger.error(f"이메일 발송 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )
    return {"message": "인증번호가 발송되었습니다."}


@router.post("/email-verify/confirm", status_code=status.HTTP_200_OK)
def confirm_email_verification(body: EmailVerifyConfirmRequest, db: Session = Depends(get_db)):
    """인증번호 검증."""
    try:
        auth_service.confirm_verification_code(db, str(body.email), body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DBOperationalError as e:
        logger.error(f"DB 연결 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 연결에 실패했습니다. 서버 설정을 확인해주세요.",
        )
    return {"message": "이메일 인증이 완료되었습니다."}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """회원가입 (개인정보 동의 포함)."""
    try:
        user = auth_service.register_user(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DBOperationalError as e:
        logger.error(f"DB 연결 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 연결에 실패했습니다. 서버 설정을 확인해주세요.",
        )
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """학번 + 비밀번호 로그인 → JWT + 사용자 정보 반환."""
    user = auth_service.authenticate_user(db, body.student_id, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="학번 또는 비밀번호가 올바르지 않습니다.",
        )
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserInfo.model_validate(user))


@router.get("/me", response_model=UserInfo)
def get_me(current_user=Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회."""
    return current_user
