from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL


class SourceForm(FlaskForm):
    name = StringField(
        "اسم المصدر",
        validators=[DataRequired(), Length(max=240)],
    )

    url = StringField(
        "رابط المصدر",
        validators=[DataRequired(), URL(), Length(max=1000)],
    )

    source_type = SelectField(
        "نوع المصدر",
        choices=[
            ("rss", "RSS"),
            ("web", "موقع ويب"),
        ],
        validators=[DataRequired()],
    )

    language = StringField(
        "اللغة",
        validators=[Optional(), Length(max=80)],
    )

    quality_score = IntegerField(
        "جودة المصدر",
        default=5,
        validators=[DataRequired(), NumberRange(min=0, max=10)],
    )

    notes = TextAreaField(
        "ملاحظات",
        validators=[Optional(), Length(max=5000)],
    )

    is_active = BooleanField(
        "المصدر مفعّل",
        default=True,
    )

    submit = SubmitField("حفظ المصدر")