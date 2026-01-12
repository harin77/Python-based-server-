import json
import logging
from chat_server.utils.response import error

# Import Handler Classes
from chat_server.handlers.auth_handler import AuthHandler
from chat_server.handlers.group_handler import GroupHandler
from chat_server.handlers.message_handler import MessageHandler
from chat_server.handlers.voice_handler import VoiceHandler
from chat_server.handlers.admin_handler import AdminHandler
from chat_server.handlers.user_search_handler import UserSearchHandler
from chat_server.handlers.media_handler import MediaHandler
from chat_server.handlers.profile_handler import ProfileHandler

class Dispatcher:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        
        # Initialize Handlers
        self.auth_handler = AuthHandler(client_manager)
        self.group_handler = GroupHandler(client_manager)
        self.message_handler = MessageHandler(client_manager)
        self.voice_handler = VoiceHandler(client_manager)
        self.admin_handler = AdminHandler(client_manager)
        self.user_search_handler = UserSearchHandler(client_manager)
        self.media_handler = MediaHandler(client_manager)
        self.profile_handler = ProfileHandler(client_manager)

    async def dispatch(self, wrapper, raw_message):
        """
        Central router: parses JSON 'type' and calls appropriate handler.
        """
        # 1. Parse JSON
        try:
            event = json.loads(raw_message)
        except json.JSONDecodeError:
            await wrapper.send_error("system", "Invalid JSON")
            return

        # 2. Extract Basic Info
        msg_type = event.get("type")
        data = event.get("data", {})
        
        # ==========================================
        # ROUTING TABLE
        # ==========================================

        # --- AUTHENTICATION ---
        if msg_type == "register":
            await self.auth_handler.handle_register(wrapper, data)
        elif msg_type == "login":
            await self.auth_handler.handle_login(wrapper, data)
        elif msg_type == "reconnect":
            await self.auth_handler.handle_reconnect(wrapper, data)
        
        # --- GROUPS ---
        elif msg_type == "get_chats":
            await self.group_handler.handle_get_chats(wrapper, data)
        elif msg_type == "create_group":
            await self.group_handler.handle_create_group(wrapper, data)
        elif msg_type == "join_group":
            await self.group_handler.handle_join_group(wrapper, data)

        # --- MESSAGING ---
        elif msg_type == "message":
            await self.message_handler.handle_send(wrapper, data)
        elif msg_type == "delete_message":
            await self.message_handler.handle_delete(wrapper, data)
        elif msg_type == "typing":
            await self.message_handler.handle_typing(wrapper, data)
        elif msg_type == "get_chat_history":
            await self.message_handler.handle_get_history(wrapper, data)
        elif msg_type == "pin_message": # <--- THIS IS THE KEY FIX
            await self.message_handler.handle_pin(wrapper, data)

        # --- VOICE / WEBRTC ---
        elif msg_type == "join_voice":
            await self.voice_handler.handle_join_voice(wrapper, data)
        elif msg_type == "leave_voice":
            await self.voice_handler.handle_leave_voice(wrapper, data)
        elif msg_type == "voice_state_update":
            await self.voice_handler.handle_voice_state(wrapper, data)
        elif msg_type == "voice_signal":
            await self.voice_handler.handle_voice_signal(wrapper, data)

        # --- ADMIN ACTIONS ---
        elif msg_type == "admin_action":
            await self.admin_handler.handle_admin_action(wrapper, data)

        # --- SEARCH ---
        elif msg_type == "search_user":
            await self.user_search_handler.handle_search(wrapper, data)

        # --- MEDIA ---
        elif msg_type == "upload_media":
            await self.media_handler.handle_upload_media(wrapper, data)
        elif msg_type == "get_media":
            await self.media_handler.handle_get_media(wrapper, data)
        elif msg_type == "media_ref":
            await self.media_handler.handle_media_ref(wrapper, data)

        # --- PROFILE / AVATAR ---
        elif msg_type == "update_profile":
            await self.profile_handler.handle_update_profile(wrapper, data)
        elif msg_type == "get_avatar":
            await self.profile_handler.handle_get_avatar(wrapper, data)

        # --- SYSTEM / HEALTH ---
        elif msg_type == "health_check":
            await wrapper.send_json("health_check", {"status": "ok"})

        # --- UNKNOWN ---
        else:
            logging.warning(f"⚠️ Unknown message type received: {msg_type}")
            await wrapper.send_error("system", f"Unknown type: {msg_type}")