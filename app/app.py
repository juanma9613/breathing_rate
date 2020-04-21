import os
import sys

sys.path.append('.')

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
    body = request.json
    audio_path = body.get("audio_path")
    breathing_rate = Breathing_rate(audio_path)
    breathing_frequency = breathing_rate.get_breathing_rate()

    response = {
        "audio_path": audio_path,
        "breathing_frequency": breathing_frequency.rate
    }
    return jsonify(response), 200


@app.route("/health_check", methods=["GET"])
def get():
    return "OK"


if __name__ == "__main__":
    app.run()
