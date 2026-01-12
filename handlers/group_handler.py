import time
import json
import uuid
import random
from chat_server.utils.file_io import FileIO
from chat_server.utils.response import success, error
from chat_server.config import GROUPS_DB, USERS_DB  # <--- Added USERS_DB

# Define constants
ROLE_OWNER = "owner"
ROLE_MEMBER = "member"

class GroupHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.groups_io = FileIO(GROUPS_DB)
        self.users_io = FileIO(USERS_DB)  # <--- Load Users DB to look up names

    async def handle_get_chats(self, wrapper, data):
        """
        Action: 'get_chats'
        Returns all groups the user is a member of.
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id: 
            return await wrapper.send_error("get_chats", "Unauthorized")

        groups_db = self.groups_io.read_json()
        my_chats = []

        # Filter groups where user is a member
        for group in groups_db.values():
            if user_id in group.get("members", {}):
                my_chats.append(group)

        # Send list back to Flutter
        await wrapper.send_json("chat_list", my_chats)

    async def handle_create_group(self, wrapper, data):
        """
        Action: 'create_group'
        Payload: { 'name': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id: 
            return await wrapper.send_error("create_group", "Unauthorized")

        group_name = data.get("name")
        if not group_name:
            return await wrapper.send_error("create_group", "Missing group name")

        # 1. Fetch Creator's Username
        users = self.users_io.read_json()
        creator_name = users.get(user_id, {}).get("username", "Unknown")

        groups_db = self.groups_io.read_json()

        # 2. Generate IDs
        group_id = str(uuid.uuid4())
        join_code = str(uuid.uuid4())[:6].upper()

        new_group = {
            "id": group_id,
            "name": group_name,
            "type": "group",
            "owner_id": user_id,
            "join_code": join_code,
            "members": {
                user_id: {
                    "role": ROLE_OWNER,
                    "username": creator_name,  # <--- Store Username
                    "joined_at": time.time(),
                    "muted": False
                }
            }
        }

        # 3. Save to DB
        groups_db[group_id] = new_group
        self.groups_io.write_json(groups_db)

        # 4. Send Success
        await wrapper.send_json("create_group", new_group)

    async def handle_join_group(self, wrapper, data):
        """
        Action: 'join_group'
        Payload: { 'join_code': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id: 
            return await wrapper.send_error("join_group", "Unauthorized")

        code = data.get("join_code")
        if not code:
            return await wrapper.send_error("join_group", "Missing join code")

        groups_db = self.groups_io.read_json()

        target_group = None
        
        # Find group by code
        for group in groups_db.values():
            if group.get("join_code") == code:
                target_group = group
                break

        if not target_group:
            return await wrapper.send_error("join_group", "Invalid Join Code")

        # Check if already a member
        if user_id in target_group["members"]:
            return await wrapper.send_error("join_group", "Already a member")

        # 1. Fetch Joiner's Username
        users = self.users_io.read_json()
        joiner_name = users.get(user_id, {}).get("username", "Unknown")

        # 2. Add member with Username
        new_member_data = {
            "role": ROLE_MEMBER,
            "username": joiner_name,  # <--- Store Username
            "joined_at": time.time(),
            "muted": False
        }
        target_group["members"][user_id] = new_member_data

        # 3. Save DB
        self.groups_io.write_json(groups_db)

        # 4. Notify the joiner (Success)
        await wrapper.send_json("join_group", target_group)

        # 5. Notify other members (Real-time update)
        notification_payload = {
            "group_id": target_group["id"],
            "user_id": user_id,
            "user_data": new_member_data
        }

        # Broadcast loop
        for member_id in target_group["members"]:
            if member_id != user_id:
                await self.client_manager.send_to_user(member_id, "group_member_joined", notification_payload)