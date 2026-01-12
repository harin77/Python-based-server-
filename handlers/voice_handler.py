import time
import logging
from chat_server.utils.file_io import FileIO
from chat_server.config import VOICE_DB, USERS_DB

class VoiceHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.voice_io = FileIO(VOICE_DB)
        self.users_io = FileIO(USERS_DB)

    async def handle_join_voice(self, wrapper, data):
        """
        Action: 'join_voice'
        Payload: { 'group_id': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id: return
        
        group_id = data.get("group_id")
        if not group_id:
            return await wrapper.send_error("voice", "Missing group_id")

        voice_db = self.voice_io.read_json()
        users_db = self.users_io.read_json()

        # 1. Get User Details (Upgrade: Include Username/Avatar)
        user_info = users_db.get(user_id, {})
        username = user_info.get("username", "Unknown")
        avatar = user_info.get("avatar", None)

        # 2. Create channel if missing
        if group_id not in voice_db:
            voice_db[group_id] = {"participants": {}}

        # 3. Add to Voice DB
        participant_data = {
            "id": user_id,
            "username": username,
            "avatar": avatar,
            "joined_at": time.time(),
            "is_muted": True,     # Default: Muted
            "is_speaking": False,
            "raised_hand": False
        }
        
        voice_db[group_id]["participants"][user_id] = participant_data
        self.voice_io.write_json(voice_db)

        # 4. Send Success to Joiner (with list of existing peers)
        current_participants = voice_db[group_id]["participants"]
        
        await wrapper.send_json("voice_joined", {
            "group_id": group_id,
            "participants": current_participants
        })

        # 5. Broadcast to Others
        notify_payload = {
            "group_id": group_id,
            "user": participant_data
        }
        await self._broadcast_to_channel(group_id, "voice_user_joined", notify_payload, exclude_user=user_id)
        logging.info(f"User {username} joined voice channel {group_id}")

    async def handle_leave_voice(self, wrapper, data):
        """
        Action: 'leave_voice'
        Payload: { 'group_id': str }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        group_id = data.get("group_id")
        
        if not group_id: return

        voice_db = self.voice_io.read_json()

        if group_id in voice_db and user_id in voice_db[group_id]["participants"]:
            # Remove user
            del voice_db[group_id]["participants"][user_id]
            
            # If empty, clean up the channel entry
            if not voice_db[group_id]["participants"]:
                del voice_db[group_id]
            
            self.voice_io.write_json(voice_db)

            # Notify others
            notify_payload = {
                "group_id": group_id,
                "user_id": user_id
            }
            await self._broadcast_to_channel(group_id, "voice_user_left", notify_payload, exclude_user=user_id)
            
            # Confirm to sender
            await wrapper.send_json("voice_left", {"group_id": group_id})

    async def handle_voice_state(self, wrapper, data):
        """
        Action: 'voice_state_update'
        Payload: { 'group_id': str, 'is_muted': bool, ... }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        group_id = data.get("group_id")
        
        voice_db = self.voice_io.read_json()
        
        if group_id in voice_db and user_id in voice_db[group_id]["participants"]:
            user_state = voice_db[group_id]["participants"][user_id]
            
            # Update fields selectively
            if "is_muted" in data: user_state["is_muted"] = data["is_muted"]
            if "is_speaking" in data: user_state["is_speaking"] = data["is_speaking"]
            if "raised_hand" in data: user_state["raised_hand"] = data["raised_hand"]

            self.voice_io.write_json(voice_db)

            # Prepare the state payload (only send necessary fields)
            state_payload = {
                "is_muted": user_state["is_muted"],
                "is_speaking": user_state["is_speaking"],
                "raised_hand": user_state["raised_hand"]
            }
            
            # Broadcast payload
            payload = {
                "group_id": group_id,
                "user_id": user_id,
                "state": state_payload
            }
            
            # --- CRITICAL FIX: Broadcast to ALL, including sender (exclude_user=None) ---
            # This ensures the sender's UI receives the confirmation needed for the glow effect.
            await self._broadcast_to_channel(group_id, "voice_state_updated", payload, exclude_user=None)

    async def handle_voice_signal(self, wrapper, data):
        """
        Action: 'voice_signal'
        Payload: { 'group_id': str, 'signal_type': str, 'payload': dict }
        
        Broadcasts WebRTC signals to the entire group (mesh network topology).
        """
        sender_id = self.client_manager.get_user_id(wrapper)
        group_id = data.get("group_id")
        
        # NOTE: Clients MUST send group_id, not target_id, for group calls
        if not group_id: 
             logging.error("Voice signal missing group_id for group call.")
             return

        # Relay Payload
        relay_payload = {
            "from": sender_id,
            "signal_type": data.get("signal_type"),
            "payload": data.get("payload")
        }
        
        # Broadcast signal to all users in the channel, excluding the sender
        await self._broadcast_to_channel(group_id, "voice_signal", relay_payload, exclude_user=sender_id)

    # --- Helper ---
    async def _broadcast_to_channel(self, group_id, event_type, data, exclude_user=None):
        """Sends event to all participants in the voice channel."""
        voice_db = self.voice_io.read_json()
        if group_id not in voice_db: return

        participants = voice_db[group_id]["participants"]
        
        for pid in participants:
            # If exclude_user is None, this condition is skipped.
            if pid == exclude_user: continue
            
            await self.client_manager.send_to_user(pid, event_type, data)