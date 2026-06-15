class TestGetClub:
    def test_not_found(self, client):
        resp = client.get("/api/v1/clubs/nonexistent-id")
        assert resp.status_code == 404

    def test_success(self, client, seeded_club):
        club = seeded_club["club"]
        resp = client.get(f"/api/v1/clubs/{club.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == club.id
        assert data["name"] == "테스트동아리"
        assert data["club_type"] == "central"
        assert data["is_recruiting"] is True
        assert data["description"] == "테스트용 동아리입니다."

    def test_response_includes_tags_field(self, client, seeded_club):
        """tags 필드가 항상 리스트로 반환되는지 확인."""
        club = seeded_club["club"]
        resp = client.get(f"/api/v1/clubs/{club.id}")
        assert resp.status_code == 200
        assert isinstance(resp.json()["tags"], list)


class TestGetClubForm:
    def test_not_found_no_club(self, client):
        resp = client.get("/api/v1/clubs/nonexistent-id/form")
        assert resp.status_code == 404

    def test_success(self, client, seeded_club):
        club = seeded_club["club"]
        form = seeded_club["form"]
        question = seeded_club["question"]

        resp = client.get(f"/api/v1/clubs/{club.id}/form")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == form.id
        assert data["club_id"] == club.id
        assert data["title"] == "2025년 신입부원 모집"
        assert data["is_active"] is True

    def test_form_includes_questions(self, client, seeded_club):
        club = seeded_club["club"]
        question = seeded_club["question"]

        resp = client.get(f"/api/v1/clubs/{club.id}/form")
        assert resp.status_code == 200
        questions = resp.json()["questions"]
        assert len(questions) == 1
        assert questions[0]["id"] == question.id
        assert questions[0]["question_text"] == "지원 동기를 작성해주세요."
        assert questions[0]["question_type"] == "text"
        assert questions[0]["is_required"] is True
        assert questions[0]["order_index"] == 0
