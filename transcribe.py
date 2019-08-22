import boto3
import json
import time
import re

def main(number, date, fileWAV):
#"18609704538"
#"2019-7-22"
    input_json = {
      "number": str(number),
      "date": str(date),
      "contactId": str(fileWAV).replace(".WAV", "")
    }

    job_name = number+date+fileWAV
    # get all the items in crmcustomeraudio with correct phone number and date, pick the first
    lm = boto3.client('lambda')
    s3 = boto3.client('s3')
    transcribe = boto3.client('transcribe')

    # run start transcription lambda
    try:
        response = lm.invoke(
        FunctionName='CRMstarttranscriptionjob',
        Payload=json.dumps(input_json)
        )
    except:
        pass

    def get_transcript(job_name,key,date):
        from boto3.dynamodb.conditions import Key, Attr
        s3client = boto3.client('s3')
        timeout = time.time() + 60 * 8  # 5 minutes from now
        #print(job_name)
        #print(s3client.list_objects(Bucket='transcriptedfilescgurry')['Contents'])
        while True:
            s3_list = [key['Key'] for key in s3client.list_objects(Bucket='transcriptedfilescgurry')['Contents']]
            if key in s3_list or time.time() > timeout:
                try:
                    s3 = boto3.resource('s3')
                    object = s3.Object('transcriptedfilescgurry', key)
                    file_content = object.get()['Body'].read().decode('utf-8')
                    json_content = json.loads(file_content)
                    break
                except:
                    print("timeout")
                    break
        #print(json_content)
        word_items = json_content['results']['items']
        speakers = json_content['results']['speaker_labels']['segments']
        speaker_segments = []
        tran_dict = []
        for i in speakers:
            if len(i['items']) > 0:
                [speaker_segments.append(x) for x in i['items']]
            elif len(i['items']) == 0:
                speaker_segments.append(i)
        for i in speaker_segments:
            tran_dict.append([i['start_time'], i['speaker_label']])

        utter = [[i['alternatives'][0]['content'], i['type'], i['start_time'] if 'start_time' in i else '', i['alternatives'][0]['confidence']] for i in word_items]

        for lst in utter:
            for x in tran_dict:
                if x[0] == lst[2]:
                    lst.append(x[1])
                else:
                    pass

        for i, lst in enumerate(utter):
            if lst[2] == '':
                lst.append(utter[i - 1][3])

        txt_file = ''
        print(utter)
        line = (utter[0][-1] + ':').upper()
        for i, row in enumerate(utter):
            # add coloring for confidence levels < .85:
            if row[1] == 'pronunciation' and float(row[3]) <= .85:
                row[0] = '('+row[2]+') '+"\033[43m" + row[0] + "\033[m"

            if row[-1].upper() == line[:5]:
                if row[1] == 'pronunciation':
                    line += ' ' + row[0]
                else:
                    line += row[0]
            elif row[1] == 'punctuation':
                line += row[0]
            else:
                line += '\n'
                txt_file += line
                line = (utter[i][-1] + ':').upper()
                if row[1] == 'pronunciation':
                    line += ' ' + row[0]
                else:
                    line += row[0]
                # line = (utter[i][3] + ':').upper()
            if i == len(utter) - 1:
                txt_file += line

        # update txt_file with person's name from dynamo contactDetails
        phone_num = '+' + key[:11]
        #print(phone_num)
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('voyacenterdatapoc')
        try:
            response = table.query(
                KeyConditionExpression=Key('phoneNum').eq(phone_num)
            )
            name = response['Items'][0]['firstName']
            #print(name)
            txt_file = txt_file.replace('SPK_1', name)
        except:
            pass

        txt_file = txt_file.replace('SPK_0', 'Agent')
        ## for cleaning up presentation:
        txt_file = txt_file.replace('phone bill', 'bill')
        txt_file = txt_file.replace('career', 'delivery')

        file_name = job_name + '.txt'
        s3_path = 'transcripts/' + phone_num + '/' + file_name
        txt_file_simple = txt_file.replace("\033[43m",'')
        txt_file_simple = txt_file_simple.replace('\033[m','')
        txt_file_simple = re.sub(r'\((\d+\.\d+)\)','',txt_file_simple)
        txt_file_simple = txt_file_simple.replace('\n','\n\n')
        file1 = open('static/my_file.txt','w')
        file1.write('Customer transcription for '+name+' on '+date+':\n\n')
        file1.write(txt_file_simple)
        file1.close()
        s3 = boto3.client('s3')
        s3.upload_file('static/my_file.txt','crmaudiobucket1',s3_path)


        #build the results.html file that prints low confidence words in red
        html_text = '''{% extends "base.html" %}
        {% block content %}
        <h3>
        <font color="red">Red Indicates Confidence Below 85%</font>
        </h3>
        <body>
        <p>
        <font color="black">
        ''' + txt_file + '''
        <a href="/" class="btn btn-primary active" role="button" aria-pressed="true">Home</a>
        </font></body>{% endblock %}'''
        html_text = html_text.replace('\n','</p><p>')
        html_text = html_text.replace('\033[43m','<font color="red">')
        html_text = html_text.replace('\033[m','</font>')
        Html_file= open("templates/results.html","w")
        Html_file.write(html_text)
        Html_file.close()

        return {
            'status code': 200,
            'body': s3_path,
            'txt': txt_file_simple
            }
    output = get_transcript(job_name[:-4],job_name[:-4]+'.json',str(date))['txt']
    return output
