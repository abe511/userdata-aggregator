from minio import Minio
from flask import Flask, request, redirect, render_template, jsonify
from processing import handle_event
from responses import handle_webhook, get_data
from utilities import is_bucket_empty, upload, calculate_mean_age

# DOCKER COMPOSE VERSION

SRC_DIR = "/src-data/"
DEST_DIR = "./processed_data/"
OUTPUT = "output.csv"
ENDPOINT = "minio:9000"

ACCESS_KEY = "admin"
SECRET_KEY = "password"
SRC_BUCKET = "datalake"
DEST_BUCKET = "processed-data"
TMP_DIR = "tmp/"
FIELDS = ["user_id", "first_name", "last_name", "birthts", "img_path"]



# HOST VERSION

# SRC_DIR = "../../02-src-data/"
# DEST_DIR = "processed_data/"
# OUTPUT = "output.csv"
# ENDPOINT = "127.0.0.1:9000"

# ACCESS_KEY = "admin"
# SECRET_KEY = "password"
# SRC_BUCKET = "datalake"
# DEST_BUCKET = "processed-data"
# TMP_DIR = "tmp/"
# FIELDS = ["user_id", "first_name", "last_name", "birthts", "img_path"]


*PATHS, = DEST_DIR, SRC_BUCKET, DEST_BUCKET, TMP_DIR


# initialize MinIO client
try:
    client = Minio(ENDPOINT, ACCESS_KEY, SECRET_KEY, secure=False)
except Exception as e:
    print("Unable to initialize the Minio client. Check endpoint and credentials")



app = Flask(__name__)


# index page with the query form
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data", methods=["GET", "POST"])
def data():
    """
    On GET request returns all or filtered records from DB in JSON format.
    On POST request triggers reprocessing of source bucket data.
    """
    if request.method == "GET":
        min_age = request.args.get("min_age", 1, type=int)
        max_age = request.args.get("max_age", 150, type=int)
        is_image_exists = request.args.get("is_image_exists", "off", type=str)
        if min_age <= 0 or max_age > 150 or min_age > max_age:
            return f"<p>Please provide valid input</p>"
        else:
            temp_db = get_data(client, DEST_BUCKET, TMP_DIR, OUTPUT, FIELDS, min_age, max_age, is_image_exists)
            return jsonify(temp_db)
    if request.method == "POST":
        handle_event(client=client, paths=PATHS, out_file=OUTPUT, fieldnames=FIELDS)
        return f"<p>Source data uploaded to the <strong>{SRC_BUCKET}</strong> bucket</p>"


@app.route("/stats")
def stats():
    """
    Returns the average age of users 
    """
    min_age = request.args.get("min_age", 1, type=int)
    max_age = request.args.get("max_age", 150, type=int)
    is_image_exists = request.args.get("is_image_exists", "off", type=str)

    if min_age <= 0 or max_age > 150 or min_age > max_age:
        return f"<p>Please provide valid input</p>"
    else:
        ages = get_data(client, DEST_BUCKET, TMP_DIR, OUTPUT, FIELDS, min_age, max_age, is_image_exists, stats=True)
        if ages:
            return f"<p>The average age of this group is <strong>{calculate_mean_age(ages)}</strong></p>"
        else:
            return "<p>No records found matching this criteria</p>"

@app.route("/webhook" ,methods=["GET", "POST"])
def webhook():
    """
    This endpoint is used by MinIO to notify about bucket events (get, put, delete)
    Parses the request JSON, extracts the event info.
    Logs the event to a file and runs the webhook handler.
    """
    if request.method == "HEAD":
        return app.make_response(("webhook status: STARTING", 200)) 
    if request.method == "GET":
        return redirect("/")
    req = request.get_json()
    if "EventName" in req and "Key" in req:
        s3_obj = req["Records"][0]["s3"]["object"]
        event = req["EventName"].split(":")[-1]
        content_type = ""
        if "contentType" in s3_obj:
            content_type = s3_obj["contentType"]
        try:
            with open("/app-data/webhook.log", "a") as logfile:
                logfile.write(req["Records"][0]["eventTime"] + "\t" + req["EventName"] + "\t" + req["Key"] + "\n")
                logfile.write(s3_obj["eTag"] + "\t")
                logfile.write(content_type + "\t")
                logfile.write(str(s3_obj["size"]) + "\n\n")
        except Exception as e:
            print(e)        
        handle_webhook(
                        client=client,
                        paths=PATHS,
                        out_file=OUTPUT,
                        fieldnames=FIELDS,
                        key=req["Key"],
                        content_type=content_type,
                        event=event)
    else:
        return app.make_response(("request not valid", 200))
    return app.make_response(("webhook status: OK", 200))


@app.route("/health")
def health():
    """
    Used by MinIO to check when the app is ready.
    """
    return app.make_response(("app status: live", 200))


@app.route("/init")
def init():
    """
    Called by a GET request from the minio-create-bucket container during startup.
    Uploads local files to MinIO bucket on startup.
    Calls the Update event handler to update the output file.
    """
    if is_bucket_empty(client, SRC_BUCKET):
        upload(client, SRC_DIR, SRC_BUCKET)
        handle_event(client=client, paths=PATHS, out_file=OUTPUT, fieldnames=FIELDS)
    return app.make_response(("app status: initialized\n", 200))
