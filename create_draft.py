import os
from google import genai

SOURCE_FILE = "source.txt"
DRAFT_FILE = "draft.txt"

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError("لم يتم العثور على GEMINI_API_KEY في متغيرات النظام.")

client = genai.Client(api_key=api_key)

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    source_text = f.read().strip()

prompt = f"""
أنت محرر عربي لموقع أطفال تعليمي.

حوّل النص التالي إلى مسودة عربية مناسبة للأطفال.
الشروط:
- لا تنشر خبرًا مخيفًا أو صادمًا.
- اجعل اللغة سهلة وواضحة.
- اكتب عنوانًا مناسبًا.
- اختر تصنيفًا واحدًا فقط من: صحة، علوم، تعليم، فضاء، قصص، تقنية.
- اجعل النص من 3 إلى 5 فقرات قصيرة.
- لا تضف معلومات غير مؤكدة.
- أخرج النتيجة بهذا الشكل فقط:

العنوان: ...

التصنيف: ...

الصورة: handwash.jpg

المحتوى:
...

النص الأصلي:
{source_text}
"""

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=prompt
)

draft = response.text.strip()

with open(DRAFT_FILE, "w", encoding="utf-8") as f:
    f.write(draft)

print("تم إنشاء draft.txt بواسطة Gemini.")
print("افتح draft.txt وراجعه قبل النشر.")