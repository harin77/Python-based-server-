import os

# ==========================================
# SERVER CONFIGURATION
# ==========================================
HOST = "0.0.0.0"
PORT = 8765
SECRET_KEY = "dea04de783fb26ce64cd08637803a3434e813a2a36fac5c71f196c79b3c13ef2"

# ==========================================
# DIRECTORY STRUCTURE
# ==========================================
# Get the directory where this config.py file is located (e.g., chat_server/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database Directory
DB_DIR = os.path.join(BASE_DIR, "database")
BACKUP_DIR = os.path.join(DB_DIR, "backups")

# Logs Directory
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Uploads/Media Directory
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
AVATARS_DIR = os.path.join(UPLOADS_DIR, "avatars") # <--- ADDED THIS
IMAGES_DIR = os.path.join(UPLOADS_DIR, "images")
VIDEOS_DIR = os.path.join(UPLOADS_DIR, "videos")
TEMP_DIR = os.path.join(UPLOADS_DIR, "temp")  # For processing uploads before saving

# ==========================================
# FILE PATHS (JSON DBs)
# ==========================================
USERS_DB = os.path.join(DB_DIR, "users.json")
GROUPS_DB = os.path.join(DB_DIR, "groups.json")
MESSAGES_DB = os.path.join(DB_DIR, "messages.json")
MEDIA_DB = os.path.join(DB_DIR, "media_refs.json")
VOICE_DB = os.path.join(DB_DIR, "voice_channels.json")

# ==========================================
# INITIALIZATION
# ==========================================
# Ensure all critical directories exist on startup
CRITICAL_DIRS = [
    DB_DIR, 
    BACKUP_DIR, 
    LOG_DIR,
    UPLOADS_DIR, 
    AVATARS_DIR, # <--- ADDED THIS
    IMAGES_DIR, 
    VIDEOS_DIR, 
    TEMP_DIR
]

for path in CRITICAL_DIRS:
    os.makedirs(path, exist_ok=True)

# ==========================================
# CONSTANTS
# ==========================================
MAX_JOIN_CODE_LENGTH = 6
BCRYPT_ROUNDS = 12