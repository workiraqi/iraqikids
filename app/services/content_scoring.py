import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentScore:
    relevance: int
    practical_value: int
    knowledge_value: int
    arabic_adaptability: int
    source_quality: int
    originality: int
    overall: int
    content_type: str
    recommendation: str
    reasons: tuple[str, ...]


class ContentScoringService:
    CHILD_TERMS = (
        "child",
        "children",
        "kid",
        "kids",
        "toddler",
        "preschool",
        "young learner",
        "young learners",
        "school-age",
        "طفل",
        "أطفال",
        "الطفل",
        "الأطفال",
    )

    CREATIVITY_TERMS = (
        "creative",
        "creativity",
        "imagination",
        "imaginative",
        "art",
        "craft",
        "drawing",
        "painting",
        "invent",
        "invention",
        "curiosity",
        "creative thinking",
        "إبداع",
        "الإبداع",
        "خيال",
        "الفن",
        "رسم",
        "ابتكار",
        "تفكير إبداعي",
    )

    LEARNING_TERMS = (
        "learning",
        "education",
        "teacher",
        "classroom",
        "school",
        "student",
        "students",
        "parent",
        "parents",
        "teaching",
        "learn",
        "تعلم",
        "التعلم",
        "تعليم",
        "التعليم",
        "معلم",
        "معلمون",
        "مدرسة",
        "طلاب",
        "أهل",
        "والدين",
    )

    PRACTICAL_TERMS = (
        "activity",
        "activities",
        "experiment",
        "try",
        "make",
        "build",
        "create",
        "step",
        "steps",
        "materials",
        "hands-on",
        "project",
        "play",
        "workshop",
        "نشاط",
        "أنشطة",
        "تجربة",
        "جرّب",
        "اصنع",
        "بناء",
        "خطوات",
        "مواد",
        "مشروع",
        "لعب",
        "ورشة",
    )

    KNOWLEDGE_TERMS = (
        "research",
        "study",
        "studies",
        "evidence",
        "science",
        "scientific",
        "development",
        "psychology",
        "cognitive",
        "findings",
        "researchers",
        "بحث",
        "دراسة",
        "دراسات",
        "أبحاث",
        "دليل",
        "علم",
        "علمي",
        "تطور",
        "نفسي",
        "معرفي",
        "نتائج",
        "باحثون",
    )

    ADAPTABILITY_TERMS = (
        "simple",
        "home",
        "classroom",
        "family",
        "teacher",
        "parents",
        "materials",
        "everyday",
        "low-cost",
        "accessible",
        "بسيط",
        "منزل",
        "صف",
        "أسرة",
        "معلم",
        "أهل",
        "مواد",
        "متاح",
        "سهل",
    )

    ADULT_CONTEXT_TERMS = (
        "career",
        "workplace",
        "retirement",
        "dating",
        "romantic relationship",
        "menopause",
        "job",
        "office",
        "marriage",
        "fitness",
        "diet",
        "professional success",
        "وظيفة",
        "تقاعد",
        "زواج",
        "حمية",
        "لياقة",
        "مكان العمل",
    )

    @staticmethod
    def _count_groups(text: str, terms: tuple[str, ...]) -> int:
        lowered = text.lower()
        return sum(1 for term in terms if term.lower() in lowered)

    @staticmethod
    def _cap(value: int, maximum: int) -> int:
        return max(0, min(value, maximum))

    @classmethod
    def estimate_originality(
        cls,
        *,
        title: str = "",
        summary: str = "",
        body: str = "",
    ) -> int:
        text = " ".join(
            part.strip()
            for part in (title, summary, body[:6000])
            if part
        )

        if not text:
            return 0

        words = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
        word_count = len(words)

        if word_count < 10:
            return 2

        unique_ratio = len(set(words)) / word_count

        if unique_ratio >= 0.70:
            diversity_score = 5
        elif unique_ratio >= 0.55:
            diversity_score = 4
        elif unique_ratio >= 0.40:
            diversity_score = 3
        elif unique_ratio >= 0.30:
            diversity_score = 2
        else:
            diversity_score = 1

        if word_count >= 120:
            length_score = 3
        elif word_count >= 60:
            length_score = 2
        elif word_count >= 25:
            length_score = 1
        else:
            length_score = 0

        sentences = [
            item.strip()
            for item in re.split(r"[.!?؟]+", text)
            if item.strip()
        ]

        if len(sentences) >= 3:
            normalized_sentences = {
                " ".join(sentence.lower().split())
                for sentence in sentences
            }
            sentence_ratio = len(normalized_sentences) / len(sentences)
            repetition_score = 2 if sentence_ratio >= 0.80 else 1
        else:
            repetition_score = 1

        return cls._cap(
            diversity_score + length_score + repetition_score,
            10,
        )

    @classmethod
    def score(
        cls,
        *,
        title: str = "",
        summary: str = "",
        body: str = "",
        source_quality: int = 5,
        originality: int = 5,
    ) -> ContentScore:
        text = " ".join(
            part.strip()
            for part in (title, summary, body[:6000])
            if part
        )

        child_hits = cls._count_groups(text, cls.CHILD_TERMS)
        creativity_hits = cls._count_groups(
            text,
            cls.CREATIVITY_TERMS,
        )
        learning_hits = cls._count_groups(
            text,
            cls.LEARNING_TERMS,
        )
        practical_hits = cls._count_groups(
            text,
            cls.PRACTICAL_TERMS,
        )
        knowledge_hits = cls._count_groups(
            text,
            cls.KNOWLEDGE_TERMS,
        )
        adaptability_hits = cls._count_groups(
            text,
            cls.ADAPTABILITY_TERMS,
        )
        adult_hits = cls._count_groups(
            text,
            cls.ADULT_CONTEXT_TERMS,
        )

        relevance = (
            child_hits * 8
            + creativity_hits * 3
            + learning_hits * 3
            - adult_hits * 6
        )
        relevance = cls._cap(relevance, 30)

        practical_value = cls._cap(
            practical_hits * 4,
            20,
        )

        knowledge_value = cls._cap(
            knowledge_hits * 3,
            15,
        )

        arabic_adaptability = cls._cap(
            5 + adaptability_hits * 2,
            15,
        )

        source_quality = cls._cap(
            int(source_quality),
            10,
        )

        originality = cls._cap(
            int(originality),
            10,
        )

        if practical_hits >= 2 and practical_hits >= knowledge_hits:
            content_type = "activity"
            overall = round(
                relevance
                + practical_value * 1.25
                + arabic_adaptability
                + source_quality * 1.5
                + originality * 1.5
            )
        elif knowledge_hits >= 2:
            content_type = "research"
            overall = round(
                relevance
                + knowledge_value * (25 / 15)
                + arabic_adaptability * (10 / 15)
                + source_quality * 2
                + originality * 1.5
            )
        else:
            content_type = "general"
            overall = (
                relevance
                + practical_value
                + knowledge_value
                + arabic_adaptability
                + source_quality
                + originality
            )

        overall = cls._cap(overall, 100)

        reasons = []

        if relevance >= 24:
            reasons.append("صلة قوية بالأطفال والتعلم والإبداع")
        elif relevance >= 12:
            reasons.append("صلة مقبولة بمجال المشروع")
        else:
            reasons.append("صلة ضعيفة بمجال المشروع")

        if practical_value >= 12:
            reasons.append("يتضمن قيمة عملية أو نشاطًا قابلًا للتطبيق")

        if knowledge_value >= 9:
            reasons.append("يتضمن قيمة معرفية أو بحثية")

        if arabic_adaptability >= 10:
            reasons.append("قابل للتكييف بسهولة للقارئ العربي")

        if adult_hits:
            reasons.append("يحتوي على سياق بالغين يحتاج إلى مراجعة")

        if relevance < 12:
            recommendation = "reject_suggested"
        elif overall >= 85:
            recommendation = "high_priority"
        elif overall >= 70:
            recommendation = "recommended"
        elif overall >= 55:
            recommendation = "human_review"
        elif overall >= 40:
            recommendation = "weak"
        else:
            recommendation = "reject_suggested"

        return ContentScore(
            relevance=relevance,
            practical_value=practical_value,
            knowledge_value=knowledge_value,
            arabic_adaptability=arabic_adaptability,
            source_quality=source_quality,
            originality=originality,
            overall=overall,
            content_type=content_type,
            recommendation=recommendation,
            reasons=tuple(reasons),
        )