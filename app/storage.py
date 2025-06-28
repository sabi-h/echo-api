from google.cloud import storage
import uuid
import os


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/key.json"

BUCKET_NAME = "echo-voice-notes"
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)


async def upload_voice_file(file_content: bytes, content_type: str, original_filename: str):
    """Upload voice file to GCS and return public URL"""
    file_extension = original_filename.split(".")[-1] if "." in original_filename else "mp3"
    unique_filename = f"voice_{uuid.uuid4()}.{file_extension}"

    blob = bucket.blob(unique_filename)
    blob.upload_from_string(file_content, content_type=content_type)

    # Return public URL
    return f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_filename}"


async def delete_voice_file(file_url: str):
    """Delete voice file from GCS"""
    try:
        filename = file_url.split("/")[-1]
        blob = bucket.blob(filename)
        blob.delete()
    except:
        pass  # Ignore errors for hackathon
