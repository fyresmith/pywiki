import os
import shutil
import threading
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("app")

# Path configurations
DB_PATH = 'data/data.db'
BACKUP_DIR = 'backups'


def backup_db():
    """
    Initiates the database backup process:
    - Creates a 'backups' directory if it doesn't exist.
    - Generates a timestamp for the backup file.
    - Copies the current database to the backup file.
    - Logs successful backup.
    - Schedules the next backup after 24 hours.
    - Removes backups older than three days.

    :return: None
    """
    try:
        # Create 'backups' directory if it doesn't exist
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        # Generate a timestamp for the backup file
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_file = f"{BACKUP_DIR}/backup_{timestamp}.db"

        # Copy the current database to the backup file
        shutil.copyfile(DB_PATH, backup_file)

        # Log successful backup
        log.info(f"Backup created: {backup_file}")

        # Schedule the next backup after 24 hours
        threading.Timer(24 * 3600, backup_db).start()

        # Remove backups older than three days
        remove_old_backups()
    except Exception as e:
        log.error(f"Error during backup: {e}")


def remove_old_backups():
    """
    Removes backups older than three days from the 'backups' directory.

    :return: None
    """
    try:
        current_time = datetime.now()
        for file_name in os.listdir(BACKUP_DIR):
            file_path = os.path.join(BACKUP_DIR, file_name)
            creation_time = datetime.fromtimestamp(os.path.getctime(file_path))

            # Remove backups older than three days
            if current_time - creation_time > timedelta(days=3):
                os.remove(file_path)
                log.info(f"Backup removed (older than three days): {file_path}")
    except Exception as e:
        log.error(f"Error during removing old backups: {e}")


def rollback_db():
    """
    Rolls back the database to the most recent backup.

    :return: None
    """
    try:
        # Find the most recent backup
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')]
        if backup_files:
            latest_backup = max(backup_files, key=os.path.getctime)
            backup_path = os.path.join(BACKUP_DIR, latest_backup)

            # Replace the current database with the backup
            shutil.copyfile(backup_path, DB_PATH)
            log.info(f"Database rolled back to: {latest_backup}")
        else:
            log.warning("No backups available for rollback")
    except Exception as e:
        log.error(f"Error during rollback: {e}")


# Example: Schedule a nightly rollback
# threading.Timer(24 * 3600, rollback_db).start()
