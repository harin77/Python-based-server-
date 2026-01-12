import os
import base64
from chat_server.config import BASE_DIR

# Define where images are stored
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads", "avatars")
os.makedirs(UPLOADS_DIR, exist_ok=True)

def save_avatar_from_base64(user_id, base64_string):
    """
    Decodes a Base64 string and saves it as a PNG file.
    Returns the filename if successful, otherwise None.
    """
    try:
        # Clean the string if it has the data URI prefix (e.g., "data:image/png;base64,...")
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
            
        file_path = os.path.join(UPLOADS_DIR, f"{user_id}.png")
        
        with open(file_path, "wb") as fh:
            fh.write(base64.b64decode(base64_string))
            
        return f"{user_id}.png"
    except Exception as e:
        print(f"Error saving avatar for {user_id}: {e}")
        return None

def get_avatar_as_base64(user_id):
    """
    Reads the user's avatar file and returns it as a Base64 string.
    Returns None if no file exists.
    """
    file_path = os.path.join(UPLOADS_DIR, f"{user_id}.png")
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with open(file_path, "rb") as fh:
            encoded_string = base64.b64encode(fh.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error reading avatar for {user_id}: {e}")
        return None