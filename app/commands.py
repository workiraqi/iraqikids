import os
from datetime import datetime, timedelta, timezone

import click
from flask import Flask

from app.extensions import db
from app.models import Article, Category, SiteSettings, Theme, User
from app.services import DEFAULT_THEME, ThemeService
from app.services.publishing import PublishingService


CATEGORY_SEED = [
    ("الإبداع والفنون", "creativity-arts"),
    ("أنشطة والطفل المبدع", "creative-child-activities"),
    ("علوم وابتكار", "science-innovation"),
    ("الأهل والمعلمون", "parents-teachers"),
    ("من العالم", "from-the-world"),
    ("أبحاث ودراسات", "research-studies"),
    ("كتب وحكايات", "books-stories"),
    ("فيديو", "videos"),
]

ARTICLE_SEED = [
    ("حين يصبح الظل أداة للرسم", "shadow-as-a-drawing-tool", "تجربة بسيطة تحول الضوء والأشياء اليومية إلى مرسم متغير.", "<p>ضع جسمًا مألوفًا قرب نافذة، وثبّت ورقة عند نهاية ظله. تتبّع الخط ثم حرّك الجسم قليلًا وكرر المحاولة.</p><h2>ماذا نلاحظ؟</h2><p>الظل لا يحتفظ بالشكل نفسه؛ فالضوء والمسافة يغيّران الرسم. اطلب من الطفل أن يتوقع الخط التالي قبل رسمه.</p>", "creativity-arts", True),
    ("جسر من ورقة واحدة", "one-sheet-paper-bridge", "اختبار هندسي صغير لفهم كيف يمنح الشكلُ الورقَ قوة إضافية.", "<p>اصنع جسرًا بين كتابين باستخدام ورقة واحدة. جرّب الورقة مسطحة، ثم اطوها مثل المروحة وقارن عدد القطع التي تحملها.</p><h2>غيّر الفكرة</h2><p>هل تعمل الطيات الواسعة مثل الطيات الضيقة؟ سجّل النتيجة بدل البحث عن إجابة واحدة.</p>", "science-innovation", True),
    ("ارسم صوت المطر", "draw-the-sound-of-rain", "نشاط يجمع الإصغاء والحركة والتعبير البصري من دون نموذج جاهز.", "<p>استمع إلى المطر أو إلى تسجيل قصير له، ثم اختر خطوطًا وألوانًا تمثل ما تسمعه.</p><blockquote>لا توجد طريقة صحيحة لرسم الصوت؛ المهم أن تشرح اختيارك.</blockquote><p>قارن بين رسمين واسأل كيف اختلف الإيقاع.</p>", "creative-child-activities", True),
    ("خمسة أسئلة تفتح باب الخيال", "five-questions-for-imagination", "بدل إعطاء الحل، تساعد هذه الأسئلة الطفل على توسيع فكرته بنفسه.", "<p>اسأل: ماذا لو غيّرنا الحجم؟ ماذا يحدث لو اختفت إحدى الأدوات؟ لمن يمكن أن تكون الفكرة مفيدة؟</p><h2>دور البالغ</h2><p>امنح الطفل وقتًا للصمت والتفكير. لا تحوّل السؤال المفتوح إلى اختبار بإجابة مخفية.</p>", "parents-teachers", True),
    ("دفتر الملاحظة الياباني", "japanese-observation-notebook", "فكرة صفية مستلهمة من قيمة الملاحظة الدقيقة قبل التفسير.", "<p>اختر ورقة نبات أو أداة صغيرة، وخصص خمس دقائق لرسم تفاصيلها من أكثر من زاوية.</p><p>هذه المادة مثال تحريري تجريبي وليست نقلًا من مصدر خارجي.</p>", "from-the-world", False),
    ("لماذا نحتاج إلى أكثر من حل؟", "why-more-than-one-solution", "تمرين قصير على الطلاقة والمرونة بدل التوقف عند أول إجابة.", "<p>اختر مشكلة يومية بسيطة واكتب ثلاثة حلول مختلفة على الأقل. بعد ذلك صنّف الحلول إلى سريع، غريب، وقابل للتجربة.</p><h2>الفكرة الأساسية</h2><p>تعدد البدائل يدرّب العقل على الانتقال بين الاحتمالات.</p>", "research-studies", False),
    ("حكاية تبدأ من شيء مفقود", "story-from-a-missing-object", "طريقة لبناء حكاية مع الطفل عبر سؤال واحد وصور ذهنية متتابعة.", "<p>اختر شيئًا صغيرًا وتخيل أنه اختفى صباحًا. من لاحظ غيابه أولًا؟ وأين ترك علامة؟</p><p>اكتب جملة واحدة بالتناوب مع الطفل حتى تكتمل الحكاية.</p>", "books-stories", False),
    ("مسرح الأشكال الورقية", "paper-shape-theatre", "قص ولصق وتمثيل يحول الأشكال الهندسية إلى شخصيات تتكلم.", "<p>قص دوائر ومثلثات ومستطيلات، ثم اجمعها في شخصيات. امنح كل شخصية طريقة حركة وصوتًا مختلفًا.</p><h2>بعد العرض</h2><p>اسأل كيف غيّر الشكل شخصية البطل.</p>", "creativity-arts", False),
    ("مختبر فقاعات المطبخ", "kitchen-bubble-lab", "ملاحظة علمية آمنة لأشكال الفقاعات وما يحدث عند اجتماعها.", "<p>اخلط ماءً وقليلًا من سائل التنظيف بمساعدة بالغ، ثم انفخ عبر شفاطة من دون ابتلاع السائل.</p><p>راقب حدود الفقاعات عندما تلتقي وارسم ما تراه.</p>", "science-innovation", False),
    ("كيف نناقش رسمة بلا أحكام؟", "talk-about-art-without-judgment", "عبارات تساعد الأهل والمعلمين على وصف العمل وفتح حوار بدل تقييمه بسرعة.", "<p>ابدأ بما تراه: لاحظت أنك كررت هذا الخط. ثم اسأل: ما الجزء الذي استمتعت به أكثر؟</p><p>تجنب تحويل كل عمل إلى جميل أو غير جميل؛ فالوصف يفتح مساحة أوسع للتعبير.</p>", "parents-teachers", False),
]


def seed_core() -> None:
    settings = db.session.get(SiteSettings, 1)
    if settings is None:
        db.session.add(SiteSettings(id=1, site_name="Mikhyal", arabic_site_name="مِخيال", short_description="منصة عربية للإبداع لدى الأطفال.", hero_title="المكان الذي تتحول فيه الأسئلة إلى تجارب.", hero_subtitle="مختبر رقمي للفن والعلوم والخيال يساعد الطفل على أن يصنع ويكتشف بنفسه.", footer_text="مِخيال — منصة عربية للإبداع لدى الأطفال"))

    theme = db.session.scalar(db.select(Theme).where(Theme.is_default.is_(True)))
    if theme is None:
        theme = Theme(**DEFAULT_THEME, is_default=True, is_active=True)
        db.session.add(theme)
    elif ThemeService.get_active() is None:
        ThemeService.activate(theme)

    existing_slugs = set(db.session.scalars(db.select(Category.slug)))
    for sort_order, (title, slug) in enumerate(CATEGORY_SEED, start=1):
        if slug not in existing_slugs:
            db.session.add(Category(title=title, slug=slug, visible=True, sort_order=sort_order, accent_color=DEFAULT_THEME["lime"]))
    db.session.commit()

    categories = {category.slug: category for category in db.session.scalars(db.select(Category))}
    existing_article_slugs = set(db.session.scalars(db.select(Article.slug)))
    now = datetime.now(timezone.utc)
    for offset, (title, slug, summary, body, category_slug, featured) in enumerate(ARTICLE_SEED):
        if slug in existing_article_slugs:
            continue
        article = Article(title=title, slug=slug, summary=summary, body=body, category_id=categories[category_slug].id, status="draft", featured=featured, author="فريق المختبر")
        PublishingService.submit_for_review(article)
        PublishingService.approve(article)
        PublishingService.publish(article)
        article.published_at = now - timedelta(days=offset)
        db.session.add(article)
    db.session.commit()


def register_commands(app: Flask) -> None:
    @app.cli.command("seed-dev")
    def seed_dev_command():
        """Create idempotent development settings, theme, categories, and articles."""
        seed_core()
        click.echo("Development seed completed.")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create or update an admin using environment credentials."""
        email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("ADMIN_PASSWORD", "")
        if not email or not password:
            raise click.ClickException("ADMIN_EMAIL and ADMIN_PASSWORD are required.")
        if len(password) < 12:
            raise click.ClickException("ADMIN_PASSWORD must be at least 12 characters.")
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None:
            user = User(email=email, display_name="مدير الموقع", role="admin", active=True)
            db.session.add(user)
        else:
            user.role = "admin"
            user.active = True
        user.set_password(password)
        db.session.commit()
        click.echo(f"Admin ready: {email}")
