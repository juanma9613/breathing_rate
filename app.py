import os

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
                try:
                    audio_path = download_audio_from_s3(audio_path=audio_path)
                except:
                    audio_path = None
                if audio_path:
                    breathing_rate = Breathing_rate(audio_path=audio_path)
                    breathing_frequency = breathing_rate.get_breathing_rate()
                    os.remove(audio_path)
                    response = {
                        "audio_path": audio_path,
                        "breathing_frequency": breathing_frequency["rate"]
                    }
                    status_code = 200
                else:
                    response = {
                        "message": "Specify a valid audio path."
                    }
                    status_code = 400
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


def download_audio_from_s3(audio_path):
    local_audio_files_dir = "audios"
    os.makedirs(local_audio_files_dir) if not os.path.exists(local_audio_files_dir) else None
    audio_path = audio_path.strip()
    audio_path = audio_path.replace("s3://", '')
    audio_path_split = audio_path.split('/')
    bucket_name = audio_path_split[0]
    key = '/'.join(audio_path_split[1:])
    audio_file_name = os.path.basename(key)
    local_audio_path = os.path.join(local_audio_files_dir, audio_file_name)
    try:
        s3_client.download_file(bucket_name, key, local_audio_path)
    except:
        audio_file_name = ''
    audio_path = local_audio_path if audio_file_name != '' else None
    return audio_path


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
