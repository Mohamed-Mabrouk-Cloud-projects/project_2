import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from mysql.connector import Error
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
MAX_VIDEO_SECONDS = 30

s3 = boto3.client("s3", region_name=AWS_REGION)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_CV_EXTENSIONS = {"pdf", "doc", "docx"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

def allowed(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

def create_presigned_put(key, content_type, expires=900):
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
        HttpMethod="PUT",
    )

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/upload-url")
def upload_url():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    filename = data.get("filename") or ""
    content_type = data.get("content_type") or "application/octet-stream"
    file_type = data.get("file_type")

    if not name or not filename or file_type not in {"photo", "cv", "video"}:
        return jsonify(error="Invalid upload request"), 400

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_map = {
        "photo": ALLOWED_IMAGE_EXTENSIONS,
        "cv": ALLOWED_CV_EXTENSIONS,
        "video": ALLOWED_VIDEO_EXTENSIONS,
    }
    if ext not in allowed_map[file_type]:
        return jsonify(error=f"Unsupported {file_type} file type"), 400

    if file_type == "photo":
        folder = "photos"
    elif file_type == "cv":
        folder = "cvs"
    else:
        folder = "videos"

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    key = f"pending/{folder}/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"

    return jsonify(
        upload_url=create_presigned_put(key, content_type),
        object_key=key,
        max_video_seconds=MAX_VIDEO_SECONDS if file_type == "video" else None,
    )

@app.post("/api/applications")
def create_application():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    photo_key = data.get("photo_key")
    cv_key = data.get("cv_key")
    video_key = data.get("video_key")

    if not name or not photo_key or not cv_key:
        return jsonify(error="Name, photo and CV are required"), 400

    if video_key and not video_key.startswith("pending/videos/"):
        return jsonify(error="Invalid video key"), 400

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO applications (name, photo_key, cv_key, video_key)
            VALUES (%s, %s, %s, %s)
            """,
            (name, photo_key, cv_key, video_key),
        )
        conn.commit()
        application_id = cursor.lastrowid

        # Move objects from pending/ to a stable application prefix.
        keys = [("photo_key", photo_key), ("cv_key", cv_key)]
        if video_key:
            keys.append(("video_key", video_key))

        final_keys = {}
        for field, old_key in keys:
            suffix = old_key.split("/", 2)[-1]
            folder = {"photo_key": "photo", "cv_key": "cv", "video_key": "video"}[field]
            new_key = f"applications/{application_id}/{folder}/{suffix}"
            s3.copy_object(
                Bucket=S3_BUCKET,
                CopySource={"Bucket": S3_BUCKET, "Key": old_key},
                Key=new_key,
            )
            s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
            final_keys[field] = new_key

        cursor.execute(
            """
            UPDATE applications
            SET photo_key=%s, cv_key=%s, video_key=%s
            WHERE id=%s
            """,
            (
                final_keys["photo_key"],
                final_keys["cv_key"],
                final_keys.get("video_key"),
                application_id,
            ),
        )
        conn.commit()
        return jsonify(message="Application submitted successfully", id=application_id), 201

    except (Error, ClientError) as exc:
        if conn:
            conn.rollback()
        app.logger.exception("Application submission failed")
        return jsonify(error="Could not save application"), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.get("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
