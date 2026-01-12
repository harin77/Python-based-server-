import os
import base64
import subprocess
import uuid
import logging
from PIL import Image
from chat_server.config import IMAGES_DIR, VIDEOS_DIR, TEMP_DIR

class MediaUtils:
    @staticmethod
    def save_temp_file(base64_data, ext):
        """Decodes Base64 and saves to a temp file."""
        try:
            # Strip metadata prefix if present (e.g., "data:image/png;base64,")
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            file_id = str(uuid.uuid4())
            temp_filename = f"{file_id}{ext}"
            temp_path = os.path.join(TEMP_DIR, temp_filename)
            
            with open(temp_path, "wb") as f:
                f.write(base64.b64decode(base64_data))
                
            return temp_path, file_id
        except Exception as e:
            logging.error(f"Temp Save Error: {e}")
            return None, None

    @staticmethod
    def compress_image(temp_path, file_id):
        """Compresses image using Pillow."""
        try:
            output_filename = f"{file_id}.jpg" # Standardize to JPG
            output_path = os.path.join(IMAGES_DIR, output_filename)
            
            with Image.open(temp_path) as img:
                # Convert to RGB (handles PNG/RGBA issues)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Resize if larger than 1920px width
                if img.width > 1920:
                    ratio = 1920 / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((1920, new_height), Image.Resampling.LANCZOS)
                
                # Save with JPEG compression
                img.save(output_path, "JPEG", quality=70, optimize=True)
            
            return output_filename
        except Exception as e:
            logging.error(f"Image Compression Error: {e}")
            return None

    @staticmethod
    def compress_video(temp_path, file_id):
        """
        Compresses video using FFmpeg.
        Falls back to raw file move if FFmpeg fails or is missing.
        """
        output_filename = f"{file_id}.mp4"
        output_path = os.path.join(VIDEOS_DIR, output_filename)
        
        try:
            # FFmpeg command: H.264 codec, CRF 28 (Good compression), AAC audio
            command = [
                'ffmpeg', '-i', temp_path, 
                '-vcodec', 'libx264', 
                '-crf', '28', 
                '-preset', 'fast', 
                '-acodec', 'aac', 
                output_path
            ]
            
            # Execute
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                return output_filename
            else:
                raise Exception(f"FFmpeg returned {result.returncode}")
                
        except Exception as e:
            logging.warning(f"Video Compression failed (saving raw): {e}")
            # Fallback: Just move the file
            try:
                os.rename(temp_path, output_path)
                return output_filename
            except OSError as mv_error:
                logging.error(f"Move failed: {mv_error}")
                return None

    @staticmethod
    def cleanup(path):
        """Removes the temporary file."""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    @staticmethod
    def get_file_base64(media_type, filename):
        """Reads a file from disk and returns Base64 string."""
        folder = IMAGES_DIR if media_type == "image" else VIDEOS_DIR
        path = os.path.join(folder, filename)
        
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logging.error(f"File Read Error: {e}")
            return None