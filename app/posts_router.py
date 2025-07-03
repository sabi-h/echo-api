# app/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from typing import Optional, List
import uuid
import os
import httpx
import tempfile
from datetime import datetime
from app.tables import Post, User, PostLike
from app import schemas
from app.dependencies import get_current_user
from supabase import create_client, Client
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import random

router = APIRouter()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = "echo-voice-notes"

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supported audio formats for recording (ElevenLabs supports these formats)
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".flac"}


def get_audio_duration(file_path: str) -> Optional[float]:
    """Get audio file duration in seconds using mutagen"""
    try:
        audio_file = mutagen.File(file_path)
        if audio_file is not None:
            return float(audio_file.info.length)
        return None
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return None


def format_post_response(post, current_user_id: Optional[int] = None) -> dict:
    """Format post data to match frontend interface"""

    # Since we're using Post.select(Post.all_columns(), Post.author.all_columns())
    # The author data should be directly accessible in the post object
    username = post.get("username", "unknown")
    display_name = post.get("display_name") or username
    avatar = post.get("avatar") or f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"

    # Format timestamp
    created_at = post.get("created_at")
    if isinstance(created_at, datetime):
        timestamp = created_at.isoformat()
    else:
        timestamp = str(created_at) if created_at else datetime.now().isoformat()

    # Handle tags - ensure it's a proper list
    tags = post.get("tags", [])
    if isinstance(tags, str):
        try:
            import json

            tags = json.loads(tags)
        except:
            tags = []
    elif not isinstance(tags, list):
        tags = []

    return {
        "id": str(post["id"]),
        "username": username,
        "display_name": display_name,
        "avatar": avatar,
        "audio_url": post.get("voice_file_path") or "",
        "duration": post.get("duration") or 0.0,
        "voice_style": post.get("voice_style") or "natural",
        "likes": post.get("likes") or 0,
        "timestamp": timestamp,
        "is_liked": False,  # Will be set properly in endpoints
        "tags": tags,
        "content": post.get("text_content") or "",
        "created_at": created_at if isinstance(created_at, datetime) else datetime.now(),
        "listen_count": post.get("listen_count") or random.randint(1, 100),
    }


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


async def generate_voice_from_text(
    text: str, voice_style: str = "natural", username: str = None
) -> tuple[Optional[str], Optional[float]]:
    """Generate voice using ElevenLabs and upload to Supabase Storage"""
    if not text or not text.strip():
        return None, None

    try:
        # Use specific voice ID for "nat" username, otherwise use default
        voice_id = "4cyB2A28b75DWiJqvXcI" if username == "nat" else ELEVENLABS_VOICE_ID

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}

        # Adjust voice settings based on style
        voice_settings = {"stability": 0.5, "similarity_boost": 0.5}
        if voice_style == "energetic":
            voice_settings = {"stability": 0.3, "similarity_boost": 0.7}
        elif voice_style == "calm":
            voice_settings = {"stability": 0.8, "similarity_boost": 0.3}

        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": voice_settings,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)

            if response.status_code == 200:
                audio_content = response.content

                # Upload to Supabase Storage
                unique_filename = f"voice_{uuid.uuid4()}.mp3"

                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_file.write(audio_content)
                    temp_file_path = temp_file.name

                try:
                    # Get duration before uploading
                    duration = get_audio_duration(temp_file_path) or 0.0

                    # Upload from file path
                    with open(temp_file_path, "rb") as f:
                        upload_response = supabase.storage.from_(BUCKET_NAME).upload(
                            path=unique_filename, file=f, file_options={"content-type": "audio/mpeg"}
                        )

                    # Get public URL
                    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                    return public_url, duration

                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)

            else:
                print(f"ElevenLabs API error: {response.status_code}")
                return None, None

    except Exception as e:
        print(f"Error generating voice: {e}")
        return None, None


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


def generate_random_tags() -> List[str]:
    """Generate 1-3 random tags for posts"""
    available_tags = [
        "music",
        "podcast",
        "story",
        "news",
        "tech",
        "ai",
        "creative",
        "funny",
        "inspiration",
        "motivation",
        "lifestyle",
        "health",
        "fitness",
        "food",
        "travel",
        "business",
        "education",
        "entertainment",
        "gaming",
        "sports",
        "art",
        "science",
        "nature",
        "books",
        "movies",
        "coding",
        "startup",
        "productivity",
        "mindfulness",
        "social",
        "family",
        "work",
        "hobby",
    ]

    import random

    num_tags = random.randint(1, 3)  # 1 to 3 tags
    return random.sample(available_tags, num_tags)


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
    voice_style: Optional[str] = Form("natural"),
    current_user: User = Depends(get_current_user),
):
    """Create post from text content"""
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Text content is required")

    # Generate random tags
    tag_list = generate_random_tags()

    # Get username for voice selection
    username = current_user["username"] if isinstance(current_user, dict) else current_user.username

    # Generate voice from text using ElevenLabs
    voice_file_url, duration = await generate_voice_from_text(content, voice_style, username)

    # Create post in database
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id
    new_post = Post(
        text_content=content.strip(),
        voice_file_path=voice_file_url,
        duration=duration or 0.0,
        voice_style=voice_style,
        tags=tag_list,
        author=user_id,
    )
    await new_post.save()

    # Get post with author info - but manually combine the data
    post_data = await Post.select().where(Post.id == new_post.id).first()

    # Add current user data to post_data
    post_data["username"] = current_user["username"]
    post_data["display_name"] = current_user.get("display_name") or current_user["username"]
    post_data["avatar"] = current_user.get("avatar")

    return format_post_response(post_data, user_id)


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

        # Get duration of original audio
        duration = get_audio_duration(temp_file_path) or 0.0

        # Transcribe audio to text
        transcribed_text = await transcribe_audio_to_text(temp_file_path)

        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio. Please try again.")

        if not transcribed_text.strip():
            raise HTTPException(status_code=400, detail="No speech detected in the audio file")

        # Generate random tags
        tag_list = generate_random_tags()

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
            voice_file_path=original_audio_url,  # Store original recording
            duration=duration,
            voice_style="original",  # Mark as original recording
            tags=tag_list,
            author=user_id,
        )
        await new_post.save()

        # Get post data and add current user data
        post_data = await Post.select().where(Post.id == new_post.id).first()

        # Add current user data to post_data
        post_data["username"] = current_user["username"]
        post_data["display_name"] = current_user.get("display_name") or current_user["username"]
        post_data["avatar"] = current_user.get("avatar")

        response_data = format_post_response(post_data, user_id)
        response_data["original_recording_url"] = original_audio_url

        return response_data

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
async def get_posts(skip: int = 0, limit: int = 10, current_user: User = Depends(get_current_user)):
    # Get current user ID for like status
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    # Get posts without join
    posts = await Post.select().offset(skip).limit(limit).order_by(Post.created_at, ascending=False)

    total = await Post.count()

    # Get all unique author IDs
    author_ids = list(set(post["author"] for post in posts))

    # Fetch all authors in one query
    authors = await User.select().where(User.id.is_in(author_ids))
    authors_dict = {author["id"]: author for author in authors}

    # Check which posts the current user liked
    if posts:
        post_ids = [post["id"] for post in posts]
        liked_posts = await PostLike.select(PostLike.post).where(
            (PostLike.user == user_id) & (PostLike.post.is_in(post_ids))
        )
        liked_post_ids = {like["post"] for like in liked_posts}
    else:
        liked_post_ids = set()

    formatted_posts = []
    for post in posts:
        # Add author data to post
        author = authors_dict.get(post["author"])
        if author:
            post["username"] = author["username"]
            post["display_name"] = author.get("display_name") or author["username"]
            post["avatar"] = author.get("avatar")
        else:
            # Fallback if author not found
            post["username"] = "unknown"
            post["display_name"] = "Unknown User"
            post["avatar"] = "https://api.dicebear.com/7.x/avataaars/svg?seed=unknown"

        formatted_post = format_post_response(post, user_id)
        formatted_post["is_liked"] = post["id"] in liked_post_ids
        formatted_posts.append(formatted_post)

    return {"posts": formatted_posts, "total": total}


@router.get("/my-posts", response_model=schemas.PostListResponse)
async def get_my_posts(skip: int = 0, limit: int = 10, current_user=Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    posts = (
        await Post.select()
        .where(Post.author == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Post.created_at, ascending=False)
    )

    total = await Post.count().where(Post.author == user_id)

    # All user's own posts - add current user data directly
    formatted_posts = []
    for post in posts:
        # Add current user data to post
        post["username"] = current_user["username"]
        post["display_name"] = current_user.get("display_name") or current_user["username"]
        post["avatar"] = current_user.get("avatar")

        formatted_post = format_post_response(post, user_id)
        formatted_post["is_liked"] = True  # User's own posts
        formatted_posts.append(formatted_post)

    return {"posts": formatted_posts, "total": total}


@router.get("/{post_id}", response_model=schemas.PostResponse)
async def get_post(post_id: int, current_user: User = Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    post = await Post.select().where(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get the author data
    author = await User.select().where(User.id == post["author"]).first()
    if author:
        post["username"] = author["username"]
        post["display_name"] = author.get("display_name") or author["username"]
        post["avatar"] = author.get("avatar")
    else:
        # Fallback if author not found
        post["username"] = "unknown"
        post["display_name"] = "Unknown User"
        post["avatar"] = "https://api.dicebear.com/7.x/avataaars/svg?seed=unknown"

    # Check if user liked this post
    liked = await PostLike.select().where((PostLike.user == user_id) & (PostLike.post == post_id)).first()

    formatted_post = format_post_response(post, user_id)
    formatted_post["is_liked"] = liked is not None

    return formatted_post


@router.post("/{post_id}/like", response_model=schemas.LikeResponse)
async def toggle_like_post(post_id: int, current_user: User = Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    # Check if post exists
    post = await Post.select().where(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if user already liked this post
    existing_like = await PostLike.select().where((PostLike.user == user_id) & (PostLike.post == post_id)).first()

    if existing_like:
        # Unlike the post
        await existing_like.remove()
        await Post.update({Post.likes: Post.likes - 1}).where(Post.id == post_id)
        is_liked = False
        message = "Post unliked"
    else:
        # Like the post
        new_like = PostLike(user=user_id, post=post_id)
        await new_like.save()
        await Post.update({Post.likes: Post.likes + 1}).where(Post.id == post_id)
        is_liked = True
        message = "Post liked"

    # Get updated like count
    updated_post = await Post.select().where(Post.id == post_id).first()
    total_likes = updated_post["likes"]

    return {"message": message, "is_liked": is_liked, "total_likes": total_likes}


@router.post("/{post_id}/listen")
async def increment_listen_count(post_id: int):
    """Increment the listen count for a post"""
    post = await Post.select().where(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await Post.update({Post.listen_count: Post.listen_count + 1}).where(Post.id == post_id)
    return {"message": "Listen count updated"}


@router.delete("/{post_id}")
async def delete_post(post_id: int, current_user=Depends(get_current_user)):
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id

    post = await Post.select().where(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["author"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    # Delete related likes first
    await PostLike.delete().where(PostLike.post == post_id)

    # Delete voice file from Supabase Storage if exists
    if post["voice_file_path"]:
        await delete_voice_file(post["voice_file_path"])

    # Delete the post
    await post.remove()

    return {"message": "Post deleted successfully"}
