import json

from openai import OpenAI


class TranslationError(RuntimeError):
    pass


class ArabicTranslationService:
    MODEL = "gpt-5.6-luna"

    @classmethod
    def translate_candidate(cls, candidate):
        client = OpenAI()

        original_body = (candidate.original_body or "")[:6000]

        source_text = f"""
TITLE:
{candidate.title or ""}

SUMMARY:
{candidate.original_summary or ""}

BODY:
{original_body}

SOURCE LANGUAGE:
{candidate.source.language or "unknown"}
""".strip()

        instructions = """
You are an Arabic editorial translator for Iraqi Kids, an educational platform focused on children, creativity, science, learning, parents, and teachers.

Translate and editorially adapt the supplied source material into clear Modern Standard Arabic.

Rules:
- Preserve factual meaning.
- Do not invent facts not present in the source.
- Do not exaggerate or sensationalize.
- Produce natural Arabic, not literal machine translation.
- Keep scientific names, organizations, dates, and numbers accurate.
- The Arabic title should be concise and journalistic.
- The Arabic summary should be one concise sentence.
- The Arabic body must be a concise original editorial adaptation based ONLY on the supplied material.
- Do not translate the source sentence by sentence and do not reproduce all details.
- Select only the most important idea, facts, and useful practical points.
- The Arabic body must not exceed 100 words.
- Prefer 60 to 90 words when that is sufficient.
- If the source contains only limited information, make the Arabic body even shorter.

Return ONLY valid JSON with exactly these keys:
{
  "arabic_title": "...",
  "arabic_summary": "...",
  "arabic_body": "..."
}
""".strip()

        try:
            response = client.responses.create(
                model=cls.MODEL,
                instructions=instructions,
                input=source_text,
            )
            raw = response.output_text.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            data = json.loads(raw.strip())
        except Exception as exc:
            raise TranslationError(str(exc)) from exc

        title = (data.get("arabic_title") or "").strip()
        summary = (data.get("arabic_summary") or "").strip()
        body = (data.get("arabic_body") or "").strip()

        if not title:
            raise TranslationError("لم يُرجع النموذج عنوانًا عربيًا صالحًا.")

        return {
            "arabic_title": title,
            "arabic_summary": summary,
            "arabic_body": body,
        }
