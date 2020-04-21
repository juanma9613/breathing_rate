import os
import sys

sys.path.append('../')

import boto3
import traceback
from botocore.config import Config

from flask import Flask, request, jsonify

from Breathing_rate import Breathing_rate
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

config_dict = {"connect_timeout": 60000000, "read_timeout": 6000000}
config = Config(**config_dict)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    config=config
)


@app.route("/calculate_bf", methods=["POST"])
def calculate_bf():
    try:
        if request.is_json:
            try:
                is_body_well_formed = True
                body = request.json
                audio_path = body["audio_path"]
            except:
                is_body_well_formed = False
                response = {
                    "message": "Specify a well-formed body."
                }
                status_code = 400
            if is_body_well_formed:
                breathing_rate = Breathing_rate(audio_path)
                breathing_frequency = breathing_rate.get_breathing_rate()
                response = {
                    "audio_path": audio_path,
                    "breathing_frequency": breathing_frequency["rate"]
                }
                status_code = 200
        else:
            response = {
                "message": "Send a JSON request."
            }
            status_code = 400
    except Exception as e:
        response = {
            "message": "Internal Server Error."
        }
        status_code = 500
        print("****** Error processing audio file ******")
        print(traceback.format_exc())
        print("****** Error ******")
        print(e)

    return jsonify(response), status_code


@app.route("/health_check", methods=["GET"])
def get():
    return "OK"


if __name__ == "__main__":
    app.run()
