import os
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.conf.apps import AppConfig

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="app",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    table_classes=[
        "app.tables.User",
        "app.tables.Post",
    ],
    migration_dependencies=[],
    commands=[],
)