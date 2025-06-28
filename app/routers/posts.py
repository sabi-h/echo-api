# app/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import aiofiles
import os
import uuid
from datetime import datetime
from app.tables import Post, User
from app import schemas
from app.dependencies import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"

@router.post("/", response_model=schemas.PostResponse)
async def create_post(
    text_content: Optional[str] = Form(None),
    voice_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    if not text_content and not voice_file:
        raise HTTPException(
            status_code=400,
            detail="Either text content or voice file must be provided"
        )
    
    voice_file_path = None
    
    # Handle voice file upload
    if voice_file:
        # Validate file type (basic validation)
        allowed_types = ["audio/mpeg", "audio/wav", "audio/m4a", "audio/mp3", "audio/ogg"]
        if voice_file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only audio files are allowed."
            )
        
        # Generate unique filename
        file_extension = voice_file.filename.split(".")[-1] if "." in voice_file.filename else "mp3"
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        voice_file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        async with aiofiles.open(voice_file_path, 'wb') as out_file:
            content = await voice_file.read()
            await out_file.write(content)
    
    # Create post in database
    new_post = Post(
        text_content=text_content,
        voice_file_path=voice_file_path,
        author=current_user.id
    )
    await new_post.save()
    
    # Get post with author info
    post_with_author = await Post.select(Post.all_columns(), Post.author.all_columns()).where(
        Post.id == new_post.id
    ).first()
    
    return {
        "id": post_with_author.id,
        "text_content": post_with_author.text_content,
        "voice_file_path": post_with_author.voice_file_path,
        "author": post_with_author.author.to_dict(),
        "created_at": post_with_author.created_at,
        "updated_at": post_with_author.updated_at
    }

@router.get("/", response_model=schemas.PostListResponse)
async def get_posts(skip: int = 0, limit: int = 10):
    posts = await Post.select(
        Post.all_columns(), 
        Post.author.all_columns()
    ).offset(skip).limit(limit).order_by(Post.created_at, ascending=False)
    
    total = await Post.count()
    
    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            "id": post.id,
            "text_content": post.text_content,
            "voice_file_path": post.voice_file_path,
            "author": post.author.to_dict(),
            "created_at": post.created_at,
            "updated_at": post.updated_at
        })
    
    return {"posts": formatted_posts, "total": total}

@router.get("/my-posts", response_model=schemas.PostListResponse)
async def get_my_posts(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    posts = await Post.select(
        Post.all_columns(), 
        Post.author.all_columns()
    ).where(
        Post.author == current_user.id
    ).offset(skip).limit(limit).order_by(Post.created_at, ascending=False)
    
    total = await Post.count().where(Post.author == current_user.id)
    
    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            "id": post.id,
            "text_content": post.text_content,
            "voice_file_path": post.voice_file_path,
            "author": post.author.to_dict(),
            "created_at": post.created_at,
            "updated_at": post.updated_at
        })
    
    return {"posts": formatted_posts, "total": total}

@router.get("/{post_id}", response_model=schemas.PostResponse)
async def get_post(post_id: int):
    post = await Post.select(
        Post.all_columns(), 
        Post.author.all_columns()
    ).where(Post.id == post_id).first()
    
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "text_content": post.text_content,
        "voice_file_path": post.voice_file_path,
        "author": post.author.to_dict(),
        "created_at": post.created_at,
        "updated_at": post.updated_at
    }

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user)
):
    post = await Post.select().where(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.author != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this post"
        )
    
    # Delete voice file if exists
    if post.voice_file_path and os.path.exists(post.voice_file_path):
        os.remove(post.voice_file_path)
    
    await post.remove()
    
    return {"message": "Post deleted successfully"}