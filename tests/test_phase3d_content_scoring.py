from app.services.content_scoring import ContentScoringService


def test_child_activity_is_recommended():
    result = ContentScoringService.score(
        title="Creative Art Activities for Children",
        body=(
            "Children can make art, experiment, draw "
            "and build simple projects at home."
        ),
    )

    assert result.content_type == "activity"
    assert result.relevance >= 12
    assert result.practical_value >= 12
    assert result.overall >= 70
    assert result.recommendation == "recommended"


def test_child_research_is_recommended():
    result = ContentScoringService.score(
        title="Study Finds Creative Play Supports Child Development",
        body=(
            "Researchers studied children and found evidence "
            "that imaginative play supports cognitive development "
            "and learning in school."
        ),
    )

    assert result.content_type == "research"
    assert result.relevance >= 12
    assert result.knowledge_value >= 9
    assert result.overall >= 70
    assert result.recommendation == "recommended"


def test_adult_creativity_article_is_not_recommended():
    result = ContentScoringService.score(
        title="Creative Thinking for Career Success",
        body=(
            "Professionals can use creative thinking to improve "
            "career success, workplace performance, jobs "
            "and office relationships."
        ),
        source_quality=10,
        originality=10,
    )

    assert result.relevance < 12
    assert result.recommendation == "reject_suggested"


def test_low_relevance_cannot_be_rescued_by_source_quality():
    result = ContentScoringService.score(
        title="Professional Career Development",
        body=(
            "A workplace guide for career success, office "
            "relationships and professional development."
        ),
        source_quality=10,
        originality=10,
    )

    assert result.relevance < 12
    assert result.recommendation == "reject_suggested"


def test_scores_never_exceed_limits():
    result = ContentScoringService.score(
        title=(
            "Children Kids Creative Creativity Art Craft "
            "Learning Education Activities"
        ),
        body=(
            "Children kids toddlers preschool students teachers "
            "creative creativity imagination art craft drawing "
            "painting invent curiosity learning education school "
            "activity experiment make build create steps materials "
            "hands-on project play workshop research study evidence "
            "science scientific development psychology cognitive "
            "findings researchers simple home classroom family."
        ),
        source_quality=999,
        originality=999,
    )

    assert 0 <= result.relevance <= 30
    assert 0 <= result.practical_value <= 20
    assert 0 <= result.knowledge_value <= 15
    assert 0 <= result.arabic_adaptability <= 15
    assert 0 <= result.source_quality <= 10
    assert 0 <= result.originality <= 10
    assert 0 <= result.overall <= 100


def test_negative_source_values_are_clamped_to_zero():
    result = ContentScoringService.score(
        title="Creative Activities for Children",
        body="Children can create and experiment.",
        source_quality=-50,
        originality=-20,
    )

    assert result.source_quality == 0
    assert result.originality == 0


def test_arabic_child_activity_is_recognized():
    result = ContentScoringService.score(
        title="أنشطة فنية إبداعية للأطفال",
        body=(
            "يمكن للأطفال تنفيذ نشاط فني بسيط في المنزل، "
            "والرسم والتجريب وصنع مشروع باستخدام مواد متاحة."
        ),
    )

    assert result.relevance >= 12
    assert result.practical_value > 0
    assert result.recommendation != "reject_suggested"


def test_reasons_explain_the_score():
    result = ContentScoringService.score(
        title="Creative Art Activities for Children",
        body=(
            "Children can make art and experiment "
            "with simple projects at home."
        ),
    )

    assert result.reasons
    assert any(
        "صلة" in reason
        for reason in result.reasons
    )


def test_high_quality_activity_can_reach_high_priority():
    result = ContentScoringService.score(
        title="Creative Art Activities for Children",
        body=(
            "Children can make art, experiment, draw, paint, "
            "build and create simple hands-on projects at home "
            "using accessible everyday materials."
        ),
        source_quality=10,
        originality=10,
    )

    assert result.content_type == "activity"
    assert result.relevance >= 12
    assert result.overall >= 85
    assert result.recommendation == "high_priority"
def test_originality_estimator_penalizes_very_short_text():
    score = ContentScoringService.estimate_originality(
        title="Kids art",
    )

    assert score == 2


def test_originality_estimator_rewards_richer_text():
    score = ContentScoringService.estimate_originality(
        title="Creative art for children",
        summary=(
            "A practical activity that encourages imagination "
            "and experimentation."
        ),
        body=(
            "Children explore different materials and colors. "
            "They create their own designs and compare different "
            "possibilities. The activity encourages experimentation, "
            "observation, discussion, imagination, choice, and reflection "
            "while allowing every child to produce a different result."
        ),
    )

    assert score >= 7


def test_originality_estimator_is_capped_at_ten():
    score = ContentScoringService.estimate_originality(
        body=" ".join(
            f"unique_word_{i}"
            for i in range(300)
        )
    )

    assert 0 <= score <= 10