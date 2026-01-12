Python WebSocket Chat ServerA complete, asynchronous chat backend using websockets and JSON flat-file storage.📦 SetupInstall Requirements:pip install -r requirements.txt
Start Server:python server.py
🔧 FeaturesAuthentication: Register/Login with Bcrypt password hashing.User Handles: Unique @username#1234 system.Groups: Create groups, Join via 6-digit code, Admin/Owner roles.Messaging: Real-time text, Reply Trees (threads).Voice: WebRTC Signaling (Offer/Answer/ICE) relay.Persistence: JSON files in database/ with auto-backups in database/backups/.📡 API Protocol (JSON)Login:{
  "type": "login",
  "data": { "handle": "User#1234", "password": "securepass" }
}
Send Message:{
  "type": "message",
  "data": { 
    "to": "group_id_here", 
    "content": "Hello World", 
    "reply_to": "parent_msg_id" 
  }
}
Voice Signal:{
  "type": "voice_signal",
  "data": { "target_id": "user_id", "signal_type": "offer", "payload": {...} }
}
