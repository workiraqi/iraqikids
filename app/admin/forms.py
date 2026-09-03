from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


HEX_VALIDATOR = Regexp(r"^#[0-9a-fA-F]{6}$", message="أدخل لونًا بصيغة #RRGGBB.")
SLUG_VALIDATOR = Regexp(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", message="استخدم أحرفًا إنجليزية صغيرة وأرقامًا وشرطات.")


class CategoryForm(FlaskForm):
    title = StringField("العنوان", validators=[DataRequired(), Length(max=160)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=160), SLUG_VALIDATOR])
    description = TextAreaField("الوصف", validators=[Optional(), Length(max=2000)])
    icon = StringField("الأيقونة", validators=[Optional(), Length(max=80)])
    accent_color = StringField("لون التمييز", validators=[Optional(), HEX_VALIDATOR])
    visible = BooleanField("ظاهر")
    sort_order = IntegerField("الترتيب", validators=[DataRequired(), NumberRange(min=0, max=9999)])
    parent_id = SelectField("التصنيف الأب", coerce=int, choices=[])
    submit = SubmitField("حفظ")


class ThemeForm(FlaskForm):
    bg = StringField("الخلفية الرئيسية", validators=[DataRequired(), HEX_VALIDATOR])
    bg_secondary = StringField("الخلفية الثانوية", validators=[DataRequired(), HEX_VALIDATOR])
    panel = StringField("Panels", validators=[DataRequired(), HEX_VALIDATOR])
    text = StringField("النص الرئيسي", validators=[DataRequired(), HEX_VALIDATOR])
    text_muted = StringField("النص الثانوي", validators=[DataRequired(), HEX_VALIDATOR])
    primary = StringField("Primary Accent", validators=[DataRequired(), HEX_VALIDATOR])
    secondary = StringField("Secondary Accent", validators=[DataRequired(), HEX_VALIDATOR])
    lime = StringField("Lime", validators=[DataRequired(), HEX_VALIDATOR])
    cyan = StringField("Cyan", validators=[DataRequired(), HEX_VALIDATOR])
    pink = StringField("Pink", validators=[DataRequired(), HEX_VALIDATOR])
    border = StringField("Borders", validators=[DataRequired(), HEX_VALIDATOR])
    button = StringField("الأزرار", validators=[DataRequired(), HEX_VALIDATOR])
    hover = StringField("Hover", validators=[DataRequired(), HEX_VALIDATOR])
    submit = SubmitField("حفظ")


class BrandingForm(FlaskForm):
    site_name = StringField("اسم الموقع", validators=[DataRequired(), Length(max=160)])
    arabic_site_name = StringField("اسم الموقع بالعربية", validators=[DataRequired(), Length(max=160)])
    short_description = TextAreaField("الوصف المختصر", validators=[DataRequired(), Length(max=1000)])
    hero_title = StringField("عنوان Hero", validators=[DataRequired(), Length(max=300)])
    hero_subtitle = TextAreaField("وصف Hero", validators=[DataRequired(), Length(max=1500)])
    footer_text = StringField("نص Footer", validators=[DataRequired(), Length(max=300)])
    submit = SubmitField("حفظ")

