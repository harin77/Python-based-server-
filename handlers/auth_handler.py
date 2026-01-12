import json
import random
import uuid
import time
import logging
import base64
import os
from chat_server.utils.file_io import FileIO
from chat_server.utils.encryption import hash_password, verify_password, generate_token
from chat_server.config import USERS_DB, AVATARS_DIR

class AuthHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.users_io = FileIO(USERS_DB)

    def _generate_user_tag(self):
        return f"{random.randint(0, 9999):04d}"

    def _create_handle(self, username, tag):
        return f"{username}#{tag}"

    async def handle_register(self, wrapper, data):
        """
        Action: 'register'
        Payload: { 'username': str, 'password': str, 'image_data': str (optional base64) }
        """
        username = data.get("username")
        password = data.get("password")
        image_data = data.get("image_data") # Base64 string from Flutter
        
        if not username or not password:
            return await wrapper.send_error("register", "Missing fields")

        users = self.users_io.read_json()

        # 1. Generate Unique Handle
        tag = self._generate_user_tag()
        handle = self._create_handle(username, tag)
        
        # Simple collision check
        attempts = 0
        while any(u.get("handle") == handle for u in users.values()) and attempts < 5:
            tag = self._generate_user_tag()
            handle = self._create_handle(username, tag)
            attempts += 1
            
        if attempts >= 5:
            return await wrapper.send_error("register", "Username is too popular, try another.")

        # 2. Generate User ID
        user_id = str(uuid.uuid4())
        
        # 3. Handle Avatar Saving (Save to Disk, not DB)
        avatar_filename = None
        if image_data:
            try:
                # Remove header if present (e.g. "data:image/png;base64,")
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                
                # Decode Base64
                file_bytes = base64.b64decode(image_data)
                
                # Create Filename: userID.jpg
                avatar_filename = f"{user_id}.jpg"
                file_path = os.path.join(AVATARS_DIR, avatar_filename)
                
                # Write to disk
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                    
                logging.info(f"Saved avatar to {file_path}")
            except Exception as e:
                logging.error(f"Failed to save avatar: {e}")
                # Don't fail registration, just proceed without avatar
                avatar_filename = None

        # 4. Create User Object
        new_user = {
            "id": user_id,
            "username": username,
            "tag": tag,
            "handle": handle,
            "password": hash_password(password),
            "created_at": time.time(),
            "avatar": avatar_filename, # Save FILENAME, not raw data
            "fcm_token": None
        }
        
        # 5. Save to DB
        users[user_id] = new_user
        self.users_io.write_json(users)
        
        # 6. Auto Login
        await self.client_manager.register_client(user_id, wrapper)
        
        # 7. Send Success Response
        # Strip password before sending back
        response_user = {k: v for k, v in new_user.items() if k != "password"}
        response_user["token"] = generate_token(user_id)
        
        # Send only (msg_type, data). The wrapper adds 'status': 'success'
        await wrapper.send_json("register", response_user)
        logging.info(f"Registered new user: {handle}")

    async def handle_login(self, wrapper, data):
        """
        Action: 'login'
        Payload: { 'handle': str, 'password': str, 'fcm_token': str }
        """
        identifier = data.get("handle")
        password = data.get("password")
        fcm_token = data.get("fcm_token")
        
        if not identifier or not password:
            return await wrapper.send_error("login", "Missing credentials")

        users = self.users_io.read_json()
        
        user = None
        # Search by Handle OR Username
        for u in users.values():
            if (u.get("handle") == identifier or u.get("username") == identifier):
                user = u
                break
            
        if user and verify_password(password, user["password"]):
            # Update FCM token
            if fcm_token:
                user["fcm_token"] = fcm_token
                users[user["id"]] = user
                self.users_io.write_json(users)

            # Register connection
            await self.client_manager.register_client(user["id"], wrapper)
            
            # Response
            response_user = {k: v for k, v in user.items() if k != "password"}
            response_user["token"] = generate_token(user["id"])
            
            # Send only (msg_type, data)
            await wrapper.send_json("login", response_user)
            logging.info(f"User logged in: {user['handle']}")
        else:
            await wrapper.send_error("login", "Invalid credentials")

    async def handle_reconnect(self, wrapper, data):
        """
        Action: 'reconnect'
        Payload: { 'user_id': str }
        
        Called by the Flutter app when it restarts and has a stored User ID.
        """
        user_id = data.get("user_id")
        
        if not user_id:
            return await wrapper.send_error("reconnect", "Missing User ID")

        users = self.users_io.read_json()
        
        # Verify user exists
        if user_id in users:
            # 1. Re-bind this new socket connection to the existing User ID
            await self.client_manager.register_client(user_id, wrapper)
            
            logging.info(f"🔄 User reconnected: {users[user_id]['username']}")
            
            # 2. Send success so the app knows it's authenticated
            await wrapper.send_json("reconnect", {
                "message": "Session restored"
            })
        else:
            await wrapper.send_error("reconnect", "User not found")