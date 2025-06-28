from piccolo.table import Table
from piccolo.columns import Integer, Varchar, Text, Timestamp, ForeignKey, Boolean, Serial
from piccolo.columns.defaults.timestamp import TimestampNow


class User(Table, tablename="users"):
    id = Serial(primary_key=True)
    username = Varchar(length=50, unique=True, index=True, null=False)
    hashed_password = Varchar(length=255, null=False)
    is_active = Boolean(default=True)
    created_at = Timestamp(default=TimestampNow())


class Post(Table, tablename="posts"):
    id = Integer(primary_key=True)
    text_content = Text(null=True)
    voice_file_path = Varchar(length=255, null=True)
    author = ForeignKey(references=User, null=False)
    created_at = Timestamp(default=TimestampNow())
    updated_at = Timestamp(null=True)
