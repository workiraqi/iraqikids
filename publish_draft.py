from datetime import datetime
import os
import subprocess

DRAFT_FILE = "draft.txt"
POSTS_DIR = "posts"
INDEX_FILE = "index.html"

with open(DRAFT_FILE, "r", encoding="utf-8") as f:
    text = f.read()

lines = text.splitlines()

title = ""
category = ""
content = []
mode = None

for line in lines:
    if line.startswith("العنوان:"):
        title = line.replace("العنوان:", "").strip()
    elif line.startswith("التصنيف:"):
        category = line.replace("التصنيف:", "").strip()
    elif line.startswith("المحتوى:"):
        mode = "content"
    elif mode == "content":
        content.append(line)

if not title:
    raise ValueError("لم يتم العثور على العنوان في draft.txt")

today = datetime.now().strftime("%Y-%m-%d")
filename = f"post_{today}.html"
post_path = os.path.join(POSTS_DIR, filename)

paragraphs = ""
for p in content:
    if p.strip():
        paragraphs += f"<p>{p.strip()}</p>\n"

html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{title}</title>
</head>
<body>

<h1>{title}</h1>
<p><strong>التصنيف:</strong> {category}</p>

{paragraphs}

<p><a href="../index.html">العودة إلى الصفحة الرئيسية</a></p>

</body>
</html>
"""

os.makedirs(POSTS_DIR, exist_ok=True)

with open(post_path, "w", encoding="utf-8") as f:
    f.write(html)

# تحديث index.html
link_line = f'<li><a href="posts/{filename}">{title}</a> - {today}</li>'

with open(INDEX_FILE, "r", encoding="utf-8") as f:
    index_html = f.read()

if link_line not in index_html:
    index_html = index_html.replace(
        "<ul>",
        "<ul>\n  " + link_line,
        1
    )

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write(index_html)

print("تم إنشاء المقال وتحديث الصفحة الرئيسية:")
print(filename)

# أوامر Git للنشر
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", f"Publish {title}"], check=True)
subprocess.run(["git", "push"], check=True)

print("تم النشر على GitHub Pages بنجاح.")