import json
import time
import os
import uuid
import base64
from chat_server.utils.file_io import FileIO
from chat_server.config import MEDIA_DB, IMAGES_DIR, VIDEOS_DIR

# Try importing MediaUtils, fallback if missing
try:
    from chat_server.utils.media_utils import MediaUtils
    HAS_UTILS = True
except ImportError:
    HAS_UTILS = False

class MediaHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.media_io = FileIO(MEDIA_DB)
        # Directories are already created by config.py on startup

    async def handle_media_ref(self, wrapper, data):
        """
        Legacy: Stores metadata for media stored elsewhere (e.g. S3 links).
        Action: 'media_ref'
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id:
            return await wrapper.send_error("media_ref", "Unauthorized")

        url = data.get("url")
        media_type = data.get("media_type")
        size = data.get("size", 0)

        if not url or not media_type:
            return await wrapper.send_error("media_ref", "Missing URL or media type")

        ref_id = str(uuid.uuid4())
        entry = {
            "id": ref_id,
            "uploader": user_id,
            "url": url,
            "type": media_type,
            "size": size,
            "storage": "external",
            "created_at": time.time()
        }

        media_db = self.media_io.read_json()
        media_db[ref_id] = entry
        self.media_io.write_json(media_db)

        await wrapper.send_json("media_uploaded", entry)

    async def handle_upload_media(self, wrapper, data):
        """
        Uploads and saves media files (Image/Video).
        Action: 'upload_media'
        Payload: { 'file_data': 'base64...', 'file_name': 'x.jpg', 'media_type': 'image'|'video' }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id:
            return await wrapper.send_error("upload_media", "Unauthorized")

        raw_data = data.get("file_data")
        file_name = data.get("file_name", "")
        media_type = data.get("media_type")

        if not raw_data or not media_type:
            return await wrapper.send_error("upload_media", "Missing data")

        # 1. Select Directory based on Type
        if media_type == "image":
            target_dir = IMAGES_DIR
            default_ext = ".jpg"
        elif media_type == "video":
            target_dir = VIDEOS_DIR
            default_ext = ".mp4"
        else:
            return await wrapper.send_error("upload_media", "Unsupported media type")

        # 2. Clean Base64 String
        if "," in raw_data:
            raw_data = raw_data.split(",")[1]

        # 3. Generate Safe Filename
        ext = os.path.splitext(file_name)[1].lower()
        if not ext: 
            ext = default_ext
        
        file_id = str(uuid.uuid4())
        final_filename = f"{file_id}{ext}"
        save_path = os.path.join(target_dir, final_filename)

        try:
            # 4. Decode & Save
            file_bytes = base64.b64decode(raw_data)
            
            # (Optional) Compression could go here if HAS_UTILS is True
                
            # Standard Save
            with open(save_path, "wb") as f:
                f.write(file_bytes)

            # 5. Save Metadata
            entry = {
                "id": file_id,
                "uploader": user_id,
                "filename": final_filename, 
                "type": media_type,
                "storage": "local",
                "created_at": time.time()
            }

            media_db = self.media_io.read_json()
            media_db[file_id] = entry
            self.media_io.write_json(media_db)

            # 6. Respond
            await wrapper.send_json("media_uploaded", entry)

        except Exception as e:
            print(f"Upload Error: {e}")
            await wrapper.send_error("upload_media", "Server upload failed")

    async def handle_get_media(self, wrapper, data):
        """
        Retrieves the binary data for a file.
        Action: 'get_media'
        Payload: { 'media_id': str }
        """
        media_id = data.get("media_id")
        media_db = self.media_io.read_json()
        
        if media_id not in media_db:
             return await wrapper.send_error("get_media", "File not found")
             
        info = media_db[media_id]
        
        if info.get("storage") == "external":
             return await wrapper.send_error("get_media", "External file: use URL")

        # Determine path based on type
        if info["type"] == "image":
            file_path = os.path.join(IMAGES_DIR, info["filename"])
        elif info["type"] == "video":
            file_path = os.path.join(VIDEOS_DIR, info["filename"])
        else:
            file_path = None

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    bytes_data = f.read()
                    b64_data = base64.b64encode(bytes_data).decode('utf-8')
                
                await wrapper.send_json("media_data", {
                    "media_id": media_id,
                    "type": info["type"],
                    "file_data": b64_data
                })
            except Exception as e:
                await wrapper.send_error("get_media", "Read error")
        else:
            await wrapper.send_error("get_media", "File missing on disk")