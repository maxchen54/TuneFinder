import json
import requests
import time
import base64
import os
import hashlib
import datatier
import boto3
import uuid

from configparser import ConfigParser
from os.path import exists

s3 = boto3.client("s3")
BUCKET_NAME = "photoapp-max-nu-cs310"

def lambda_handler(event, context):
    try:
        config_file = 'tunefinder-config.ini'
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
        
        configur = ConfigParser()
        configur.read(config_file)

        rds_endpoint = configur.get('rds', 'endpoint')
        rds_portnum = int(configur.get('rds', 'port_number'))
        rds_username = configur.get('rds', 'user_name')
        rds_pwd = configur.get('rds', 'user_pwd')
        rds_dbname = configur.get('rds', 'db_name')

        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        if "body" not in event or not event["body"]:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing 'body' in request!"})}

        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError as e:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON format!"})}

        audio_base64 = body.get("audio", "")

        if not audio_base64:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing 'audio' in request!"})}

        try:
            audio_binary = base64.b64decode(audio_base64)
        except Exception as e:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid Base64 encoding!"})}

        key = str(uuid.uuid4().hex)
        file_name = f"uploads/audio_{key}.mp3"

        sql = "INSERT INTO jobs(bucketkey) VALUES(%s)"
        datatier.perform_action(dbConn, sql, [file_name])
        
        try:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=file_name,
                Body=audio_binary,
                ContentType="audio/mpeg"
            )
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"
        except Exception as e:
            return {"statusCode": 500, "body": json.dumps({"error": "S3 upload failed!"})}

        sql = "SELECT LAST_INSERT_ID();"
    
        row = datatier.retrieve_one_row(dbConn, sql)
    
        jobid = row[0]

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Upload successful", "jobid": jobid})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
