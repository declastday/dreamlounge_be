from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.models.user import EmailVerification


# ── 헬스체크 ──────────────────────────────────────────────────────────────────

def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200


# ── 이메일 인증번호 발송 ───────────────────────────────────────────────────────

class TestEmailVerifySend:
    def test_success(self, client):
        with patch("src.services.auth_service.send_verification_email") as mock_send:
            resp = client.post("/api/v1/auth/email-verify/send", json={"email": "test@cju.ac.kr"})
        assert resp.status_code == 200
        mock_send.assert_called_once_with("test@cju.ac.kr", mock_send.call_args[0][1])

    def test_wrong_domain(self, client):
        resp = client.post("/api/v1/auth/email-verify/send", json={"email": "test@gmail.com"})
        assert resp.status_code == 400

    def test_invalid_email_format(self, client):
        resp = client.post("/api/v1/auth/email-verify/send", json={"email": "not-an-email"})
        assert resp.status_code == 422

    def test_resend_invalidates_previous_code(self, client, db):
        """재발송 시 이전 코드가 만료 처리되는지 확인."""
        with patch("src.services.auth_service.send_verification_email"):
            client.post("/api/v1/auth/email-verify/send", json={"email": "resend@cju.ac.kr"})
            client.post("/api/v1/auth/email-verify/send", json={"email": "resend@cju.ac.kr"})

        unused = db.query(EmailVerification).filter(
            EmailVerification.email == "resend@cju.ac.kr",
            EmailVerification.is_used.is_(False),
        ).all()
        assert len(unused) == 1


# ── 이메일 인증번호 확인 ───────────────────────────────────────────────────────

class TestEmailVerifyConfirm:
    def test_success(self, client, db):
        with patch("src.services.auth_service.send_verification_email"):
            client.post("/api/v1/auth/email-verify/send", json={"email": "confirm@cju.ac.kr"})

        code = db.query(EmailVerification).filter(
            EmailVerification.email == "confirm@cju.ac.kr",
            EmailVerification.is_used.is_(False),
        ).first().code

        resp = client.post("/api/v1/auth/email-verify/confirm", json={
            "email": "confirm@cju.ac.kr",
            "code": code,
        })
        assert resp.status_code == 200

    def test_wrong_code(self, client, db):
        with patch("src.services.auth_service.send_verification_email"):
            client.post("/api/v1/auth/email-verify/send", json={"email": "wrong@cju.ac.kr"})

        resp = client.post("/api/v1/auth/email-verify/confirm", json={
            "email": "wrong@cju.ac.kr",
            "code": "000000",
        })
        assert resp.status_code == 400

    def test_no_code_sent(self, client):
        resp = client.post("/api/v1/auth/email-verify/confirm", json={
            "email": "nobody@cju.ac.kr",
            "code": "123456",
        })
        assert resp.status_code == 400

    def test_code_must_be_6_digits(self, client):
        resp = client.post("/api/v1/auth/email-verify/confirm", json={
            "email": "test@cju.ac.kr",
            "code": "12345",  # 5자리
        })
        assert resp.status_code == 422


# ── 회원가입 ───────────────────────────────────────────────────────────────────

class TestRegister:
    EMAIL = "register@cju.ac.kr"
    STUDENT_ID = "2021111111"

    def _get_code(self, client, db, email=None):
        email = email or self.EMAIL
        with patch("src.services.auth_service.send_verification_email"):
            client.post("/api/v1/auth/email-verify/send", json={"email": email})
        return db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.is_used.is_(False),
        ).first().code

    def _base_payload(self, code, student_id=None, email=None):
        return {
            "student_id": student_id or self.STUDENT_ID,
            "password": "Password1!",
            "name": "홍길동",
            "phone": "010-1234-5678",
            "department": "컴퓨터공학과",
            "email": email or self.EMAIL,
            "verification_code": code,
            "privacy_consent": {"required_agreed": True, "optional_agreed": False},
        }

    def test_success(self, client, db):
        code = self._get_code(client, db)
        resp = client.post("/api/v1/auth/register", json=self._base_payload(code))
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == self.EMAIL
        assert data["student_id"] == self.STUDENT_ID
        assert data["email_verified"] is True

    def test_missing_required_consent(self, client, db):
        code = self._get_code(client, db)
        payload = self._base_payload(code)
        payload["privacy_consent"]["required_agreed"] = False
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_wrong_verification_code(self, client, db):
        self._get_code(client, db)
        payload = self._base_payload("000000")
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_duplicate_student_id(self, client, db):
        code = self._get_code(client, db)
        client.post("/api/v1/auth/register", json=self._base_payload(code))

        email2 = "register2@cju.ac.kr"
        code2 = self._get_code(client, db, email2)
        payload = self._base_payload(code2, student_id=self.STUDENT_ID, email=email2)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_duplicate_email(self, client, db):
        code = self._get_code(client, db)
        client.post("/api/v1/auth/register", json=self._base_payload(code))

        code2 = self._get_code(client, db)  # 같은 이메일로 재발송
        payload = self._base_payload(code2, student_id="2021999999")
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_password_too_short(self, client, db):
        code = self._get_code(client, db)
        payload = self._base_payload(code)
        payload["password"] = "short"
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422


# ── 로그인 ─────────────────────────────────────────────────────────────────────

class TestLogin:
    EMAIL = "login@cju.ac.kr"
    STUDENT_ID = "2021222222"
    PASSWORD = "Password1!"

    def _register(self, client, db):
        with patch("src.services.auth_service.send_verification_email"):
            client.post("/api/v1/auth/email-verify/send", json={"email": self.EMAIL})
        code = db.query(EmailVerification).filter(
            EmailVerification.email == self.EMAIL,
            EmailVerification.is_used.is_(False),
        ).first().code
        client.post("/api/v1/auth/register", json={
            "student_id": self.STUDENT_ID,
            "password": self.PASSWORD,
            "name": "로그인테스트",
            "email": self.EMAIL,
            "verification_code": code,
            "privacy_consent": {"required_agreed": True, "optional_agreed": False},
        })

    def test_success(self, client, db):
        self._register(client, db)
        resp = client.post("/api/v1/auth/login", json={
            "student_id": self.STUDENT_ID,
            "password": self.PASSWORD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_wrong_password(self, client, db):
        self._register(client, db)
        resp = client.post("/api/v1/auth/login", json={
            "student_id": self.STUDENT_ID,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_unknown_student_id(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "student_id": "9999999999",
            "password": "SomePassword!",
        })
        assert resp.status_code == 401

    def test_token_is_usable(self, client, db):
        """발급된 토큰으로 인증이 필요한 엔드포인트 접근 가능한지 확인."""
        self._register(client, db)
        login_resp = client.post("/api/v1/auth/login", json={
            "student_id": self.STUDENT_ID,
            "password": self.PASSWORD,
        })
        token = login_resp.json()["access_token"]

        resp = client.get("/api/v1/me/applications/drafts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


# ── 회원탈퇴 ───────────────────────────────────────────────────────────────────

class TestAccountWithdrawal:
    def test_withdraws_account_and_active_memberships(
        self, client, db, auth_headers, seeded_club
    ):
        from src.models.club_member import ClubMember
        from src.models.user import User

        user = db.query(User).filter(User.student_id == "2021000001").one()
        membership = ClubMember(
            club_id=seeded_club["club"].id,
            user_id=user.id,
            role="member",
            status="active",
        )
        db.add(membership)
        db.commit()

        resp = client.delete("/api/v1/auth/me", headers=auth_headers)

        assert resp.status_code == 204
        db.refresh(user)
        db.refresh(membership)
        assert user.is_active is False
        assert user.withdrawn_at is not None
        assert user.student_id.startswith("deleted_")
        assert user.email.endswith("@invalid.local")
        assert user.name == "탈퇴한 사용자"
        assert user.phone is None
        assert user.department is None
        assert user.auth_user_id is None
        assert membership.status == "withdrawn"
        assert membership.left_at is not None

    def test_withdrawn_account_cannot_use_token_or_login(
        self, client, db, auth_headers
    ):
        resp = client.delete("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 204

        me_resp = client.get("/api/v1/auth/me", headers=auth_headers)
        login_resp = client.post("/api/v1/auth/login", json={
            "student_id": "2021000001",
            "password": "Password1!",
        })

        assert me_resp.status_code == 401
        assert login_resp.status_code == 401

    def test_can_register_again_with_same_student_id_and_email(
        self, client, db, auth_headers
    ):
        from src.models.user import EmailVerification, User

        original_user = db.query(User).filter(
            User.student_id == "2021000001",
        ).one()
        original_user_id = original_user.id

        withdraw_resp = client.delete("/api/v1/auth/me", headers=auth_headers)
        assert withdraw_resp.status_code == 204

        with patch("src.services.auth_service.send_verification_email"):
            send_resp = client.post(
                "/api/v1/auth/email-verify/send",
                json={"email": "user@cju.ac.kr"},
            )
        assert send_resp.status_code == 200

        code = db.query(EmailVerification).filter(
            EmailVerification.email == "user@cju.ac.kr",
            EmailVerification.is_used.is_(False),
        ).one().code
        register_resp = client.post("/api/v1/auth/register", json={
            "student_id": "2021000001",
            "password": "NewPassword1!",
            "name": "재가입 사용자",
            "phone": "010-1111-2222",
            "department": "컴퓨터공학과",
            "email": "user@cju.ac.kr",
            "verification_code": code,
            "privacy_consent": {
                "required_agreed": True,
                "optional_agreed": False,
            },
        })

        assert register_resp.status_code == 201
        assert register_resp.json()["id"] != original_user_id
        new_user = db.query(User).filter(User.student_id == "2021000001").one()
        assert new_user.email == "user@cju.ac.kr"
        assert new_user.is_active is True

    def test_active_president_must_transfer_role_first(
        self, client, db, president_headers, seeded_club
    ):
        president = seeded_club["president"]

        resp = client.delete("/api/v1/auth/me", headers=president_headers)

        assert resp.status_code == 409
        assert resp.json()["detail"] == (
            "동아리 회장은 다른 부원에게 회장 권한을 이전한 후 "
            "회원탈퇴할 수 있습니다."
        )
        db.refresh(president)
        assert president.is_active is True
        assert president.withdrawn_at is None

    def test_hard_deletes_linked_supabase_auth_user(self, db):
        from src.core.config import settings
        from src.models.user import User
        from src.services import auth_service

        user = User(
            auth_user_id="00000000-0000-0000-0000-000000000001",
            student_id="WITHDRAW001",
            password_hash="unused",
            name="탈퇴테스트",
            email="withdraw@cju.ac.kr",
            email_verified=True,
        )
        db.add(user)
        db.commit()

        auth_user_id = user.auth_user_id
        supabase = MagicMock()
        with (
            patch.object(settings, "SUPABASE_SERVICE_KEY", "test-service-key"),
            patch(
                "src.services.auth_service.get_supabase_admin_client",
                return_value=supabase,
            ),
        ):
            auth_service.withdraw_user(db, user)

        supabase.auth.admin.delete_user.assert_called_once_with(
            auth_user_id,
            should_soft_delete=False,
        )
        assert user.is_active is False
        assert user.auth_user_id is None

    def test_login_client_does_not_replace_admin_client_session(self, db):
        from src.core.config import settings
        from src.models.user import User
        from src.services import auth_service

        user = User(
            auth_user_id="00000000-0000-0000-0000-000000000002",
            student_id="LOGINCLIENT001",
            password_hash="unused",
            name="로그인테스트",
            email="login-client@cju.ac.kr",
            email_verified=True,
        )
        db.add(user)
        db.commit()

        auth_client = MagicMock()
        expected_session = MagicMock()
        auth_client.auth.sign_in_with_password.return_value.session = expected_session
        admin_client = MagicMock()

        with (
            patch.object(settings, "SUPABASE_SERVICE_KEY", "test-service-key"),
            patch(
                "src.services.auth_service.create_supabase_auth_client",
                return_value=auth_client,
            ),
            patch(
                "src.services.auth_service.get_supabase_admin_client",
                return_value=admin_client,
            ),
        ):
            session = auth_service.create_supabase_session(db, user, "Password1!")

        assert session is expected_session
        auth_client.auth.sign_in_with_password.assert_called_once_with({
            "email": user.email,
            "password": "Password1!",
        })
        admin_client.auth.sign_in_with_password.assert_not_called()
