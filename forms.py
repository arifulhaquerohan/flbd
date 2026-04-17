from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Optional, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    contact = StringField('Contact Info') # Catch-all sometimes used
    interest = StringField('Interest', validators=[Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired()])
    budget = StringField('Budget', validators=[Optional(), Length(max=50)])
    service_type = StringField('Service Type', validators=[Optional(), Length(max=100)])
    timeline = StringField('Timeline', validators=[Optional(), Length(max=50)])

    # Flatland allows submitting even if interest doesn't exist, so Optional for those.
