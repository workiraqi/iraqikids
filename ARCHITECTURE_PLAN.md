# Iraqi Kids — Architecture Plan

> نطاق هذه الوثيقة: تحليل `02_immersive_lab.html` واقتراح الأساس المعماري فقط. لا تتضمن تنفيذ PHASE 1 أو أي اتصال بالدومين أو خدمات Production.

## 1. خلاصة تحليل المرجع البصري

القالب الحالي صفحة عربية RTL أحادية تعتمد على واجهة داكنة غامرة، وتتميز بـ:

- شريط تنقل ثابت فوق تدرج شفاف.
- Hero كبير بخلفية شبكية، وهجين لونيين (blobs)، وثلاث بطاقات عائمة.
- عنوان ضخم عالي التباين مع لون Highlight، ووصف وCTA مزدوج.
- شبكة بطاقات editorial غير متناظرة (`1.3fr / .7fr / .7fr`) مع بطاقة رئيسية ممتدة.
- ألوان أساسية حالية: `#0d1220`, `#141b2d`, `#f7f8fb`, `#a8b0c2`, `#d9ff64`, `#7ce7ff`, `#ff8cc8`.
- حواف مستديرة كبيرة، حدود منخفضة التباين، Hover رأسي، وحركة Reveal عبر `IntersectionObserver`.
- استجابة جيدة مبدئيًا عند 960px و640px، مع إخفاء العناصر العائمة وروابط سطح المكتب.

نقاط التحسين عند التحويل إلى نظام فعلي: إزالة CSS وJavaScript المضمّنين، استبدال الألوان الصريحة بمتغيرات Theme، استكمال قائمة الجوال، تحسين حالات التركيز وتقليل الحركة، ومنع محتوى الإدارة من كسر التخطيط.

## 2. القرارات التقنية

- Backend: Flask بتطبيق Factory وBlueprints، دون `app.py` ضخم.
- Rendering: Jinja2 وHTML دلالي، RTL أولًا، مع JavaScript صغير تدريجي التحسين.
- ORM/Migrations: SQLAlchemy 2 + Flask-SQLAlchemy + Alembic/Flask-Migrate.
- Database: SQLite للتطوير، PostgreSQL للإنتاج عبر `DATABASE_URL`، من دون اختلافات منطقية بينهما.
- Validation/Admin forms: Flask-WTF وWTForms مع CSRF.
- Authentication: Flask-Login، hashing عبر Werkzeug/Argon2، وأدوار وصلاحيات إدارية.
- Content sanitization: Bleach بسياسة عناصر وسمات محددة.
- Fetching: HTTPX + feedparser + BeautifulSoup داخل adapters مستقلة.
- Tests: pytest، pytest-flask، factory-boy (اختياري)، وقاعدة بيانات اختبار معزولة.
- Assets: CSS/JS محلية ومنظمة؛ لا Framework واجهة ثقيل في المرحلة الأولى.

## 3. هيكل المجلد النهائي المقترح

```text
iraqikids/
├── app/
│   ├── __init__.py              # create_app وتهيئة الإضافات
│   ├── config.py
│   ├── extensions.py
│   ├── commands.py
│   ├── models/
│   │   ├── auth.py
│   │   ├── content.py
│   │   ├── taxonomy.py
│   │   ├── sources.py
│   │   ├── videos.py
│   │   ├── media.py
│   │   ├── appearance.py
│   │   └── audit.py
│   ├── public/                   # الصفحة العامة والمقالات والبحث والعالم
│   ├── admin/                    # Blueprints ونماذج الإدارة حسب المجال
│   ├── auth/
│   ├── services/
│   │   ├── publishing.py
│   │   ├── search.py
│   │   ├── deduplication.py
│   │   └── audit.py
│   ├── fetchers/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── rss.py
│   │   └── website.py
│   ├── ai/                       # Interfaces وسياسات الـdraft، لا نشر تلقائي
│   ├── translation/
│   ├── media/
│   ├── videos/                   # allowlist وبناء embed الآمن
│   ├── templates/
│   │   ├── base.html
│   │   ├── partials/
│   │   ├── components/
│   │   ├── home/
│   │   ├── articles/
│   │   ├── videos/
│   │   ├── search/
│   │   └── admin/
│   └── static/
│       ├── css/{tokens,base,layout,components,pages,admin}.css
│       ├── js/{site,reveal,video-consent,admin-theme-preview}.js
│       ├── images/
│       └── uploads/
├── migrations/
├── seeds/
├── tests/{unit,integration,security}/
├── instance/                     # أسرار وSQLite محلي؛ مستبعد من Git
├── scripts/
├── docs/
├── .env.example
├── pyproject.toml
├── wsgi.py
├── README.md
└── ARCHITECTURE_PLAN.md
```

## 4. نموذج البيانات

كل الجداول تستخدم مفاتيح رقمية/UUID، وحقول `created_at` و`updated_at` وتوقيت UTC، مع فهارس للحالة والتاريخ والـslug والمفاتيح الأجنبية.

### الإدارة والهوية

- `User`: email، password_hash، display_name، role، active، last_login_at.
- `SiteSettings`: site_name، arabic_site_name، descriptions، hero copy، footer، logo/favicon media IDs. سجل مفرد مُدار.
- `Theme`: name، token values، is_active، is_default، timestamps. يسمح لاحقًا بالـpresets؛ Theme واحد فعال.
- `HomepageSection`: section_key، title، visible، sort_order، config محدود ومتحقق منه.
- `HomepageSelection`: section، content_type، object_id، sort_order؛ لا تخزين قائمة كـJSON غير منضبط.
- `FloatingHighlight`: eyebrow، title، target URL/content reference، position، visible، sort_order.

### المحتوى والتصنيفات

- `Category`: parent_id اختياري، title، slug، description، icon، accent_color، visible، sort_order.
- `TaxonomyTerm`: vocabulary (`age`, `skill`, `country`, `environment`, `activity_type`)، name، slug، metadata.
- `Article`: الحقول التحريرية المطلوبة، category_id، source metadata، status، featured، approved/published timestamps، author/editor relations.
- جداول ربط many-to-many بين المحتوى و`TaxonomyTerm`، بدل أعمدة نصية متعددة القيم.
- `Activity`, `Book`, `CreativeChallenge`: جداول مستقلة لأن لكل نوع حقول وسلوكًا خاصًا؛ تشترك في mixins للحالة، slug، النشر والصورة.
- `CreativeChallenge`: title، description، instructions، materials، duration، active_from/to، featured، status.
- `MediaAsset`: storage path، original filename، MIME، size، dimensions، alt، caption، credit، source_url، checksum.

### المصادر وسير التحرير

- `Source`: الحقول المحددة، source_type، active/fetch_enabled، priority، trust_score، fetch adapter key وإعدادات آمنة.
- `FetchRun`: source_id، started/finished، status، counts، error summary.
- `Candidate`: النصوص الأصلية المختصرة وURL والصورة واللغة والتاريخ والدرجات والحالة وfingerprint.
- `CandidateDraft`: AI/editorial output، prompt/model metadata، claims/inferences notes، revision؛ لا يغيّر `Article` المنشور مباشرة.
- `VideoSource`: مصدر مستقل أو subtype واضح من Source؛ يُفضّل جدول مستقل لتطبيق allowlist وحقول provider.
- `VideoCandidate`: provider، video_id، canonical/source data، metadata، status، fingerprint.
- `Video`: جميع الحقول المطلوبة، مع `provider` و`video_id` فقط للتضمين، وحقول “جرّب بعد المشاهدة”.
- `AuditLog`: event_type، actor، target، timestamp، metadata منقّحة بلا أسرار.

يجب تنفيذ حالات الانتقال عبر service layer بقواعد صريحة؛ لا يمكن الانتقال من Candidate إلى Published مباشرة، ولا يجوز للـfetcher أو AI استدعاء النشر.

## 5. أقسام لوحة الإدارة

- Dashboard: العدادات، أخطاء وآخر عمليات الجلب.
- Content: Articles، Activities، Challenges، Books، Videos.
- Editorial: Candidates، Video Candidates، معاينة Draft والمصدر والدرجات.
- Sources: Article Sources، Video Sources، تشغيل Fetch يدوي.
- Taxonomy: Categories، Ages، Skills، Countries، Environment، Activity Types.
- Media: الصور والبيانات الوصفية والاستبدال.
- Appearance: Branding، Theme مع live preview، Homepage وترتيب أقسامها.
- System: AI settings (أسرارها خارج DB أو مشفرة)، Logs، Users.

الصلاحيات المقترحة: `admin`, `editor`, `reviewer` مع فصل صلاحية الاعتماد والنشر عند الحاجة.

## 6. المسارات العامة

```text
/                         الصفحة الرئيسية الديناميكية
/articles                 قائمة المقالات مع pagination/filters
/articles/<slug>          صفحة المقال
/activities[/<slug>]      الأنشطة
/challenges[/<slug>]      التحديات
/books[/<slug>]           الكتب والحكايات
/videos                   مكتبة الفيديو
/videos/<slug>            مشاهدة آمنة + جرّب بعد المشاهدة
/category/<slug>          محتوى التصنيف
/world                    استكشاف الدول
/world/<country-slug>     محتوى دولة
/search                   بحث موحد مع filters
/sitemap.xml
/robots.txt
/admin/...                لوحة الإدارة المحمية
```

تُستخدم canonical URLs وBreadcrumbs وJSON-LD (`Article`, `VideoObject`) في القوالب المختصة.

## 7. سير المصادر والمقالات

```text
Source → FetchRun → adapter.normalize() → Candidate
       → URL/content fingerprint deduplication
       → relevance analysis (optional/manual trigger)
       → Arabic editorial draft
       → human review → approved → explicit publish
```

- واجهة `BaseFetcher` تعيد عناصر normalized ولا تكتب مقالات.
- Registry يربط `source_type/adapter_key` بالمحوّل دون شروط متفرقة.
- Deduplication على canonical URL + normalized title + content fingerprint، مع score للمراجعة لا حذف غامض.
- نخزن excerpt وmetadata الضرورية فقط، لا نسخة كاملة من المقال الأجنبي.
- كل Draft يحتفظ بإسناد المصدر، ويُظهر الاستنتاجات بوضوح للمحرر.
- المجدول المستقبلي يشغّل fetch فقط وينتج Candidates، ولا يمتلك مسار نشر.

## 8. سير الفيديو والتضمين الآمن

```text
VideoSource → VideoCandidate → review → approved → explicit publish → safe player
```

- لا يقبل الإداري HTML أو iframe؛ يقبل canonical URL أو `provider + video_id` بعد التحقق.
- Backend يبني الرابط من allowlist ثابتة للمزوّدين، مثل YouTube عبر `youtube-nocookie.com`، وVimeo عند اعتماده.
- التحقق من شكل `video_id` لكل provider ومنع URL schemes/hosts غير المعتمدة.
- Player بصورة مصغرة وزر تشغيل؛ iframe لا يُنشأ قبل تفاعل المستخدم.
- `sandbox`, `allow`, `referrerpolicy` وCSP `frame-src` بأقل صلاحيات، بلا autoplay.
- المواد المرتبطة تأتي من قاعدة الموقع ومن المنشور فقط.

## 9. نظام Theme والهوية

تُعرّف قائمة tokens مسماة ومتحققًا منها، مثل:

```css
:root {
  --color-bg: #0d1220;
  --color-bg-secondary: #101728;
  --color-panel: #141b2d;
  --color-text: #f7f8fb;
  --color-text-muted: #a8b0c2;
  --color-primary: #d9ff64;
  --color-secondary: #6a5cff;
  --color-lime: #d9ff64;
  --color-cyan: #7ce7ff;
  --color-pink: #ff8cc8;
  --color-border: #283149;
  --color-button: #d9ff64;
  --color-hover: #4c597a;
}
```

- القيم الافتراضية مشتقة من القالب، مع إضافة tokens للألوان الصريحة المتبقية.
- `ThemeService` يقرأ Theme الفعال مع cache قصير/invalidation عند الحفظ، ثم يولّد CSS variables فقط، لا CSS حر.
- التحقق الصارم من القيم (ألوان Hex مثلًا) يمنع CSS injection.
- Live preview يعمل داخل صفحة الإدارة على draft محلي قبل الحفظ؛ Reset يعيد preset الافتراضي.
- Branding ونسخ Hero لا تثبت اسم “مخيال” في القوالب؛ الاسم الحالي seed افتراضي فقط.

## 10. تحويل Prototype إلى Jinja دون فقد الهوية

1. استخراج head/metadata والهيكل العام إلى `base.html`، ثم header/footer إلى partials.
2. تحويل Hero إلى component يستقبل SiteSettings وCTA والبطاقات العائمة، مع نفس grid/blobs/typography.
3. تحويل `.tile` إلى macro/card variants (`default`, `lime`, `cyan`, `pink`, `large`)؛ البيانات من Category/featured content، والvariant من قيم مقيدة لا CSS حر.
4. تقسيم الصفحة إلى partial لكل section، وتحميلها وفق `HomepageSection.sort_order/visible`.
5. نقل tokens إلى `tokens.css`، القواعد العامة إلى `base/layout`، والبطاقات والـCTA إلى `components.css`.
6. نقل reveal/menu إلى ملفات JS صغيرة؛ احترام `prefers-reduced-motion` وإبقاء المحتوى ظاهرًا عند تعطيل JS.
7. الحفاظ على النسب والمساحات والتدرجات والـeditorial hierarchy، مع ضبط mobile navigation وfocus states والتباين.
8. استخدام صور محلية responsive وplaceholder مصمم، وتحميل كسول لما تحت الطية.

## 11. الأمان والخصوصية

- CSRF لكل mutation، cookies `Secure/HttpOnly/SameSite=Lax` في الإنتاج، تدوير session عند login.
- password hashing قوي، rate limiting لتسجيل الدخول، ورسائل خطأ لا تكشف الحسابات.
- صلاحيات server-side لكل إجراء، وسجل audit للاعتماد والنشر والتغييرات الحساسة.
- Sanitization لـrich text، escaping افتراضي في Jinja، ولا `|safe` إلا بعد sanitization.
- Upload allowlist، فحص MIME والتوقيع الفعلي، أسماء عشوائية، حد للحجم، ومعالجة الصور خارج مسار التنفيذ.
- حماية SSRF: HTTPS/HTTP فقط، DNS/IP checks، منع الشبكات الخاصة وredirect revalidation، timeouts وحدود تنزيل.
- Security headers: CSP دقيقة، `X-Content-Type-Options`, `Referrer-Policy`, HSTS في الإنتاج، و`frame-ancestors` بدل الاعتماد على X-Frame-Options وحده.
- لا حسابات أطفال أو تعليقات أو tracking افتراضي. Analytics اختياري ومحدود بعد موافقة إدارية واضحة.
- الأسرار عبر environment/secret store لا داخل قاعدة البيانات أو Git.

## 12. Dependencies المقترحة

Runtime الأساسية:

```text
Flask
Flask-SQLAlchemy
Flask-Migrate
Flask-Login
Flask-WTF
Flask-Limiter
psycopg[binary]
python-dotenv
email-validator
bleach
httpx
feedparser
beautifulsoup4
Pillow
python-slugify
```

Development/quality:

```text
pytest
pytest-flask
pytest-cov
factory-boy
ruff
mypy
pre-commit
```

اختيارية لاحقًا حسب القياس: `redis` للكاش/limiting المشترك، و`APScheduler` أو worker queue للجدولة. لا تُضاف قبل الحاجة، ولا تمنح صلاحية نشر.

## 13. حدود PHASE 1 المقترحة عند الموافقة

- scaffold للتطبيق والإعدادات والإضافات.
- migrations ونماذج User/Category/Theme/SiteSettings الأساسية.
- Login وصلاحيات أولية وBasic Admin.
- Theme editing آمن وحقن CSS variables.
- seed تطوير منفصل واختبارات authentication/models/theme/category.

لا تشمل PHASE 1: الصفحة الرئيسية الديناميكية الكاملة، البحث، fetchers، AI، مكتبة الفيديو، deployment، أو الاتصال بـ`iraqikids.com`.

## 14. ملاحظات قبل بدء التنفيذ

- يجب نسخ المرجع البصري إلى مجلد `docs/reference/` عند إنشاء المشروع مع توثيق أنه مرجع لا template تشغيل.
- يلزم تثبيت قرار تخزين الصور Production لاحقًا (local persistent volume أو object storage)، لكن الواجهة يجب أن تعتمد abstraction منذ البداية.
- يجب اعتماد سياسة تحرير وحقوق مصادر قبل تفعيل fetchers الفعلية.
- لا انتقال إلى PHASE 1 إلا بطلب صريح.
