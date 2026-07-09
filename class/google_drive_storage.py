from django.core.files.storage import Storage
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os
import mimetypes
import logging

logger = logging.getLogger(__name__)

class GoogleDriveStorage(Storage):
    """
    Custom Django Storage backend for uploading and managing files on Google Drive.
    Files are organized hierarchically as requested.
    """
    def __init__(self, **kwargs):
        # Load credentials from settings or environment variables
        self.email = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_EMAIL', os.environ.get('GOOGLE_SERVICE_ACCOUNT_EMAIL'))
        self.private_key = getattr(settings, 'GOOGLE_PRIVATE_KEY', os.environ.get('GOOGLE_PRIVATE_KEY'))
        self.folder_id = getattr(settings, 'GOOGLE_DRIVE_HOMEWORK_FOLDER_ID', os.environ.get('GOOGLE_DRIVE_HOMEWORK_FOLDER_ID'))
        
        if not self.email or not self.private_key or not self.folder_id:
            logger.error("Google Drive credentials or Folder ID missing in settings/env.")
            raise ValueError("Google Drive credentials or Folder ID are not configured.")
            
        # Clean private key strings that have escape characters
        if isinstance(self.private_key, str):
            self.private_key = self.private_key.replace('\\n', '\n')
            
        self.credentials = service_account.Credentials.from_service_account_info({
            "private_key": self.private_key,
            "client_email": self.email,
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        self.service = build('drive', 'v3', credentials=self.credentials)

    def _get_or_create_folder(self, folder_name, parent_id):
        """
        Helper method to traverse or create nested directories on Google Drive.
        """
        try:
            # Query if folder already exists under this parent
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed = false"
            response = self.service.files().list(
                q=query, 
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = response.get('files', [])
            if files:
                return files[0]['id']
            else:
                # Create the folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(
                    body=folder_metadata, 
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Created Google Drive folder '{folder_name}' with ID: {folder['id']}")
                return folder['id']
        except Exception as e:
            logger.error(f"Error checking/creating folder '{folder_name}' in parent '{parent_id}': {e}")
            raise IOError(f"Google Drive folder operation failed: {e}")

    def _open(self, name, mode='rb'):
        """
        Opens a file from Google Drive using its file_id (which is saved as 'name').
        """
        try:
            request = self.service.files().get_media(fileId=name)
            file_content = request.execute()
            return io.BytesIO(file_content)
        except Exception as e:
            logger.error(f"Failed to read file {name} from Google Drive: {e}")
            raise IOError(f"Failed to open Google Drive file: {e}")

    def _save(self, name, content):
        """
        Saves file in Google Drive under a nested directory hierarchy, e.g.:
        CLAS / {year} / {month} / {document_type} / {user} / {filename}
        """
        # Ensure path is unix-style for splitting
        normalized_path = name.replace('\\', '/')
        parts = [p for p in normalized_path.split('/') if p]
        
        if not parts:
            filename = name
            folders = []
        else:
            filename = parts[-1]
            folders = parts[:-1]
            
        # Traverse / create directories starting from root folder_id
        current_parent = self.folder_id
        for folder in folders:
            current_parent = self._get_or_create_folder(folder, current_parent)
            
        # Get correct mimetype
        mimetype, _ = mimetypes.guess_type(filename)
        if not mimetype:
            mimetype = 'application/octet-stream'
            
        file_metadata = {
            'name': filename,
            'parents': [current_parent] if current_parent else []
        }
        
        media = MediaIoBaseUpload(content, mimetype=mimetype, resumable=True)
        
        try:
            # Create file
            file = self.service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id',
                supportsAllDrives=True
            ).execute()
            file_id = file['id']
            logger.info(f"Successfully uploaded file '{filename}' to Google Drive. File ID: {file_id}")
            
            # Make the file readable by anyone with the link
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={'role': 'reader', 'type': 'anyone'},
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Set public reader permission on Google Drive file: {file_id}")
            except Exception as perm_err:
                logger.warning(f"Failed to set public permissions on Google Drive file {file_id}: {perm_err}")
                
            return file_id
        except Exception as e:
            logger.error(f"Failed to write file to Google Drive: {e}")
            raise IOError(f"Google Drive upload failed: {e}")

    def exists(self, name):
        """
        Checks if the file exists on Google Drive.
        Old database records contain paths with slashes (e.g. 'clas/lessonplan/...').
        New records store the Google Drive File ID directly (no slashes).
        """
        if not name:
            return False
        if '/' in name or '\\' in name:
            return False
        try:
            self.service.files().get(fileId=name, supportsAllDrives=True).execute()
            return True
        except Exception:
            return False

    def url(self, name):
        """
        Returns the download URL for the file.
        For new files (Google Drive File ID), returns the direct download link.
        For legacy files (S3 paths), falls back to the S3 bucket URL format.
        """
        if not name:
            return ""
            
        # Check if legacy path (contains slashes)
        if '/' in name or '\\' in name:
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            # If MEDIA_URL is already an absolute domain URL (like S3)
            if media_url.startswith('http'):
                return f"{media_url.rstrip('/')}/{name.lstrip('/')}"
            # Fallback to local media URL
            return f"/{media_url.lstrip('/').rstrip('/')}/{name.lstrip('/')}"
            
        # Return direct download Google Drive URL
        return f"https://drive.google.com/uc?export=download&id={name}"

    def delete(self, name):
        """
        Deletes the file from Google Drive.
        """
        if not name or '/' in name or '\\' in name:
            # Avoid trying to delete legacy S3 paths
            return
        try:
            self.service.files().delete(fileId=name, supportsAllDrives=True).execute()
            logger.info(f"Deleted Google Drive file ID: {name}")
        except Exception as e:
            logger.warning(f"Failed to delete Google Drive file {name}: {e}")
