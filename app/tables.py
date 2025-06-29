from piccolo.table import Table
from piccolo.columns import Integer, Varchar, Text, Timestamp, ForeignKey, Boolean, Serial, Float
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.columns.column_types import JSON


class User(Table, tablename="users"):
    id = Serial(primary_key=True)
    username = Varchar(length=50, unique=True, index=True, null=False)
    hashed_password = Varchar(length=255, null=False)
    display_name = Varchar(length=100, null=True)
    avatar = Text(null=True)
    is_active = Boolean(default=True)
    created_at = Timestamp(default=TimestampNow())


class Post(Table, tablename="posts"):
    id = Serial(primary_key=True)
    text_content = Text(null=True)
    voice_file_path = Text(null=True)
    duration = Float(null=True)
    voice_style = Varchar(length=50, null=True, default="natural")
    likes = Integer(default=0)
    listen_count = Integer(default=0)
    tags = JSON(default=list)
    author = ForeignKey(references=User, null=False)
    created_at = Timestamp(default=TimestampNow())
    updated_at = Timestamp(null=True)


class PostLike(Table, tablename="post_likes"):
    id = Serial(primary_key=True)
    user = ForeignKey(references=User, null=False)
    post = ForeignKey(references=Post, null=False)
    created_at = Timestamp(default=TimestampNow())
