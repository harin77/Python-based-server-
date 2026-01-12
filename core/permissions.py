# Role Constants
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

def get_user_role(group, user_id):
    """
    Helper to determine the role of a user in a specific group.
    
    Updated for Dictionary Structure:
    group = {
        "members": {
            "uid_1": { "role": "owner", ... },
            "uid_2": { "role": "member", ... }
        }
    }
    """
    # 1. Check if members dict exists
    members = group.get("members", {})
    
    # 2. Check if user is in the group
    if user_id not in members:
        return None
        
    # 3. Retrieve user data safely
    user_data = members[user_id]
    
    # 4. Return role (Default to MEMBER if key is missing)
    return user_data.get("role", ROLE_MEMBER)

# --- Permission Checks ---

def can_manage_members(user_role):
    """Allowed to Kick/Ban users."""
    return user_role in [ROLE_OWNER, ROLE_ADMIN]

def can_delete_group(user_role):
    """Allowed to delete the entire group."""
    return user_role == ROLE_OWNER

def can_mute_members(user_role):
    """Allowed to mute/unmute others."""
    return user_role in [ROLE_OWNER, ROLE_ADMIN]

def can_promote_members(user_role):
    """Allowed to promote member to admin."""
    return user_role == ROLE_OWNER

def can_edit_group_info(user_role):
    """Allowed to change Group Name/Avatar."""
    return user_role in [ROLE_OWNER, ROLE_ADMIN]