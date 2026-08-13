class TestListClubs:
    def test_returns_all_clubs_without_search(self, client, seeded_club):
        resp = client.get("/api/v1/clubs")

        assert resp.status_code == 200
        assert seeded_club["club"].id in {club["id"] for club in resp.json()}

    def test_searches_by_partial_club_name(self, client, seeded_club):
        resp = client.get("/api/v1/clubs", params={"search": "스트동"})

        assert resp.status_code == 200
        assert [club["id"] for club in resp.json()] == [seeded_club["club"].id]

    def test_search_is_case_insensitive(self, client, db, seeded_club):
        from src.models.club import Club

        club = Club(
            president_id=seeded_club["president"].id,
            name="Dream Lounge Band",
            is_recruiting=False,
        )
        db.add(club)
        db.commit()

        resp = client.get("/api/v1/clubs", params={"search": "lOuNgE"})

        assert resp.status_code == 200
        assert [item["id"] for item in resp.json()] == [club.id]

    def test_searches_by_partial_division(self, client, db, seeded_club):
        from src.models.club import Club

        performance_club = Club(
            president_id=seeded_club["president"].id,
            name="Stage Crew",
            division="\uacf5\uc5f0\uc608\uc220\ubd84\uacfc",
            is_recruiting=True,
        )
        academic_club = Club(
            president_id=seeded_club["president"].id,
            name="Book Circle",
            division="\uad50\uc591\ud559\uc220\ubd84\uacfc",
            is_recruiting=True,
        )
        db.add_all([performance_club, academic_club])
        db.commit()

        resp = client.get("/api/v1/clubs", params={"search": "\uacf5\uc5f0"})

        assert resp.status_code == 200
        assert [item["id"] for item in resp.json()] == [performance_club.id]

    def test_search_matches_name_or_division(self, client, db, seeded_club):
        from src.models.club import Club

        club_matched_by_name = Club(
            president_id=seeded_club["president"].id,
            name="Culture Makers",
            division="\uacf5\uc5f0\uc608\uc220\ubd84\uacfc",
            is_recruiting=True,
        )
        club_matched_by_division = Club(
            president_id=seeded_club["president"].id,
            name="Book Circle",
            division="Culture Division",
            is_recruiting=True,
        )
        db.add_all([club_matched_by_name, club_matched_by_division])
        db.commit()

        resp = client.get("/api/v1/clubs", params={"search": "culture"})

        assert resp.status_code == 200
        assert {item["id"] for item in resp.json()} == {
            club_matched_by_name.id,
            club_matched_by_division.id,
        }

    def test_returns_empty_list_when_name_does_not_match(self, client, seeded_club):
        resp = client.get("/api/v1/clubs", params={"search": "존재하지않는동아리"})

        assert resp.status_code == 200
        assert resp.json() == []


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
