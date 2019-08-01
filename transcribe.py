import boto3
import json
import time

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

    def get_transcript(job_name,key):
        from boto3.dynamodb.conditions import Key, Attr
        s3client = boto3.client('s3')
        timeout = time.time() + 60 * 3  # 3 minutes from now
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
                    break

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

        utter = [[i['alternatives'][0]['content'], i['type'], i['start_time'] if 'start_time' in i else ''] for i in
                 word_items]

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

        line = (utter[0][3] + ':').upper()
        for i, row in enumerate(utter):
            if row[3].upper() == line[:5]:
                if row[1] == 'pronunciation':
                    line += ' ' + row[0]
                else:
                    line += row[0]
            else:
                line += '\n'
                txt_file += line
                line = (utter[i][3] + ':').upper()
                if row[1] == 'pronunciation':
                    line += ' ' + row[0]
                else:
                    line += row[0]
            if i == len(utter) - 1:
                txt_file += line

        # update txt_file with person's name from dynamo contactDetails
        phone_num = '+' + key[:11]
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('voyacenterdatapoc')
        try:
            response = table.query(
                KeyConditionExpression=Key('phoneNum').eq(phone_num)
            )
            name = response['Items'][0]['firstName']
            txt_file = txt_file.replace('SPK_1', name)
        except:
            pass

        txt_file = txt_file.replace('SPK_0', 'Agent')
        file_name = job_name + '.txt'
        s3_path = 'transcripts/' + file_name

        return {
            'status code': 200,
            'body': s3_path,
            'txt': txt_file
            }
    output = get_transcript(job_name[:-4],job_name[:-4]+'.json')['txt']
    return output
