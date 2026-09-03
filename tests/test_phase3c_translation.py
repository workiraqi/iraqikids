import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.translation import (
    ArabicTranslationService,
    TranslationError,
)


def _candidate(body="Original body"):
    return SimpleNamespace(
        title="Creative Activities for Children",
        original_summary="A short source summary.",
        original_body=body,
        source=SimpleNamespace(language="en"),
    )


def _response(payload):
    return SimpleNamespace(
        output_text=json.dumps(payload, ensure_ascii=False)
    )


def test_translation_returns_expected_arabic_fields():
    response = _response(
        {
            "arabic_title": "أنشطة إبداعية للأطفال",
            "arabic_summary": "أفكار عملية لتنمية الإبداع.",
            "arabic_body": "يمكن للأطفال استكشاف الفن والتجريب من خلال أنشطة بسيطة وممتعة.",
        }
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        result = ArabicTranslationService.translate_candidate(
            _candidate()
        )

    assert result["arabic_title"] == "أنشطة إبداعية للأطفال"
    assert result["arabic_summary"] == "أفكار عملية لتنمية الإبداع."
    assert result["arabic_body"] == "يمكن للأطفال استكشاف الفن والتجريب من خلال أنشطة بسيطة وممتعة."


def test_translation_limits_source_body_to_6000_characters():
    body = "A" * 8000

    response = _response(
        {
            "arabic_title": "عنوان",
            "arabic_summary": "ملخص",
            "arabic_body": "متن عربي مختصر",
        }
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        ArabicTranslationService.translate_candidate(
            _candidate(body)
        )

        kwargs = openai.return_value.responses.create.call_args.kwargs
        sent_input = kwargs["input"]

    body_section = sent_input.split(
        "BODY:\n", 1
    )[1].split(
        "\n\nSOURCE LANGUAGE:", 1
    )[0]

    assert len(body_section) == 6000
    assert "A" * 6000 == body_section


def test_translation_accepts_json_code_fence():
    payload = {
        "arabic_title": "عنوان عربي",
        "arabic_summary": "ملخص عربي",
        "arabic_body": "متن عربي",
    }

    response = SimpleNamespace(
        output_text=(
            "```json\n"
            + json.dumps(payload, ensure_ascii=False)
            + "\n```"
        )
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        result = ArabicTranslationService.translate_candidate(
            _candidate()
        )

    assert result == payload


def test_translation_rejects_invalid_json():
    response = SimpleNamespace(
        output_text="this is not json"
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        with pytest.raises(TranslationError):
            ArabicTranslationService.translate_candidate(
                _candidate()
            )


def test_translation_rejects_missing_arabic_title():
    response = _response(
        {
            "arabic_title": "",
            "arabic_summary": "ملخص",
            "arabic_body": "متن",
        }
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        with pytest.raises(TranslationError):
            ArabicTranslationService.translate_candidate(
                _candidate()
            )


def test_translation_uses_configured_model():
    response = _response(
        {
            "arabic_title": "عنوان",
            "arabic_summary": "ملخص",
            "arabic_body": "متن",
        }
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        ArabicTranslationService.translate_candidate(
            _candidate()
        )

        kwargs = openai.return_value.responses.create.call_args.kwargs

    assert kwargs["model"] == ArabicTranslationService.MODEL


def test_translation_prompt_requires_short_editorial_body():
    response = _response(
        {
            "arabic_title": "عنوان",
            "arabic_summary": "ملخص",
            "arabic_body": "متن",
        }
    )

    with patch("app.services.translation.OpenAI") as openai:
        openai.return_value.responses.create.return_value = response

        ArabicTranslationService.translate_candidate(
            _candidate()
        )

        kwargs = openai.return_value.responses.create.call_args.kwargs
        instructions = kwargs["instructions"]

    assert "must not exceed 100 words" in instructions
    assert "Prefer 60 to 90 words" in instructions
    assert "do not reproduce all details" in instructions