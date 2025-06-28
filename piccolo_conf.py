from piccolo.conf.apps import AppRegistry
from piccolo.engine.sqlite import SQLiteEngine

DB = SQLiteEngine(path="hackathon.db")

APP_REGISTRY = AppRegistry(
    apps=[
        "app.piccolo_app",
    ]
)