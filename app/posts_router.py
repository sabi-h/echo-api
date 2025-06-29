# app/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from typing import Optional
import uuid
import os
import httpx
import tempfile
from datetime import datetime
from app.tables import Post, User
from app import schemas
from app.dependencies import get_current_user
from supabase import create_client, Client

router = APIRouter()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = "echo-voice-notes"

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-api-key")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supported audio formats for recording (ElevenLabs supports these formats)
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".flac"}


async def transcribe_audio_to_text(audio_file_path: str) -> Optional[str]:
    """Convert audio file to text using ElevenLabs Speech-to-Text API"""
    try:
        url = "https://api.elevenlabs.io/v1/speech-to-text"

        headers = {"xi-api-key": ELEVENLABS_API_KEY}

        # Read the file content
        with open(audio_file_path, "rb") as f:
            audio_content = f.read()

        # Prepare the multipart form data
        files = {"file": (os.path.basename(audio_file_path), audio_content, "audio/mpeg")}

        data = {"model_id": "scribe_v1"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                # ElevenLabs might return the text directly or in a 'text' field
                if isinstance(result, dict):
                    transcribed_text = result.get("text", result.get("transcript", "")).strip()
                else:
                    transcribed_text = str(result).strip()
                return transcribed_text
            else:
                print(f"ElevenLabs Speech-to-Text API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"Error transcribing audio with ElevenLabs: {e}")
        return None


async def generate_voice_from_text(text: str) -> Optional[str]:
    """Generate voice using ElevenLabs and upload to Supabase Storage"""
    if not text or not text.strip():
        return None

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}

        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)

            if response.status_code == 200:
                audio_content = response.content

                # Upload to Supabase Storage
                unique_filename = f"voice_{uuid.uuid4()}.mp3"

                # Save to temporary file
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_file.write(audio_content)
                    temp_file_path = temp_file.name

                try:
                    # Upload from file path
                    with open(temp_file_path, "rb") as f:
                        upload_response = supabase.storage.from_(BUCKET_NAME).upload(
                            path=unique_filename, file=f, file_options={"content-type": "audio/mpeg"}
                        )

                        print(upload_response)

                    # Get public URL
                    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                    return public_url

                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)

            else:
                print(f"ElevenLabs API error: {response.status_code}")
                return None

    except Exception as e:
        print(f"Error generating voice: {e}")
        return None


async def delete_voice_file(file_url: str):
    """Delete voice file from Supabase Storage"""
    try:
        filename = file_url.split("/")[-1]
        response = supabase.storage.from_(BUCKET_NAME).remove([filename])
        if response.error:
            print(f"Error deleting file: {response.error}")
    except Exception as e:
        print(f"Error deleting file: {e}")
        pass


def validate_audio_file(file: UploadFile) -> bool:
    """Validate if the uploaded file is a supported audio format"""
    if not file.filename:
        return False

    file_extension = os.path.splitext(file.filename.lower())[1]
    return file_extension in SUPPORTED_AUDIO_FORMATS


@router.post("/transcribe", response_model=schemas.AudioTranscriptionResponse)
async def transcribe_audio_only(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe audio to text without creating a post (useful for testing)"""

    # Validate file type
    if not validate_audio_file(audio_file):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported formats: {', '.join(SUPPORTED_AUDIO_FORMATS)}",
        )

    # Check file size (ElevenLabs has a 10MB limit for speech-to-text)
    if audio_file.size and audio_file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large. Maximum size is 10MB")

    temp_file_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Transcribe audio to text
        transcribed_text = await transcribe_audio_to_text(temp_file_path)

        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio. Please try again.")

        if not transcribed_text.strip():
            raise HTTPException(status_code=400, detail="No speech detected in the audio file")

        return {"transcribed_text": transcribed_text.strip()}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing recording: {e}")
        raise HTTPException(status_code=500, detail="Failed to process recording")

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Error cleaning up temp file: {e}")


@router.post("/", response_model=schemas.PostResponse)
async def create_post(
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Create post from text content"""
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Text content is required")

    # Generate voice from text using ElevenLabs
    voice_file_url = await generate_voice_from_text(content)

    # Create post in database
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id
    new_post = Post(text_content=content.strip(), voice_file_path=voice_file_url, author=user_id)
    await new_post.save()

    # Get post with author info
    post_with_author = (
        await Post.select(Post.all_columns(), Post.author.all_columns()).where(Post.id == new_post.id).first()
    )

    return {
        "id": post_with_author["id"],
        "text_content": post_with_author["text_content"],
        "voice_file_path": post_with_author["voice_file_path"],
        "author": post_with_author["author"],
        "created_at": post_with_author["created_at"],
        "updated_at": post_with_author["updated_at"],
    }


@router.post("/from-recording", response_model=schemas.PostResponseWithOriginal)
async def create_post_from_recording(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Create post from voice recording - keeps both original recording and transcribed text"""

    # Validate file type
    if not validate_audio_file(audio_file):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported formats: {', '.join(SUPPORTED_AUDIO_FORMATS)}",
        )

    # Check file size (ElevenLabs has a 10MB limit for speech-to-text)
    if audio_file.size and audio_file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large. Maximum size is 10MB")

    temp_file_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Transcribe audio to text
        transcribed_text = await transcribe_audio_to_text(temp_file_path)

        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio. Please try again.")

        if not transcribed_text.strip():
            raise HTTPException(status_code=400, detail="No speech detected in the audio file")

        # Upload original recording to Supabase Storage
        original_audio_url = None
        try:
            unique_filename = f"original_{uuid.uuid4()}{os.path.splitext(audio_file.filename)[1]}"

            with open(temp_file_path, "rb") as f:
                upload_response = supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=f,
                    file_options={"content-type": audio_file.content_type or "audio/mpeg"},
                )

            original_audio_url = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
        except Exception as e:
            print(f"Error uploading original audio: {e}")

        # Create post in database with transcribed text and original audio
        user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id
        new_post = Post(
            text_content=transcribed_text.strip(),
            voice_file_path=original_audio_url,  # Store original recording instead of generated voice
            author=user_id,
        )
        await new_post.save()

        # Get post with author info
        post_with_author = (
            await Post.select(Post.all_columns(), Post.author.all_columns()).where(Post.id == new_post.id).first()
        )

        return {
            "id": post_with_author["id"],
            "text_content": post_with_author["text_content"],
            "voice_file_path": post_with_author["voice_file_path"],
            "original_recording_url": original_audio_url,
            "author": post_with_author["author"],
            "created_at": post_with_author["created_at"],
            "updated_at": post_with_author["updated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing recording: {e}")
        raise HTTPException(status_code=500, detail="Failed to process recording")

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Error cleaning up temp file: {e}")


@router.get("/", response_model=schemas.PostListResponse)
async def get_posts(skip: int = 0, limit: int = 10):
    posts = (
        await Post.select(Post.all_columns(), Post.author.all_columns())
        .offset(skip)
        .limit(limit)
        .order_by(Post.created_at, ascending=False)
    )

    total = await Post.count()

    formatted_posts = []
    for post in posts:
        formatted_posts.append(
            {
                "id": post["id"],
                "text_content": post["text_content"],
                "voice_file_path": post["voice_file_path"],
                "author": post["author"],
                "created_at": post["created_at"],
                "updated_at": post["updated_at"],
            }
        )

    return {"posts": formatted_posts, "total": total}


@router.get("/my-posts", response_model=schemas.PostListResponse)
async def get_my_posts(skip: int = 0, limit: int = 10, current_user=Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    posts = (
        await Post.select(Post.all_columns(), Post.author.all_columns())
        .where(Post.author == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Post.created_at, ascending=False)
    )

    total = await Post.count().where(Post.author == user_id)

    formatted_posts = []
    for post in posts:
        formatted_posts.append(
            {
                "id": post["id"],
                "text_content": post["text_content"],
                "voice_file_path": post["voice_file_path"],
                "author": post["author"],
                "created_at": post["created_at"],
                "updated_at": post["updated_at"],
            }
        )

    return {"posts": formatted_posts, "total": total}


@router.get("/{post_id}", response_model=schemas.PostResponse)
async def get_post(post_id: int):
    post = await Post.select(Post.all_columns(), Post.author.all_columns()).where(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "id": post["id"],
        "text_content": post["text_content"],
        "voice_file_path": post["voice_file_path"],
        "author": post["author"],
        "created_at": post["created_at"],
        "updated_at": post["updated_at"],
    }


@router.delete("/{post_id}")
async def delete_post(post_id: int, current_user=Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    post = await Post.select().where(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["author"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    # Delete voice file from Supabase Storage if exists
    if post["voice_file_path"]:
        await delete_voice_file(post["voice_file_path"])

    await post.remove()

    return {"message": "Post deleted successfully"}
