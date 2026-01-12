============================
PYTHON-BASED WEBSOCKET CHAT SERVER
============================================================

Author      : Harin (harin77)
Repository  : https://github.com/harin77/Python-based-server-
Language    : Python
Server Type : Asynchronous WebSocket Server
Storage     : JSON (Flat-file Database)

------------------------------------------------------------
PROJECT OVERVIEW
------------------------------------------------------------

This project is a fully asynchronous Python-based WebSocket
chat server designed for real-time communication applications.

It supports:
- User authentication (Register/Login)
- One-to-one and group messaging
- Group creation and join via invite code
- Role-based permissions (Owner, Admin, Member)
- Message replies
- Voice call signaling using WebRTC
- Persistent storage using JSON files
- Automatic database backups

This server is suitable for:
- Chat applications
- Social media apps
- Multiplayer game chat systems
- Voice-enabled communication apps
- College / portfolio projects

------------------------------------------------------------
TECHNOLOGIES USED
------------------------------------------------------------

- Python 3.9+
- asyncio
- websockets
- bcrypt (for password hashing)
- uuid
- json
- datetime

------------------------------------------------------------
FOLDER STRUCTURE
------------------------------------------------------------

Python-based-server-/
│
├── server.py
├── requirements.txt
│
├── database/
│   ├── users.json
│   ├── groups.json
│   ├── messages.json
│   └── backups/
│       ├── users_backup.json
│       ├── groups_backup.json
│       └── messages_backup.json
│
└── README.txt

------------------------------------------------------------
INSTALLATION & SETUP
------------------------------------------------------------

1. Clone the repository:

   git clone https://github.com/harin77/Python-based-server-
   cd Python-based-server-

2. Install required dependencies:

   pip install -r requirements.txt

3. Start the server:

   python server.py

4. Server will start listening on:

   ws://localhost:8765

------------------------------------------------------------
FEATURES
------------------------------------------------------------

1. USER AUTHENTICATION
----------------------
- Secure registration system
- Passwords hashed using bcrypt
- Unique user handles in the format:
  username#1234

2. REAL-TIME MESSAGING
----------------------
- One-to-one private messages
- Group chat messages
- Message reply system
- Message IDs for threading

3. GROUP MANAGEMENT
----------------------
- Create groups
- Join groups via 6-digit invite code
- Group roles:
  - Owner
  - Admin
  - Member
- Admin/Owner moderation support

4. VOICE CALL SIGNALING
----------------------
- WebRTC signaling support
- Offer / Answer / ICE candidate relay
- Enables voice chat integration
- Server acts as signaling bridge

5. DATA PERSISTENCE
----------------------
- Uses JSON files instead of SQL
- Automatically saves:
  - Users
  - Groups
  - Messages
- Backup system to prevent data loss

6. ASYNCHRONOUS DESIGN
----------------------
- Fully non-blocking
- Handles multiple clients simultaneously
- Scalable architecture

------------------------------------------------------------
WEBSOCKET MESSAGE FORMAT (JSON)
------------------------------------------------------------

All communication uses JSON messages.

----------------------
REGISTER
----------------------
{
  "type": "register",
  "data": {
    "username": "harin",
    "password": "mypassword"
  }
}

----------------------
LOGIN
----------------------
{
  "type": "login",
  "data": {
    "handle": "harin#1234",
    "password": "mypassword"
  }
}

----------------------
SEND MESSAGE
----------------------
{
  "type": "message",
  "data": {
    "to": "group_id_or_user_id",
    "content": "Hello everyone!",
    "reply_to": "optional_message_id"
  }
}

----------------------
CREATE GROUP
----------------------
{
  "type": "create_group",
  "data": {
    "group_name": "My Group"
  }
}

----------------------
JOIN GROUP
----------------------
{
  "type": "join_group",
  "data": {
    "invite_code": "123456"
  }
}

----------------------
VOICE SIGNALING
----------------------
{
  "type": "voice_signal",
  "data": {
    "target_id": "user_id",
    "signal_type": "offer",
    "payload": {
      "sdp": "..."
    }
  }
}

------------------------------------------------------------
SECURITY DETAILS
------------------------------------------------------------

- Passwords are never stored in plain text
- Bcrypt hashing with salt
- Unique user IDs generated using UUID
- No direct file access from clients
- Server-side validation for all actions

------------------------------------------------------------
USE CASE EXAMPLES
------------------------------------------------------------

- Chat backend for Flutter / Android apps
- Multiplayer game lobby chat
- Discord-like application backend
- College final year project
- Learning async networking in Python

------------------------------------------------------------
FUTURE IMPROVEMENTS
------------------------------------------------------------

- Database migration to MongoDB / PostgreSQL
- File sharing support
- Message encryption
- Push notifications
- Admin dashboard
- Rate limiting & anti-spam
- Docker deployment
- SSL/TLS support

------------------------------------------------------------
LICENSE
------------------------------------------------------------

This project is open-source.
You are free to modify, distribute, and use it
for personal or educational purposes.

------------------------------------------------------------
AUTHOR
------------------------------------------------------------

Harin
GitHub: https://github.com/harin77

============================================================
END OF README
============================================================
