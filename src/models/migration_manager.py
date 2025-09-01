import sqlite3
import logging
from pathlib import Path
import importlib.util

from src.config import settings
from src.models.database import get_schema_version, initialize_schema_version

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = settings.ROOT_DIR / "migrations"

def _update_schema_version(conn: sqlite3.Connection, version: int):
    """スキーマバージョンを更新する。"""
    cursor = conn.cursor()
    cursor.execute("UPDATE schema_version SET version = ?", (version,))
    conn.commit()
    logger.info(f"データベースのスキーマバージョンを {version} に更新しました。")

def apply_migrations(conn: sqlite3.Connection):
    """
    データベースのマイグレーションを適用する。
    `migrations`ディレクトリ内のスクリプトを検出し、現在のバージョンから順番に実行する。
    """
    initialize_schema_version(conn)
    current_version = get_schema_version(conn)
    logger.info(f"現在のデータベーススキーマバージョン: {current_version}")

    migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.py"))

    if not migration_files:
        logger.info("適用するマイグレーションファイルが見つかりません。")
        return

    latest_script_version = int(migration_files[-1].name.split('_')[0])
    logger.info(f"最新のマイグレーションスクリプトバージョン: {latest_script_version}")

    if current_version >= latest_script_version:
        logger.info("データベースは最新の状態です。")
        return

    for migration_file in migration_files:
        script_version = int(migration_file.name.split('_')[0])

        if script_version > current_version:
            logger.info(f"マイグレーション {migration_file.name} を適用します...")
            try:
                # ファイルからモジュールを動的にインポート
                spec = importlib.util.spec_from_file_location(migration_file.stem, migration_file)
                migration_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_module)

                # upgrade関数を実行
                if hasattr(migration_module, 'upgrade'):
                    migration_module.upgrade(conn)
                    _update_schema_version(conn, script_version)
                    logger.info(f"マイグレーション {migration_file.name} の適用が完了しました。")
                else:
                    logger.error(f"マイグレーションスクリプト {migration_file.name} に `upgrade` 関数がありません。")
                    raise AttributeError(f"Upgrade function missing in {migration_file.name}")

            except Exception as e:
                logger.critical(f"マイグレーション {migration_file.name} の適用中にエラーが発生しました: {e}", exc_info=True)
                # エラーが発生したら、それ以降のマイグレーションは中止する
                raise
