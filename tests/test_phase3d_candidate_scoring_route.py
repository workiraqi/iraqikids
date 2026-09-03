from app.extensions import db
from app.models import Candidate, Source
from app.services.content_scoring import ContentScoringService


def _make_candidate(app):
    with app.app_context():
        source = Source(
            name="Phase 3D Scoring Source",
            url="https://scoring.example",
            source_type="web",
            language="en",
            quality_score=9,
            is_active=True,
        )
        db.session.add(source)
        db.session.flush()

        candidate = Candidate(
            source_id=source.id,
            title="Creative Art Activity for Children",
            original_url="https://scoring.example/art-activity",
            original_summary="A hands-on creative activity for children.",
            original_body=(
                "Children use simple materials to create, experiment, "
                "explore colors, and discuss what they made."
            ),
            status="new",
        )

        db.session.add(candidate)
        db.session.commit()

        return candidate.id


def test_score_route_saves_scores(app, client, auth):
    candidate_id = _make_candidate(app)

    auth.login()

    response = client.post(
        f"/admin/candidates/{candidate_id}/score",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.relevance_score is not None
        assert candidate.practical_score is not None
        assert candidate.knowledge_score is not None
        assert candidate.adaptability_score is not None
        assert candidate.source_quality_score == 9
        expected_originality = ContentScoringService.estimate_originality(
            title=candidate.title or "",
            summary=candidate.original_summary or "",
            body=candidate.original_body or "",
        )
        assert candidate.originality_score == expected_originality
        assert candidate.overall_score is not None
        assert candidate.content_type is not None
        assert candidate.score_recommendation is not None
        assert candidate.scored_at is not None


def test_score_route_does_not_change_candidate_status(
    app,
    client,
    auth,
):
    candidate_id = _make_candidate(app)

    auth.login()

    with app.app_context():
        before = db.session.get(Candidate, candidate_id)
        assert before.status == "new"

    response = client.post(
        f"/admin/candidates/{candidate_id}/score",
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.status == "new"
        assert candidate.converted_article_id is None
        assert candidate.overall_score is not None