import time
import uuid
import logging
from chat_server.utils.file_io import FileIO
from chat_server.config import MESSAGES_DB, GROUPS_DB

class MessageHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.messages_io = FileIO(MESSAGES_DB)
        self.groups_io = FileIO(GROUPS_DB)

    async def handle_send(self, wrapper, data):
        """
        Action: 'message'
        Payload: { 'to': str, 'content': str, 'msg_type': str, 'reply_to': str }
        """
        sender_id = self.client_manager.get_user_id(wrapper)
        if not sender_id:
            return await wrapper.send_error("message", "Unauthorized")

        target_id = data.get("to")
        content = data.get("content")
        msg_type = data.get("msg_type", "text") 
        reply_to = data.get("reply_to")

        if not target_id or not content:
            return await wrapper.send_error("message", "Missing 'to' or 'content'")

        # 1. Load DBs Fresh
        messages_db = self.messages_io.read_json()
        groups_db = self.groups_io.read_json()

        # 2. Determine Chat Key
        is_group = target_id in groups_db

        if is_group:
            chat_key = target_id
            if sender_id not in groups_db[chat_key].get("members", {}):
                 return await wrapper.send_error("message", "You are not a member")
        else:
            chat_key = "_".join(sorted([sender_id, target_id]))

        # 3. Create Message Object
        msg_obj = {
            "id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "content": content,
            "type": msg_type,
            "timestamp": int(time.time() * 1000), 
            "reply_to": reply_to,
            "is_deleted": False,
            "reactions": {}
        }

        # 4. Save to DB
        if chat_key not in messages_db:
            messages_db[chat_key] = []
        
        msg_obj['chat_id'] = target_id if is_group else chat_key

        messages_db[chat_key].append(msg_obj)
        self.messages_io.write_json(messages_db)

        # 5. Broadcast
        response_chat_id = target_id if is_group else sender_id 
        response_payload = {
            "chat_id": response_chat_id, 
            "message": msg_obj
        }
        
        await self._broadcast_to_target(target_id, "message", response_payload, groups_db, sender_id, is_group)

    async def handle_get_history(self, wrapper, data):
        """
        Action: 'get_chat_history'
        Payload: { 'chat_id': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        target_id = data.get("chat_id")
        
        if not user_id or not target_id: return

        # 1. Load DBs Fresh
        messages_db = self.messages_io.read_json()
        groups_db = self.groups_io.read_json()
        
        # 2. Determine Chat Key
        is_group = target_id in groups_db
        pinned_info = None
        
        if is_group:
            chat_key = target_id
            group_data = groups_db.get(chat_key, {})
            
            # Security: Check membership
            if user_id not in group_data.get("members", {}):
                return await wrapper.send_error("chat_history", "Not a member")
            
            # --- FIX: Check for Pinned Message ---
            pinned_id = group_data.get("pinned_message_id")
            if pinned_id:
                chat_msgs = messages_db.get(chat_key, [])
                for m in chat_msgs:
                    if m["id"] == pinned_id:
                        pinned_info = {
                            "id": pinned_id,
                            "content": m["content"]
                        }
                        break
        else:
            # Private: Sort IDs
            chat_key = "_".join(sorted([user_id, target_id]))

        # 3. Retrieve Messages
        history = messages_db.get(chat_key, [])
        
        # 4. Send back (With Pinned Info)
        await wrapper.send_json("chat_history", {
            "chat_id": target_id,
            "messages": history,
            "pinned_message": pinned_info 
        })

    async def handle_delete(self, wrapper, data):
        """
        Action: 'delete_message'
        Payload: { 'chat_id': str, 'message_id': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")

        if not chat_id or not message_id: return

        messages_db = self.messages_io.read_json()
        groups_db = self.groups_io.read_json()

        is_group = chat_id in groups_db
        if is_group:
            chat_key = chat_id
        else:
            chat_key = "_".join(sorted([user_id, chat_id]))

        if chat_key not in messages_db:
            return await wrapper.send_error("delete_message", "Chat not found")

        # Find and Update
        found = False
        for msg in messages_db[chat_key]:
            if msg["id"] == message_id:
                if msg["sender_id"] == user_id:
                    msg["is_deleted"] = True
                    msg["content"] = "🚫 This message was deleted"
                    msg["type"] = "deleted"
                    found = True
                break
        
        if found:
            self.messages_io.write_json(messages_db)
            
            payload = {
                "chat_id": chat_id,
                "message_id": message_id
            }
            await self._broadcast_to_target(chat_id, "message_deleted", payload, groups_db, user_id, is_group)

    async def handle_typing(self, wrapper, data):
        """
        Action: 'typing'
        Payload: { 'to': str, 'is_typing': bool }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        target_id = data.get("to")
        groups_db = self.groups_io.read_json()
        is_group = target_id in groups_db

        payload = {
            "from": user_id,
            "chat_id": target_id,
            "is_typing": data.get("is_typing", True)
        }

        await self._broadcast_to_target(target_id, "typing", payload, groups_db, user_id, is_group, exclude_sender=True)

    async def handle_pin(self, wrapper, data):
        """
        Action: 'pin_message'
        Payload: { 'chat_id': str, 'message_id': str }
        """
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user_id = self.client_manager.get_user_id(wrapper)
        
        # 1. Load Group DB
        groups_db = self.groups_io.read_json()
        
        # 2. Validate
        if chat_id not in groups_db:
            return await wrapper.send_error("pin_message", "Group not found")

        # 3. Save Pin State to Group Data
        groups_db[chat_id]["pinned_message_id"] = message_id
        self.groups_io.write_json(groups_db)
        
        # 4. Get the actual message content
        messages_db = self.messages_io.read_json()
        pinned_content = "Pinned Message" 
        
        chat_msgs = messages_db.get(chat_id, [])
        for m in chat_msgs:
            if m["id"] == message_id:
                pinned_content = m["content"]
                break

        # 5. Broadcast to Group
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "content": pinned_content,
            "pinned_by": user_id
        }
        
        await self._broadcast_to_target(chat_id, "message_pinned", payload, groups_db, user_id, is_group=True)

    # --- Helper Methods ---

    async def _broadcast_to_target(self, target_id, event_type, data, groups_db, sender_id, is_group, exclude_sender=False):
        """
        Routes the message to a group list or private pair.
        """
        recipients = set()

        if is_group:
            members = groups_db.get(target_id, {}).get("members", {}).keys()
            for member_id in members:
                recipients.add(member_id)
        else:
            recipients.add(target_id)
            recipients.add(sender_id)

        for uid in recipients:
            if exclude_sender and uid == sender_id:
                continue
            await self.client_manager.send_to_user(uid, event_type, data)