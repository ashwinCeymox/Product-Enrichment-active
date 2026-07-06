"""
Google Drive Uploader — Uploads base64 images to Google Drive and returns shareable links.

Uses a service account for authentication (no OAuth browser flow needed).
Each uploaded image is made publicly readable so the URL can be used directly
in product page HTML.
"""

import io
import base64
import uuid
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

import config


# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GDriveUploader:
    """Uploads images to Google Drive and generates shareable URLs."""

    def __init__(
        self,
        service_account_file: str = None,
        folder_id: str = None
    ):
        self.service_account_file = (
            service_account_file or config.GDRIVE_SERVICE_ACCOUNT_FILE
        )
        self.folder_id = folder_id or config.GDRIVE_FOLDER_ID
        self._service = None

    @property
    def service(self):
        """Lazy-initialize the Google Drive API service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES,
            )
            self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def upload_base64_image(
        self,
        base64_data: str,
        filename: str = None,
        mime_type: str = "image/png"
    ) -> dict:
        """
        Upload a base64-encoded image to Google Drive.

        Args:
            base64_data: The base64-encoded image data (without data URI prefix).
            filename: Optional filename. Auto-generated if not provided.
            mime_type: MIME type of the image (default: image/png).

        Returns:
            dict with keys:
              - success (bool)
              - file_id (str): Google Drive file ID
              - url (str): Direct viewable URL (lh3.googleusercontent.com format)
              - drive_url (str): Standard Google Drive sharing URL
              - error (str): error message if failed
        """
        if not base64_data:
            return self._error_result("No image data provided")

        if not self.folder_id:
            return self._error_result("No Google Drive folder ID configured")

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_id = uuid.uuid4().hex[:8]
            ext = mime_type.split("/")[-1]
            if ext == "jpeg":
                ext = "jpg"
            filename = f"product_img_{timestamp}_{short_id}.{ext}"

        try:
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            image_stream = io.BytesIO(image_bytes)

            # File metadata
            file_metadata = {
                "name": filename,
                "parents": [self.folder_id],
            }

            # Upload
            media = MediaIoBaseUpload(
                image_stream,
                mimetype=mime_type,
                resumable=True,
            )

            print(f"[GDrive] Uploading {filename} ({len(image_bytes)} bytes)...")

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            file_id = file.get("id")

            # Make the file publicly readable
            self.service.permissions().create(
                fileId=file_id,
                body={
                    "type": "anyone",
                    "role": "reader",
                },
            ).execute()

            # Build URLs
            # Direct embeddable URL (used in img tags)
            direct_url = (
                f"https://lh3.googleusercontent.com/d/{file_id}=w1000"
            )
            # Standard sharing URL
            drive_url = (
                f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            )

            print(f"[GDrive] SUCCESS — uploaded as {file_id}")

            return {
                "success": True,
                "file_id": file_id,
                "url": direct_url,
                "drive_url": drive_url,
                "error": "",
            }

        except Exception as e:
            return self._error_result(f"Upload failed: {e}")

    def upload_multiple(
        self,
        images: list,
        filename_prefix: str = "product"
    ) -> list:
        """
        Upload multiple base64 images.

        Args:
            images: List of dicts with "data" (base64) and "mime_type" keys.
            filename_prefix: Prefix for generated filenames.

        Returns:
            List of upload result dicts.
        """
        results = []
        for i, img in enumerate(images):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = img.get("mime_type", "image/png").split("/")[-1]
            if ext == "jpeg":
                ext = "jpg"
            filename = f"{filename_prefix}_{timestamp}_{i+1}.{ext}"

            result = self.upload_base64_image(
                base64_data=img["data"],
                filename=filename,
                mime_type=img.get("mime_type", "image/png"),
            )
            results.append(result)

        return results

    @staticmethod
    def _error_result(message: str) -> dict:
        print(f"[GDrive] ERROR: {message}")
        return {
            "success": False,
            "file_id": "",
            "url": "",
            "drive_url": "",
            "error": message,
        }
