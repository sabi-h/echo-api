from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# User schemas
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
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


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    id: int
    voice_file_path: Optional[str] = None
    author: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostResponseWithOriginal(PostBase):
    """Extended response for posts created from recordings that keep original audio"""

    id: int
    voice_file_path: Optional[str] = None
    original_recording_url: Optional[str] = None
    author: int
    created_at: datetime
    updated_at: Optional[datetime] = None

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
