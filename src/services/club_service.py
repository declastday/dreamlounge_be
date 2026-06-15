from sqlalchemy.orm import Session, selectinload
from src.models.club import Club, ClubTag
from src.models.club_member import ClubMember
from src.models.application import ApplicationForm, FormQuestion
from src.models.user import User
from src.schemas.club import ClubCreate, ClubUpdate, FormCreate, FormUpdate, QuestionCreate, QuestionUpdate


def get_clubs(db: Session) -> list[Club]:
    """전체 동아리 목록 조회 (tags + members 함께 로드)."""
    return (
        db.query(Club)
        .options(selectinload(Club.tags), selectinload(Club.members))
        .all()
    )


def get_club(db: Session, club_id: str) -> Club | None:
    """club_id로 동아리 상세 정보 조회 (tags 포함)."""
    return (
        db.query(Club)
        .options(selectinload(Club.tags))
        .filter(Club.id == club_id)
        .first()
    )


def get_active_form(db: Session, club_id: str) -> ApplicationForm | None:
    """동아리의 활성 신청 폼과 질문 목록 조회 (is_active=True인 최신 폼)."""
    return (
        db.query(ApplicationForm)
        .options(selectinload(ApplicationForm.questions))
        .filter(ApplicationForm.club_id == club_id, ApplicationForm.is_active == True)
        .first()
    )


def create_club(db: Session, user: User, data: ClubCreate) -> Club:
    if db.query(Club).filter(Club.name == data.name).first():
        raise ValueError("이미 등록된 동아리 이름입니다.")

    club = Club(
        president_id=user.id,
        name=data.name,
        club_type=data.club_type,
        description=data.description,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        open_chat_url=data.open_chat_url,
        image_url=data.image_url,
        activity_images=data.activity_images or [],
        division=data.division,
        field=data.field,
        atmosphere=data.atmosphere,
        activity_purpose=data.activity_purpose,
        activity_period=data.activity_period,
        recruit_start=data.recruit_start,
        recruit_end=data.recruit_end,
        is_recruiting=data.is_recruiting,
    )
    db.add(club)
    db.flush()

    for tag in data.tags:
        db.add(ClubTag(club_id=club.id, tag_key=tag.tag_key, tag_value=tag.tag_value))

    db.add(ClubMember(club_id=club.id, user_id=user.id, role="president", status="active"))

    db.commit()
    db.refresh(club)
    return club


def update_club(db: Session, club: Club, data: ClubUpdate) -> Club:
    if data.name is not None and data.name != club.name:
        if db.query(Club).filter(Club.name == data.name).first():
            raise ValueError("이미 등록된 동아리 이름입니다.")

    for field, value in data.model_dump(exclude_unset=True, exclude={"tags"}).items():
        setattr(club, field, value)

    if data.tags is not None:
        for tag in list(club.tags):
            db.delete(tag)
        db.flush()
        for tag in data.tags:
            db.add(ClubTag(club_id=club.id, tag_key=tag.tag_key, tag_value=tag.tag_value))

    db.commit()
    db.refresh(club)
    return club


# ── 신청 폼 관리 ───────────────────────────────────────────────────────────────

def create_form(db: Session, club_id: str, data: FormCreate) -> ApplicationForm:
    existing = db.query(ApplicationForm).filter(
        ApplicationForm.club_id == club_id,
        ApplicationForm.is_active == True,
    ).first()
    if existing:
        raise ValueError("이미 활성화된 신청 폼이 존재합니다.")

    form = ApplicationForm(club_id=club_id, title=data.title)
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


def update_form(db: Session, club_id: str, data: FormUpdate) -> ApplicationForm:
    form = db.query(ApplicationForm).filter(
        ApplicationForm.club_id == club_id,
        ApplicationForm.is_active == True,
    ).first()
    if not form:
        raise LookupError("활성화된 신청 폼이 없습니다.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(form, field, value)

    db.commit()
    db.refresh(form)
    return form


def add_question(db: Session, club_id: str, data: QuestionCreate) -> FormQuestion:
    form = db.query(ApplicationForm).filter(
        ApplicationForm.club_id == club_id,
        ApplicationForm.is_active == True,
    ).first()
    if not form:
        raise LookupError("활성화된 신청 폼이 없습니다.")

    question = FormQuestion(
        form_id=form.id,
        question_text=data.question_text,
        question_type=data.question_type,
        is_required=data.is_required,
        order_index=data.order_index,
        options=data.options,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def update_question(db: Session, club_id: str, question_id: str, data: QuestionUpdate) -> FormQuestion:
    question = (
        db.query(FormQuestion)
        .join(ApplicationForm, FormQuestion.form_id == ApplicationForm.id)
        .filter(ApplicationForm.club_id == club_id, FormQuestion.id == question_id)
        .first()
    )
    if not question:
        raise LookupError("질문을 찾을 수 없습니다.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, club_id: str, question_id: str) -> None:
    question = (
        db.query(FormQuestion)
        .join(ApplicationForm, FormQuestion.form_id == ApplicationForm.id)
        .filter(ApplicationForm.club_id == club_id, FormQuestion.id == question_id)
        .first()
    )
    if not question:
        raise LookupError("질문을 찾을 수 없습니다.")

    db.delete(question)
    db.commit()


def reorder_questions(db: Session, club_id: str, question_ids: list[str]) -> ApplicationForm:
    form = db.query(ApplicationForm).filter(
        ApplicationForm.club_id == club_id,
        ApplicationForm.is_active == True,
    ).first()
    if not form:
        raise LookupError("활성화된 신청 폼이 없습니다.")

    id_to_question = {q.id: q for q in form.questions}
    for idx, qid in enumerate(question_ids):
        if qid not in id_to_question:
            raise ValueError(f"질문 ID를 찾을 수 없습니다: {qid}")
        id_to_question[qid].order_index = idx

    db.commit()
    db.refresh(form)
    return form
