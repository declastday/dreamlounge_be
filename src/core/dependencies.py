from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.core.security import decode_access_token

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
        )

    from src.models.user import User
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def require_club_president(club_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """해당 동아리의 현직 회장인지 확인. 아니면 403."""
    from src.models.club_member import ClubMember
    membership = db.query(ClubMember).filter(
        ClubMember.club_id == club_id,
        ClubMember.user_id == current_user.id,
        ClubMember.role == "president",
        ClubMember.status == "active",
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="동아리 회장만 접근할 수 있습니다.",
        )
    return current_user


def require_club_member(club_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """해당 동아리의 active 부원(회장 포함)인지 확인. 아니면 403."""
    from src.models.club_member import ClubMember
    membership = db.query(ClubMember).filter(
        ClubMember.club_id == club_id,
        ClubMember.user_id == current_user.id,
        ClubMember.status == "active",
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="동아리 부원만 접근할 수 있습니다.",
        )
    return current_user
