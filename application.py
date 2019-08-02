from flask import Flask, render_template, flash, request, url_for, redirect
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
from forms import *
import os
import boto3
import json
import transcribe



# App config.
DEBUG = True
app = Flask(__name__, static_url_path='/templates')
app.config.from_object(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


s3 = boto3.resource('s3')
client = boto3.client('dynamodb')
bucket = s3.Bucket('crmcustomeraudio')


@app.route('/giveDates', methods=['GET'])
def giveDates():
    return render_template("transcription.html")

@app.route('/', methods=['GET', 'POST',  'PUT'])
def getNumber():
    formNum = GetNumForm()
    formName = getName()
    if (formNum.is_submitted() and formNum.phoneNum.data):
        result = request.form
        phoneNumber = result['phoneNum']
        if phoneNumber[0] == "+":
            phoneNumber = phoneNumber[1:]
        if phoneNumber[0] != "1":
            phoneNumber = "1" + phoneNumber
        call = "/selectCall/" + phoneNumber
        return redirect(call)
    if (formName.is_submitted() and formName.name.data):
        result = request.form
        name = result['name']
        if name[0].islower():
            name.split(" ")
            first = name[0][0].upper() + name[0][1:]
            last = name[1][0].upper() + name[0][1:]
            name = first + last
        # Look up the persons name in to find their phone number and submit the form that way
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('nametophonepoc')
        try:
            name = table.get_item(Key={'name': name})
            phoneNumber = name['Item']['phoneNum']
            call = "/selectCall/" + phoneNumber[1:]
            return redirect(call)
        except:
            message = "Could not find this person in the database"
            return render_template("getNum.html", form=formNum, form2=formName, message=message)
    message = " "
    return render_template("getNum.html", form=formNum, form2=formName, message=message)


@app.route('/selectCall/<phoneNum>', methods=['GET', 'POST'])
def selectCall(phoneNum):
    listofbuckets = []
    masterInfoList = []
    for obj in bucket.objects.all():
        call = obj.key.split("/")
        if (call[0] == phoneNum):
            listofbuckets.append((obj.key, call[1]))
    formDate = getDateForm()
    formDate.dateGiven.choices = listofbuckets
    if formDate.is_submitted():
        result = request.form
        filename = result["dateGiven"]
        fileNum = str(filename.split("/")[0])
        fileDate = str(filename.split("/")[1])
        fileWAV = str(filename.split("/")[-1])
        transcript = transcribe.main(fileNum, fileDate, fileWAV )
        return render_template("transcription.html", transcript=transcript)
    return render_template('giveDates.html', phoneNum=phoneNum,form=formDate, listofbuckets=listofbuckets)

if __name__ == "__main__":
    app.run()
