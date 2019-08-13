from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField

class GetNumForm(FlaskForm):
    phoneNum = StringField('Please enter in the phone number: ')
    submit = SubmitField('Find')

class getDateForm(FlaskForm):
    dateGiven = RadioField('Select conversation', choices=[('value','description')])
    submit = SubmitField('Get Transcription')


class getName(FlaskForm):
    name = StringField('Please enter in the customers first and last name:  ')
    submit = SubmitField('Find')

class playaudio(FlaskForm):
    submit = SubmitField('Listen to Call')
