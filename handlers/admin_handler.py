import json
from chat_server.utils.file_io import FileIO
from chat_server.config import GROUPS_DB
# Ensure these are defined in chat_server/core/permissions.py
from chat_server.core.permissions import (
    can_manage_members, can_mute_members, 
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER
)

class AdminHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.groups_io = FileIO(GROUPS_DB)

    async def handle_admin_action(self, wrapper, data):
        """
        Action: 'admin_action'
        Payload: { 
            'group_id': str, 
            'target_id': str, 
            'action': 'kick' | 'mute' | 'unmute' 
        }
        """
        user_id = self.client_manager.get_user_id(wrapper)
        if not user_id:
            return await wrapper.send_error("admin", "Unauthorized")

        # 1. Extract Data
        action = data.get("action")
        group_id = data.get("group_id")
        target_id = data.get("target_id")
        
        if not group_id or not target_id or not action:
            return await wrapper.send_error("admin", "Missing required fields")

        # 2. Load Groups DB
        groups = self.groups_io.read_json()
        
        if group_id not in groups:
            return await wrapper.send_error("admin", "Group not found")

        group = groups[group_id]
        
        # 3. Check Membership
        if user_id not in group.get("members", {}):
            return await wrapper.send_error("admin", "You are not a member of this group")

        # Get member objects safely
        requester_profile = group["members"][user_id]
        target_profile = group["members"].get(target_id)

        # Special check for kick: Target might exist, but we need to verify logic below
        if not target_profile and action != "kick": 
            return await wrapper.send_error("admin", "Target user not in group")

        # Extract roles (Default to MEMBER if missing)
        requester_role = requester_profile.get("role", ROLE_MEMBER)
        target_role = target_profile.get("role", ROLE_MEMBER) if target_profile else ROLE_MEMBER

        # 4. Action Logic
        updated = False
        error_msg = None

        if action == "kick":
            if can_manage_members(requester_role):
                if not target_profile:
                    error_msg = "User already removed"
                elif target_role == ROLE_OWNER:
                    error_msg = "Cannot kick the group owner"
                elif requester_role == ROLE_ADMIN and target_role == ROLE_ADMIN:
                    error_msg = "Admins cannot kick other admins"
                else:
                    # Remove from Dictionary
                    del group["members"][target_id]
                    updated = True
            else:
                error_msg = "Permission denied: You cannot kick members"

        elif action == "mute":
            if can_mute_members(requester_role):
                if target_role == ROLE_OWNER:
                    error_msg = "Cannot mute the group owner"
                else:
                    # Update boolean inside member object
                    if not target_profile.get("muted"):
                        target_profile["muted"] = True
                        updated = True
            else:
                error_msg = "Permission denied: You cannot mute members"

        elif action == "unmute":
            if can_mute_members(requester_role):
                if target_profile.get("muted"):
                    target_profile["muted"] = False
                    updated = True
            else:
                error_msg = "Permission denied: You cannot unmute members"
        
        else:
            error_msg = f"Unknown action: {action}"

        # 5. Save & Broadcast
        if error_msg:
            await wrapper.send_error("admin", error_msg)
        elif updated:
            self.groups_io.write_json(groups)

            payload = {
                "group_id": group_id,
                "action": action,
                "target_id": target_id,
                # Send the updated members list so clients can refresh UI
                "members": group["members"] 
            }

            # Broadcast to all CURRENT members 
            # (If kicked, the target is no longer in keys, so we add them manually to notify them)
            recipients = set(group["members"].keys())
            if action == "kick":
                recipients.add(target_id)

            for member_id in recipients:
                await self.client_manager.send_to_user(member_id, "group_update", payload)
        else:
            await wrapper.send_json("admin", {"status": "no_change", "message": "Action had no effect"})