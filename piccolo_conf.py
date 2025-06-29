from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
import os


# Supabase PostgreSQL Database Configuration
DB = PostgresEngine(
    config={
        "database": os.getenv("SUPABASE_DB_NAME", "postgres"),
        "user": os.getenv("SUPABASE_DB_USER", "postgres"),
        "password": os.getenv("SUPABASE_DB_PASSWORD"),
        "host": os.getenv("SUPABASE_DB_HOST"),
        "port": int(os.getenv("SUPABASE_DB_PORT", "5432")),
    }
)

APP_REGISTRY = AppRegistry(
    apps=[
        "app.piccolo_app",
    ]
)
