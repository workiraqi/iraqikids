from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = EmailField("البريد الإلكتروني", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(max=256)])
    submit = SubmitField("تسجيل الدخول")

