# app/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Form
from typing import Optional
import uuid
import os
import httpx
from datetime import datetime
from app.tables import Post, User
from app import schemas
from app.dependencies import get_current_user
from supabase import create_client, Client

router = APIRouter()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = "echo-voice-notes"

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-api-key")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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


@router.post("/", response_model=schemas.PostResponse)
async def create_post(
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
):
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
