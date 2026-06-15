from datetime import datetime
from sqlalchemy.orm import Session, selectinload

from src.models.application import Application, ApplicationAnswer, ApplicationForm
from src.models.club import Club
from src.models.club_member import ClubMember
from src.models.user import User
from src.schemas.application import ApplicationCreate, ApplicationUpdate


def _to_list_dict(app: Application) -> dict:
    return {
        "id": app.id,
        "form_id": app.form_id,
        "club_id": app.form.club_id if app.form else None,
        "club_name": app.form.club.name if (app.form and app.form.club) else None,
        "status": app.status,
        "is_draft": app.is_draft,
        "submitted_at": app.submitted_at,
        "updated_at": app.updated_at,
    }


def _to_detail_dict(app: Application) -> dict:
    d = _to_list_dict(app)
    d["answers"] = [
        {"question_id": a.question_id, "answer_text": a.answer_text}
        for a in app.answers
    ]
    return d


def _validate_required_answers(form_questions, answers) -> None:
    answered_ids = {a.question_id for a in answers}
    for q in form_questions:
        if q.is_required and q.id not in answered_ids:
            raise ValueError(f"필수 항목에 답변이 누락되었습니다: {q.question_text}")


def create_application(db: Session, user: User, data: ApplicationCreate) -> dict:
    form = db.get(ApplicationForm, data.form_id)
    if not form or not form.is_active:
        raise ValueError("존재하지 않거나 비활성화된 신청 폼입니다.")

    existing_submitted = (
        db.query(Application)
        .filter(
            Application.form_id == data.form_id,
            Application.user_id == user.id,
            Application.is_draft == False,
        )
        .first()
    )
    if existing_submitted:
        raise ValueError("이미 제출한 신청서가 있습니다.")

    if not data.is_draft:
        _validate_required_answers(form.questions, data.answers)

    now = datetime.utcnow()
    app = Application(
        form_id=data.form_id,
        user_id=user.id,
        is_draft=data.is_draft,
        status="draft" if data.is_draft else "submitted",
        submitted_at=None if data.is_draft else now,
    )
    db.add(app)
    db.flush()

    for ans in data.answers:
        db.add(ApplicationAnswer(
            application_id=app.id,
            question_id=ans.question_id,
            answer_text=ans.answer_text,
        ))

    db.commit()

    result = (
        db.query(Application)
        .options(
            selectinload(Application.answers),
            selectinload(Application.form).selectinload(ApplicationForm.club),
        )
        .filter(Application.id == app.id)
        .first()
    )
    return _to_detail_dict(result)


def update_application(
    db: Session, user: User, application_id: str, data: ApplicationUpdate
) -> dict:
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == user.id)
        .first()
    )
    if not app:
        raise LookupError("신청서를 찾을 수 없습니다.")
    if not app.is_draft:
        raise ValueError("이미 제출된 신청서는 수정할 수 없습니다.")

    submitting = data.is_draft is False

    if data.answers is not None:
        for ans in list(app.answers):
            db.delete(ans)
        db.flush()
        for ans in data.answers:
            db.add(ApplicationAnswer(
                application_id=app.id,
                question_id=ans.question_id,
                answer_text=ans.answer_text,
            ))
        app.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(app)

    if submitting:
        answers_to_check = data.answers if data.answers is not None else app.answers
        form = db.get(ApplicationForm, app.form_id)
        _validate_required_answers(form.questions, answers_to_check)
        app.is_draft = False
        app.status = "submitted"
        app.submitted_at = datetime.utcnow()

    db.commit()

    result = (
        db.query(Application)
        .options(
            selectinload(Application.answers),
            selectinload(Application.form).selectinload(ApplicationForm.club),
        )
        .filter(Application.id == app.id)
        .first()
    )
    return _to_detail_dict(result)


def delete_application(db: Session, user: User, application_id: str) -> None:
    """신청서 삭제 (임시저장) 또는 지원 취소 (제출됨·검토중)."""
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == user.id)
        .first()
    )
    if not app:
        raise LookupError("신청서를 찾을 수 없습니다.")
    if app.status in ("passed", "failed"):
        raise ValueError("이미 심사가 완료된 신청서는 취소할 수 없습니다.")
    # FK 제약 오류 방지: answers를 먼저 명시 삭제 후 application 삭제
    db.query(ApplicationAnswer).filter(ApplicationAnswer.application_id == app.id).delete(synchronize_session=False)
    db.delete(app)
    db.commit()


def get_draft_applications(db: Session, user: User) -> list[dict]:
    apps = (
        db.query(Application)
        .options(selectinload(Application.form).selectinload(ApplicationForm.club))
        .filter(Application.user_id == user.id, Application.is_draft == True)
        .order_by(Application.updated_at.desc())
        .all()
    )
    return [_to_list_dict(app) for app in apps]


def get_draft_application(db: Session, user: User, application_id: str) -> dict | None:
    app = (
        db.query(Application)
        .options(
            selectinload(Application.answers),
            selectinload(Application.form).selectinload(ApplicationForm.club),
        )
        .filter(
            Application.id == application_id,
            Application.user_id == user.id,
            Application.is_draft == True,
        )
        .first()
    )
    return _to_detail_dict(app) if app else None


def get_submitted_applications(db: Session, user: User) -> list[dict]:
    apps = (
        db.query(Application)
        .options(selectinload(Application.form).selectinload(ApplicationForm.club))
        .filter(Application.user_id == user.id, Application.is_draft == False)
        .order_by(Application.submitted_at.desc())
        .all()
    )
    return [_to_list_dict(app) for app in apps]


def get_submitted_application(db: Session, user: User, application_id: str) -> dict | None:
    app = (
        db.query(Application)
        .options(
            selectinload(Application.answers),
            selectinload(Application.form).selectinload(ApplicationForm.club),
        )
        .filter(
            Application.id == application_id,
            Application.user_id == user.id,
            Application.is_draft == False,
        )
        .first()
    )
    return _to_detail_dict(app) if app else None


def get_active_clubs(db: Session, user: User) -> list[dict]:
    memberships = (
        db.query(ClubMember)
        .join(Club, ClubMember.club_id == Club.id)
        .filter(ClubMember.user_id == user.id, ClubMember.status == "active")
        .all()
    )
    return [
        {
            "club_id": m.club_id,
            "club_name": m.club.name,
            "role": m.role,
            "joined_at": m.joined_at,
        }
        for m in memberships
    ]


# ── 관리자: 신청서 심사 ────────────────────────────────────────────────────────

def get_club_applications(db: Session, club_id: str) -> list[dict]:
    """동아리에 제출된 신청서 목록 (is_draft=False)."""
    apps = (
        db.query(Application)
        .join(ApplicationForm, Application.form_id == ApplicationForm.id)
        .filter(ApplicationForm.club_id == club_id, Application.is_draft == False)
        .order_by(Application.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_name": a.user.name,
            "user_student_id": a.user.student_id,
            "status": a.status,
            "submitted_at": a.submitted_at,
        }
        for a in apps
    ]


def get_club_application(db: Session, club_id: str, application_id: str) -> dict | None:
    """동아리 신청서 상세 (관리자용)."""
    app = (
        db.query(Application)
        .options(selectinload(Application.answers), selectinload(Application.user))
        .join(ApplicationForm, Application.form_id == ApplicationForm.id)
        .filter(
            ApplicationForm.club_id == club_id,
            Application.id == application_id,
            Application.is_draft == False,
        )
        .first()
    )
    if not app:
        return None
    return {
        "id": app.id,
        "user_id": app.user_id,
        "user_name": app.user.name,
        "user_student_id": app.user.student_id,
        "status": app.status,
        "submitted_at": app.submitted_at,
        "answers": app.answers,
    }


def update_application_status(db: Session, club_id: str, application_id: str, new_status: str) -> Application:
    """심사 결과 업데이트. passed 시 ClubMember 자동 등록."""
    app = (
        db.query(Application)
        .join(ApplicationForm, Application.form_id == ApplicationForm.id)
        .filter(
            ApplicationForm.club_id == club_id,
            Application.id == application_id,
            Application.is_draft == False,
        )
        .first()
    )
    if not app:
        raise LookupError("신청서를 찾을 수 없습니다.")
    if app.status in ("passed", "failed"):
        raise ValueError("이미 최종 심사가 완료된 신청서입니다.")

    app.status = new_status

    if new_status == "passed":
        already = db.query(ClubMember).filter(
            ClubMember.club_id == club_id,
            ClubMember.user_id == app.user_id,
            ClubMember.status == "active",
        ).first()
        if not already:
            db.add(ClubMember(club_id=club_id, user_id=app.user_id, role="member", status="active"))

    db.commit()
    db.refresh(app)
    return app
