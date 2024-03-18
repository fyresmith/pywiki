import logging
import os
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

LOCAL_BACKUP_FOLDER = 'backups'
LOCAL_DATA_FOLDER = 'data'
DB_PATH = f'{LOCAL_DATA_FOLDER}/data.db'
SERVICE_CREDENTIALS = os.getenv('ROOT_FOLDER') + os.getenv('SERVICE_CREDENTIALS')
BACKUP_FOLDER_ID = os.getenv('BACKUP_FOLDER_ID')
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('ROOT_FOLDER') + 'logs/app.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("app")

def backup_db():
    # Load credentials from the JSON file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_CREDENTIALS,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Build the Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    # Extract file details
    file_name, file_extension = os.path.splitext(os.path.basename(DB_PATH))

    # Create new filename with timestamp
    new_file_name = f'{file_name}_{timestamp}{file_extension}'

    # Set file metadata and content
    file_metadata = {'name': new_file_name, 'parents': [BACKUP_FOLDER_ID]}
    media = MediaFileUpload(DB_PATH, resumable=True)

    # Upload the file
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    backup_thread = threading.Timer(24 * 3600, backup_db)
    backup_thread.name = "backup_db"
    backup_thread.start()

    log.info(f'File {file_name} uploaded to Google Drive with timestamped filename: {new_file_name} (ID: {file["id"]})')


def download_latest_backup():
    # Load credentials from the JSON file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_CREDENTIALS,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Build the Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)

    try:
        # List files in the backup folder
        results = drive_service.files().list(q=f"'{BACKUP_FOLDER_ID}' in parents", orderBy='createdTime desc', fields='files(id, name)').execute()
        files = results.get('files', [])

        if not files:
            logging.warning('No files found in the backup folder.')
            return

        # Get the most recently uploaded file
        latest_backup = files[0]
        latest_backup_id = latest_backup['id']
        latest_backup_name = latest_backup['name']

        # Print the name of the latest backup
        logging.info(f'The most recently uploaded backup file is: {latest_backup_name} (ID: {latest_backup_id})')

        # Download the latest backup to the local folder
        local_backup_path = os.path.join(LOCAL_BACKUP_FOLDER, latest_backup_name)
        request = drive_service.files().get_media(fileId=latest_backup_id)
        with open(local_backup_path, 'wb') as local_file:
            downloader = MediaIoBaseDownload(local_file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        logging.info(f'Latest backup downloaded to: {local_backup_path}')

    except Exception as e:
        logging.error(f'Error during backup download: {e}')


def delete_old_backups():
    # Load credentials from the JSON file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_CREDENTIALS,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Build the Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)

    try:
        # Calculate the date 2 minutes ago in UTC
        deletion_date = datetime.utcnow() - timedelta(minutes=3)

        # List files in the backup folder
        results = drive_service.files().list(q=f"'{BACKUP_FOLDER_ID}' in parents", fields='files(id, name, createdTime)').execute()
        files = results.get('files', [])

        if not files:
            log.info('No files found in the backup folder.')
            return

        # Identify and delete files older than two minutes
        for file in files:
            created_time_utc = datetime.strptime(file['createdTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if created_time_utc < deletion_date:
                drive_service.files().delete(fileId=file['id']).execute()
                log.info(f'Deleted file: {file["name"]} (ID: {file["id"]})')

        log.info('Old backups deleted successfully.')

    except Exception as e:
        log.error(f'Error during old backups deletion: {e}')


def rollback_db():
    # Load credentials from the JSON file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_CREDENTIALS,
        scopes=['https://www.googleapis.com/auth/drive']
    )

    # Build the Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)

    try:
        # List files in the backup folder
        results = drive_service.files().list(q=f"'{BACKUP_FOLDER_ID}' in parents", orderBy='createdTime desc', fields='files(id, name)').execute()
        files = results.get('files', [])

        if not files:
            log.warning('No backup files found in the backup folder.')
            return

        # Get the most recently uploaded backup file
        latest_backup = files[0]
        latest_backup_id = latest_backup['id']
        latest_backup_name = latest_backup['name']

        # Download the latest backup to the local folder
        local_backup_path = os.path.join(LOCAL_BACKUP_FOLDER, latest_backup_name)
        request = drive_service.files().get_media(fileId=latest_backup_id)
        with open(local_backup_path, 'wb') as local_file:
            downloader = MediaIoBaseDownload(local_file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        # Replace the 'data.db' file with the latest backup
        local_data_db_path = os.path.join(LOCAL_DATA_FOLDER, 'data.db')
        os.replace(local_backup_path, local_data_db_path)

        log.info(f'Rollback successful. Latest backup {latest_backup_name} applied to data.db.')

    except Exception as e:
        log.error(f'Error during rollback: {e}')
