from datetime import datetime
from sqlalchemy.orm import Session, selectinload

from src.models.club_member import ClubMember


def list_members(db: Session, club_id: str) -> list[dict]:
    """동아리 회원 목록 조회.

    user 를 함께 로드한다(N+1 방지).
    아래 반복문에서 m.user.name / student_id / department / email / phone 을
    접근하므로, eager loading 이 없으면 회원 수만큼 추가 쿼리가 발생한다.
    (회원 41명 -> 쿼리 42회, 개선 후 2회)
    """
    members = (
        db.query(ClubMember)
        .options(selectinload(ClubMember.user))
        .filter(ClubMember.club_id == club_id, ClubMember.status == "active")
        .all()
    )
    return [
        {
            "user_id": m.user_id,
            "name": m.user.name,
            "student_id": m.user.student_id,
            "department": m.user.department,
            "email": m.user.email,
            "phone": m.user.phone,
            "role": m.role,
            "joined_at": m.joined_at,
        }
        for m in members
    ]


def withdraw_member(db: Session, club_id: str, target_user_id: str) -> None:
    member = db.query(ClubMember).filter(
        ClubMember.club_id == club_id,
        ClubMember.user_id == target_user_id,
        ClubMember.status == "active",
    ).first()
    if not member:
        raise LookupError("해당 부원을 찾을 수 없습니다.")
    if member.role == "president":
        raise ValueError("회장은 탈퇴 처리할 수 없습니다. 권한 이전 후 탈퇴해주세요.")

    member.status = "withdrawn"
    member.left_at = datetime.utcnow()
    db.commit()


def transfer_role(db: Session, club_id: str, current_president_id: str, target_user_id: str) -> None:
    if current_president_id == target_user_id:
        raise ValueError("본인에게 권한을 이전할 수 없습니다.")

    new_president = db.query(ClubMember).filter(
        ClubMember.club_id == club_id,
        ClubMember.user_id == target_user_id,
        ClubMember.status == "active",
    ).first()
    if not new_president:
        raise LookupError("대상 부원을 찾을 수 없습니다.")

    old_president = db.query(ClubMember).filter(
        ClubMember.club_id == club_id,
        ClubMember.user_id == current_president_id,
        ClubMember.role == "president",
    ).first()

    old_president.role = "member"
    new_president.role = "president"

    from src.models.club import Club
    db.query(Club).filter(Club.id == club_id).update({"president_id": target_user_id})

    db.commit()
