#
# Client-side python app for benford app, which is calling
# a set of lambda functions in AWS through API Gateway.
# The overall purpose of the app is to process a PDF and
# see if the numeric values in the PDF adhere to Benford's
# law. This version adds authentication with user names, 
# passwords, and login tokens.
#
# Authors:
#   max chen
#
#   Prof. Joe Hummel (initial template)
#   Northwestern University
#   CS 310
#

import hashlib
import hmac
import json
import requests
import jsons

import uuid
import pathlib
import logging
import sys
import os
import base64
import time

from configparser import ConfigParser
from getpass import getpass


############################################################
#
# classes

class Song:

  def __init__(self, row):
    self.title = row[0]
    self.score = row[1]
    self.artist = row[2]
    self.album = row[3]
    self.release_date = row[4]


###################################################################
#
# web_service_get
#
# When calling servers on a network, calls can randomly fail. 
# The better approach is to repeat at least N times (typically 
# N=3), and then give up after N tries.
#
def web_service_get(url):
  """
  Submits a GET request to a web service at most 3 times, since 
  web services can fail to respond e.g. to heavy user or internet 
  traffic. If the web service responds with status code 200, 400 
  or 500, we consider this a valid response and return the response.
  Otherwise we try again, at most 3 times. After 3 attempts the 
  function returns with the last response.
  
  Parameters
  ----------
  url: url for calling the web service
  
  Returns
  -------
  response received from web service
  """

  try:
    retries = 0
    
    while True:
      response = requests.get(url)
        
      if response.status_code in [200, 400, 480, 481, 482, 500]:
        #
        # we consider this a successful call and response
        #
        break;

      #
      # failed, try again?
      #
      retries = retries + 1
      if retries < 3:
        # try at most 3 times
        time.sleep(retries)
        continue
          
      #
      # if get here, we tried 3 times, we give up:
      #
      break

    return response

  except Exception as e:
    print("**ERROR**")
    logging.error("web_service_get() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return None
  

def web_service_post(url, data, headers=None):
  """
  Submits a GET request to a web service at most 3 times, since 
  web services can fail to respond e.g. to heavy user or internet 
  traffic. If the web service responds with status code 200, 400 
  or 500, we consider this a valid response and return the response.
  Otherwise we try again, at most 3 times. After 3 attempts the 
  function returns with the last response.
  
  Parameters
  ----------
  url: url for calling the web service
  
  Returns
  -------
  response received from web service
  """

  try:
    retries = 0
    
    while True:
      response = requests.post(url, json=data, headers=headers)
        
      if response.status_code in [200, 400, 480, 481, 482, 500]:
        #
        # we consider this a successful call and response
        #
        break;

      #
      # failed, try again?
      #
      retries = retries + 1
      if retries < 3:
        # try at most 3 times
        time.sleep(retries)
        continue
          
      #
      # if get here, we tried 3 times, we give up:
      #
      break

    return response

  except Exception as e:
    print("**ERROR**")
    logging.error("web_service_get() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return None
    

############################################################
#
# prompt
#
def prompt():
  """
  Prompts the user and returns the command number

  Parameters
  ----------
  None

  Returns
  -------
  Command number entered by user (0, 1, 2, ...)
  """
  try:
      print()
      print(">> Enter a command:")
      print("   0 => end")
      print("   1 => upload")
      print("   2 => identify song")
      print("   3 => check previously analyzed songs")

      cmd = input()

      if cmd == "":
        cmd = -1
      elif not cmd.isnumeric():
        cmd = -1
      else:
        cmd = int(cmd)

      return cmd

  except Exception as e:
      print("**ERROR")
      print("**ERROR: invalid input")
      print("**ERROR")
      return -1

def upload():
  url = "https://t0xahidjwe.execute-api.us-east-2.amazonaws.com/prod/upload"
  print("Enter file name for upload>")
  filename = str(input()).strip()

  try:
    with open(filename, "rb") as f:
      audio_base64 = base64.b64encode(f.read()).decode("utf-8")
  except FileNotFoundError:
    print("ERROR: File does not exist!")
    return

  data = {"audio": audio_base64}
  headers = {"Content-Type": "application/json",
             "Content-Length": str(len(audio_base64))}

  response = requests.post(url, json=data, headers=headers)

  if response.status_code == 200:
    print(f"Uploaded successfully!")
    jobid = response.json().get('jobid')
    print("Job ID (use to refer to the file):", jobid)
  else:
    print(f"Upload Failed: {response.text}") 

def songs():
  try:
    api = "https://t0xahidjwe.execute-api.us-east-2.amazonaws.com/prod/songs"

    res = web_service_get(api)
    if res.status_code == 200: #success
      body = res.json()
      songs = []
      for row in body:
        song = Song(row)
        songs.append(song)
      for song in songs:
        print(song.title)
        print(" ", song.score)
        print(" ", song.artist)
        print(" ", song.album)
        print(" ", song.release_date)
    elif res.status_code == 500 or res.status_code == 400:
      # we'll have an error message
      body = res.json()
      print("**ERROR:", body)
      return
    else:
      print("**ERROR:", res.status_code)
    #
    return
  
  except Exception as e:
    logging.error("**ERROR: songs() failed:")
    logging.error("url: " + api)
    logging.error(e)
    return
    
def identify():
    url = "https://t0xahidjwe.execute-api.us-east-2.amazonaws.com/prod/identify"

    print("Enter the job ID to analyze>")
    jobid = str(input()).strip()

    print("Enter the trim length for your file, or ENTER for default (10 seconds)>")
    trim_length = str(input()).strip()

    if trim_length == "":
      trim_length = 10
    elif int(trim_length) < 5:
      print("Too short of a length! Automatically trimming to shortest length, 5 seconds.")
      trim_length = 5

    data = {
      "jobid": jobid,
      "trim_length": trim_length
    }

    headers = {"Content-Type": "application/json"}

    response = web_service_post(url, data=data, headers=headers)

    response_json = response.json()

    if response.status_code == 200:
      print("Identified Song:", response_json)
      if float(response_json.get('score')) < 0.85:
        print("**NOTE: The confidence level for this prediction is low, try again with a longer trim length or clearer file!")
    else:
      print(f"Error {response.status_code}: {response_json}")

############################################################
# main
#
try:
  sys.tracebacklimit = 0

  tunefinder_config = 'tunefinder_config.ini'
  if not pathlib.Path(tunefinder_config).is_file():
    print("**ERROR: tunefinder config file '", tunefinder_config, "' does not exist, exiting")
    sys.exit(0)

  #
  # does config file exist?
  #
  if not pathlib.Path(tunefinder_config).is_file():
    print("**ERROR: authsvc config file '", tunefinder_config, "' does not exist, exiting")
    sys.exit(0)

  #
  # main processing loop:
  #
  cmd = prompt()

  while cmd != 0:
    #
    if cmd == 1:
      upload()
    elif cmd == 2:
      identify()
    elif cmd == 3:
      songs()
    else:
      print("** Unknown command, try again...")
    #
    cmd = prompt()

  #
  # done
  #
  print()
  print('** done **')
  sys.exit(0)

except Exception as e:
  logging.error("**ERROR: main() failed:")
  logging.error(e)
  sys.exit(0)
