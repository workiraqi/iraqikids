from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp, URL


SLUG_VALIDATOR = Regexp(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message="استخدم أحرفًا إنجليزية صغيرة وأرقامًا وشرطات.",
)


class ArticleForm(FlaskForm):
    title = StringField("العنوان", validators=[DataRequired(), Length(max=240)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=240), SLUG_VALIDATOR])
    summary = TextAreaField("الملخص", validators=[DataRequired(), Length(max=2000)])
    body = TextAreaField("المحتوى", validators=[DataRequired(), Length(max=50000)])
    category_id = SelectField("التصنيف", coerce=int, validators=[DataRequired()], choices=[])
    author = StringField("الكاتب", validators=[Optional(), Length(max=180)])
    source_name = StringField("اسم المصدر", validators=[Optional(), Length(max=240)])
    source_url = StringField("رابط المصدر", validators=[Optional(), URL(), Length(max=1000)])
    source_language = StringField("لغة المصدر", validators=[Optional(), Length(max=80)])
    original_title = StringField("العنوان الأصلي", validators=[Optional(), Length(max=500)])
    image = FileField(
        "صورة المقال",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "صيغة الصورة غير مدعومة.")],
    )
    image_alt = StringField("النص البديل للصورة", validators=[Optional(), Length(max=300)])
    image_caption = StringField("وصف الصورة", validators=[Optional(), Length(max=500)])
    image_credit = StringField("حقوق الصورة", validators=[Optional(), Length(max=300)])
    remove_image = BooleanField("حذف الصورة الحالية")
    featured = BooleanField("مقال مميز")
    submit = SubmitField("حفظ المسودة")
