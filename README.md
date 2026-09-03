# Iraqi Kids

Local Flask foundation for an Arabic creativity platform for children. PHASE 2 adds the immersive dynamic homepage, articles, editorial publishing controls, safe local images, category pages, search, and baseline SEO.

## Requirements

- Python 3.11+
- Windows PowerShell or Command Prompt

## PowerShell setup

```powershell
cd "$env:USERPROFILE\Desktop\iraqikids"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Set a long random `SECRET_KEY` in `.env`. Leave `DATABASE_URL` empty for local SQLite. `SITE_BASE_URL` is optional locally and can remain empty.

```powershell
flask --app wsgi.py db upgrade
flask --app wsgi.py seed-dev
$env:ADMIN_EMAIL = "admin@example.com"
$env:ADMIN_PASSWORD = "use-a-long-local-password"
flask --app wsgi.py create-admin
flask --app wsgi.py run
```

## Command Prompt setup

```bat
cd %USERPROFILE%\Desktop\iraqikids
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
copy .env.example .env
flask --app wsgi.py db upgrade
flask --app wsgi.py seed-dev
set ADMIN_EMAIL=admin@example.com
set ADMIN_PASSWORD=use-a-long-local-password
flask --app wsgi.py create-admin
flask --app wsgi.py run
```

Open `http://127.0.0.1:5000/` and use `http://127.0.0.1:5000/admin/login` for administration.

## PHASE 2 routes

Public:

- `/`
- `/articles`
- `/articles/<slug>`
- `/category/<slug>`
- `/search?q=`
- `/sitemap.xml`
- `/robots.txt`

Admin:

- `/admin/articles`
- `/admin/articles/new`
- `/admin/articles/<id>/edit`
- `/admin/articles/<id>/preview`
- publish, hide, restore, and delete POST actions

## Editorial workflow

New articles are always drafts. Publishing, hiding, and restoring pass through `PublishingService`; public queries return only `status == published`. Article body HTML is cleaned with a small Bleach allowlist: paragraphs, level-two and level-three headings, emphasis, lists, blockquotes, and HTTP/HTTPS links. Scripts, iframes, embedded objects, styles, and unsafe URL schemes are removed.

## Article images

Development images are stored under `app/static/uploads/articles/` using random filenames. JPG, PNG, and WebP are accepted. The service checks extension, MIME type, and decoded image format with Pillow. The application request limit is 4 MB. Uploaded files are ignored by Git except for the directory placeholder.

## Seed

`flask --app wsgi.py seed-dev` is idempotent and creates:

- one SiteSettings record;
- the default immersive dark Theme;
- eight database-backed categories;
- ten short original Arabic development articles, four featured.

It does not create an admin automatically.

## Tests and migrations

```powershell
pytest
flask --app wsgi.py db check
```

Development uses `instance/iraqikids.db`. Production only reads `DATABASE_URL`; this project does not contact a production database.

## Scope boundary

Sources, RSS, scraping, fetchers, candidates, AI, translation, videos, activities, challenge and book models, scheduling, deployment, and domain configuration remain outside PHASE 2.
