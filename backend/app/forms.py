from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    name = StringField("Tên hiển thị", validators=[DataRequired(), Length(max=80)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=12, max=128)])
    confirm = PasswordField("Nhập lại mật khẩu", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Tạo tài khoản")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Đăng nhập")
