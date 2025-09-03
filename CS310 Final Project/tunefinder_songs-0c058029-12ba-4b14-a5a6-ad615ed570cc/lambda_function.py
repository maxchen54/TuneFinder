import json
import requests
import time
import base64
import os
import hashlib
import datatier

from configparser import ConfigParser

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

        sql = "SELECT * FROM songs"
        songs = datatier.retrieve_all_rows(dbConn, sql)
        print(songs)

        return {"statusCode": 200, "body": json.dumps(songs)}

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
