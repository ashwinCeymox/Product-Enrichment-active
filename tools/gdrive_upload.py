# tools/gdrive_upload.py
"""
Google Drive Uploader — Async wrapper for uploading base64 images to GDrive.

Uses a service account for authentication. Each uploaded image is made
publicly readable so the URL can be used in product page HTML.
"""

import io
import base64
import uuid
import asyncio
from datetime import datetime
from functools import partial

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Module-level service cache (initialized once)
_service = None


def _get_service(service_account_file: str):
    """Get or create the Google Drive API service (cached)."""
    global _service
    if _service is None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=SCOPES,
        )
        _service = build("drive", "v3", credentials=credentials)
    return _service


def _upload_sync(
    base64_data: str,
    mime_type: str,
    filename: str,
    folder_id: str,
    service_account_file: str,
) -> dict:
    """Synchronous upload — runs in executor to avoid blocking the event loop."""
    if not base64_data:
        return _error("No image data provided")
    if not folder_id:
        return _error("No Google Drive folder ID configured")

    try:
        service = _get_service(service_account_file)

        image_bytes = base64.b64decode(base64_data)
        image_stream = io.BytesIO(image_bytes)

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        media = MediaIoBaseUpload(image_stream, mimetype=mime_type, resumable=True)

        file = service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

        file_id = file.get("id")

        # Make publicly readable
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        direct_url = f"https://lh3.googleusercontent.com/d/{file_id}=w1000"
        drive_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

        return {
            "success": True,
            "file_id": file_id,
            "url": direct_url,
            "drive_url": drive_url,
            "error": "",
        }

    except Exception as e:
        return _error(f"Upload failed: {e}")


async def upload_image(
    base64_data: str,
    mime_type: str = "image/png",
    filename: str = None,
    folder_id: str = "",
    service_account_file: str = "service-account.json",
) -> dict:
    """
    Async upload a base64 image to Google Drive.

    Args:
        base64_data: Base64-encoded image (without data URI prefix).
        mime_type: Image MIME type.
        filename: Optional. Auto-generated if not provided.
        folder_id: Google Drive folder ID to upload into.
        service_account_file: Path to the service account JSON key.

    Returns:
        dict with: success, file_id, url, drive_url, error
    """
    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
        filename = f"product_{ts}_{uid}.{ext}"

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        partial(
            _upload_sync,
            base64_data=base64_data,
            mime_type=mime_type,
            filename=filename,
            folder_id=folder_id,
            service_account_file=service_account_file,
        ),
    )
    return result


def _error(msg: str) -> dict:
    print(f"  [gdrive] ERROR: {msg}")
    return {"success": False, "file_id": "", "url": "", "drive_url": "", "error": msg}
