import os
from piccolo.conf.apps import AppConfig

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="app",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    table_classes=[
        "app.tables.User",
        "app.tables.Post",
        "app.tables.PostLike",
    ],
    migration_dependencies=[],
    commands=[],
)
