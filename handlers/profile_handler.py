import json
import os
import base64
from chat_server.utils.file_io import FileIO
from chat_server.config import USERS_DB, AVATARS_DIR

class ProfileHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.users_io = FileIO(USERS_DB)

    async def handle_update_profile(self, wrapper, data):
        """
        Action: 'update_profile'
        Payload: { 'image_data': 'base64_string', ...other fields }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id:
            return await wrapper.send_error("auth", "Authentication required")

        # 1. Load User DB
        users = self.users_io.read_json()
        
        if user_id not in users:
            return await wrapper.send_error("profile", "User not found")

        # 2. Process Avatar Update
        image_data = data.get("image_data")
        if image_data:
            try:
                # Clean Base64 string
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                
                # Decode and Save to Disk
                file_bytes = base64.b64decode(image_data)
                filename = f"{user_id}.jpg"
                file_path = os.path.join(AVATARS_DIR, filename)
                
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                
                # Update DB record with filename
                users[user_id]["avatar"] = filename
            except Exception as e:
                return await wrapper.send_error("profile", f"Failed to save avatar: {e}")

        # 3. Update other fields (bio, etc.)
        if "bio" in data:
            users[user_id]["bio"] = data["bio"]

        # 4. Save Changes
        self.users_io.write_json(users)
        
        # 5. Send Response
        clean_user = {k: v for k, v in users[user_id].items() if k != "password"}
        await wrapper.send_json("profile_updated", clean_user)

    async def handle_get_avatar(self, wrapper, data):
        """
        Action: 'get_avatar'
        Payload: { 'target_id': str }
        """
        target_id = data.get("target_id") or data.get("user_id")
        
        if not target_id:
            return await wrapper.send_error("avatar", "Missing target_id")

        # 1. Check DB for avatar filename
        users = self.users_io.read_json()
        user = users.get(target_id)
        
        base64_img = None

        if user:
            # Check for "avatar" key (new standard) or "avatar_url" (legacy)
            filename = user.get("avatar") or user.get("avatar_url")
            
            if filename:
                # Construct path using the global config
                file_path = os.path.join(AVATARS_DIR, filename)
                
                # Read file if it exists
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            base64_img = base64.b64encode(f.read()).decode('utf-8')
                    except Exception as e:
                        print(f"Error reading avatar: {e}")

        # 2. Send Result (Empty image if not found, client handles placeholder)
        await wrapper.send_json("avatar_data", {
            "user_id": target_id,
            "image": base64_img 
        })