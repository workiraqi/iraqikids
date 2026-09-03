from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")

html = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>خبر اليوم {today}</title>
</head>
<body>

<h1>خبر اليوم {today}</h1>

<p>
هذا مقال تجريبي تم إنشاؤه تلقائياً بواسطة بايثون.
</p>

</body>
</html>
"""

filename = f"post_{today}.html"

with open(filename, "w", encoding="utf-8") as file:
    file.write(html)

print("تم إنشاء:", filename)