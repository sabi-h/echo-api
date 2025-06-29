from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# User schemas
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str
    display_name: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(UserBase):
    id: int
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Post schemas
class PostBase(BaseModel):
    text_content: Optional[str] = None
    voice_style: Optional[str] = "natural"


class PostCreate(PostBase):
    pass


class PostResponse(BaseModel):
    id: str  # Convert to string as frontend expects
    username: str
    display_name: str
    avatar: str
    audio_url: str
    duration: float
    voice_style: str
    likes: int
    timestamp: str
    is_liked: bool
    tags: List[str]
    content: str
    created_at: datetime
    listen_count: Optional[int] = 0

    class Config:
        from_attributes = True


class PostResponseWithOriginal(BaseModel):
    """Extended response for posts created from recordings that keep original audio"""

    id: str
    username: str
    display_name: str
    avatar: str
    audio_url: str
    original_recording_url: Optional[str] = None
    duration: float
    voice_style: str
    likes: int
    timestamp: str
    is_liked: bool
    tags: List[str]
    content: str
    created_at: datetime
    listen_count: Optional[int] = 0

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int


# Audio/Recording schemas
class AudioTranscriptionResponse(BaseModel):
    """Response for audio transcription without creating a post"""

    transcribed_text: str
    confidence: Optional[float] = None


class RecordingUploadResponse(BaseModel):
    """Response for successful recording upload"""

    message: str
    file_url: str
    transcribed_text: Optional[str] = None


# Like schemas
class LikeResponse(BaseModel):
    message: str
    is_liked: bool
    total_likes: int
