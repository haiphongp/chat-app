from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError
from passlib.hash import pbkdf2_sha256
from models import UserGlobal


def hashpassword(password):
    hash = 0
    if (len(password) == 0): 
        return hash
    for i in range(len(password)):
        chr   = ord(password[i])
        hash  = ((hash << 5) - hash) + chr
        hash |= 0; # Convert to 32bit integer
    return str(hash)


def validate_profile(form, field):
    password = field.data
    username = form.username.data

    user_data = UserGlobal.query.filter_by(name=username).first()
    if user_data is None:
        raise ValidationError("Name or password is incorrect!")
    elif hashpassword(password) != str(user_data.hashpass):
        raise ValidationError("Name or password is incorrect!")


class RegistrationForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(message="user Name Required"),
                                                         Length(min=1, max=45,
                                                                message="The length must be between 5 and 45 characters")])

    password = PasswordField('password', validators=[InputRequired(message="Password Required"),
                                                     Length(min=1, max=45,
                                                            message="The length must be between 5 and 45 characters")])

    confirm_password = PasswordField('confirm_password', validators=[InputRequired(message="Password Required"),
                                                                     EqualTo('password', message="Password did not match!")])

    def validate_username(self, username):
        user = UserGlobal.query.filter_by(name=username.data).first()
        if user:
            raise ValidationError("user name already exist!")


class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(message="user Name Required!")])
    password = PasswordField('password', validators=[InputRequired(message="Password Required!"), validate_profile])

class SearchForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(message="user Name Required!")])
    