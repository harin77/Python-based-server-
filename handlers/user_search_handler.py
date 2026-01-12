import json
from chat_server.utils.file_io import FileIO
from chat_server.config import USERS_DB

class UserSearchHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.users_io = FileIO(USERS_DB)

    async def handle_search(self, wrapper, data):
        """
        Action: 'search_user'
        Payload: { 'query': 'username_or_handle' }
        """
        query = data.get("query", "").strip()
        
        if not query:
            return await wrapper.send_error("search_result", "Please enter a username or handle")

        users = self.users_io.read_json()
        found_user = None

        # Logic: Priority Search
        # 1. Exact Handle Match (e.g. "User#1234")
        # 2. Exact Username Match (e.g. "User")
        
        # Search Loop
        for u in users.values():
            handle = u.get("handle", "")
            username = u.get("username", "")
            
            if query == handle:
                found_user = u
                break
            elif query == username:
                found_user = u
                # Don't break yet, in case there's a better handle match later? 
                # Actually, strictly breaking on first exact match is usually safer for performance.
                break

        if found_user:
            # Construct Safe Public Profile (No Passwords!)
            public_profile = {
                "id": found_user["id"],
                "username": found_user["username"],
                "handle": found_user.get("handle", "Unknown"),
                "avatar": found_user.get("avatar") # Base64 string or URL
            }
            
            # Send 'search_result' (Singular) to match Flutter logic
            await wrapper.send_json("search_result", {
                "status": "success",
                "data": public_profile
            })
        else:
            await wrapper.send_json("search_result", {
                "status": "error",
                "message": "User not found"
            })