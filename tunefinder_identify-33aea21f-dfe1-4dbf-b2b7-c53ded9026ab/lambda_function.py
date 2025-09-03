#
# Song identification function
#

import json
import requests
import time
import base64
import os
import hmac
import hashlib
import boto3
import subprocess
import datatier
import decimal

from configparser import ConfigParser

s3 = boto3.client("s3")

API_HOST = os.getenv('API_HOST')
API_ACCESS_KEY = os.getenv('API_ACCESS_KEY')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

def identify_song(audio_binary):
    api_url = f"https://{API_HOST}/v1/identify"

    if len(audio_binary) < 1000:  # Less than 1KB
        print(" ERROR: Audio file too small!")
        return {"error": "Audio file is too short or corrupted"}

    timestamp = str(int(time.time()))
    string_to_sign = f"POST\n/v1/identify\n{API_ACCESS_KEY}\naudio\n1\n{timestamp}"
    signature = base64.b64encode(
        hmac.new(
            API_SECRET_KEY.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha1
        ).digest()
    ).decode('utf-8')

    audio_file = {'sample': ('audio.mp3', audio_binary, 'audio/mpeg')}
    data = {
        'access_key': API_ACCESS_KEY,
        'sample_bytes': len(audio_binary),
        'timestamp': timestamp,
        'signature': signature,
        'data_type': 'audio',
        'signature_version': 1
    }

    response = requests.post(api_url, files=audio_file, data=data)
    response_text = response.content.decode("utf-8", errors="replace")
    response_json = json.loads(response_text)

    return response_json

def lambda_handler(event, context):
    try:
        config_file = 'tunefinder-config.ini'
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
        
        configur = ConfigParser()
        configur.read(config_file)
        
        s3_profile = 's3readwrite'
        boto3.setup_default_session(profile_name=s3_profile)
        
        bucketname = configur.get('s3', 'bucket_name')

        rds_endpoint = configur.get('rds', 'endpoint')
        rds_portnum = int(configur.get('rds', 'port_number'))
        rds_username = configur.get('rds', 'user_name')
        rds_pwd = configur.get('rds', 'user_pwd')
        rds_dbname = configur.get('rds', 'db_name')

        dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

        body = json.loads(event.get("body", "{}"))
        print(body)
        
        jobid = body.get("jobid", "")
        trim_length = body.get("trim_length", "10")  # Default 10 sec

        if not jobid:
            print("ERROR: Missing 'jobid' in request!")
            return {"statusCode": 400, "body": json.dumps({"error": "Missing Job ID!"})}

        sql = "SELECT * FROM jobs WHERE jobid = %s"
        row = datatier.retrieve_one_row(dbConn, sql, [jobid])
        if not row:
            print(f"ERROR: Job ID '{jobid}' not found!")
            return {"statusCode": 400, "body": json.dumps({"error": "Job ID not found!"})}

        file_name = row[1].split("/")[-1]
        local_path = f"/tmp/{file_name}"
        trimmed_path = f"/tmp/trimmed_{file_name}"

        # Download file from S3
        try:
            s3_object = s3.get_object(Bucket=bucketname, Key=f"uploads/{file_name}")
            audio_binary = s3_object["Body"].read()
            print(f"S3 Downloaded File Size (Memory): {len(audio_binary)} bytes")
        except Exception as e:
            print(f"ERROR: Failed to download file from S3 - {str(e)}")
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to download file from S3"})}

        with open(local_path, "wb") as f:
            f.write(audio_binary)
        print(f"✅ File saved locally: {local_path}")

        try:
            ffmpeg_cmd = [
                "/opt/bin/ffmpeg", "-i", local_path,  # ✅ Input file
                "-t", str(trim_length),  # ✅ Trim duration
                "-b:a", "128k",  # ✅ Keep bitrate high for better quality
                "-y", trimmed_path  # ✅ Output file
            ]
            subprocess.run(ffmpeg_cmd, check=True)
        except subprocess.CalledProcessError as e:
            return {"statusCode": 500, "body": json.dumps({"error": "FFmpeg processing failed"})}

        with open(trimmed_path, "rb") as f:
            trimmed_audio_binary = f.read()

        response = identify_song(trimmed_audio_binary)

        sql = """INSERT INTO songs(title, score, artist, album, release_date)
                            VALUES(%s, %s, %s, %s, %s)"""

        if response.get('status', {}).get('msg') == 'Success':
            song_info = response.get("metadata", {}).get("humming", [{}])[0]
            song = song_info.get('title', "Unknown")
            artist = song_info.get('artists', [{}])[0].get('name', "Unknown Artist")
            release_date = song_info.get('release_date', "Unknown")
            album = song_info.get('album', {}).get('name', "Unknown Album")
            score = song_info.get('score', 0)
            datatier.perform_action(dbConn, sql, [song, score, artist, album, release_date])
            response_data = {
                'song': song_info.get('title', "Unknown"),
                'artist': song_info.get('artists', [{}])[0].get('name', "Unknown Artist"),
                'release_date': song_info.get('release_date', "Unknown"),
                'album': song_info.get('album', {}).get('name', "Unknown Album"),
                'score': song_info.get('score', 0)
            }
        else:
            response_data = {"error": "Song identification failed"}

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_data)
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}