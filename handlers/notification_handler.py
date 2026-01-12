import os
import time
import uuid
import json
from chat_server.utils.file_io import FileIO
from chat_server.utils.response import success, error
from chat_server.utils.push_service import PushService
from chat_server.config import DB_DIR

# Define path strictly for this handler since it wasn't in main config
NOTIFICATIONS_DB = os.path.join(DB_DIR, "notifications.json")

class NotificationHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager
        self.file_io = FileIO(NOTIFICATIONS_DB)

    async def create_notification(self, user_id, title, message, type="info"):
        """
        Internal method to generate a notification. 
        Can be called by other handlers (e.g., when a group invite is sent).
        """
        notifications = self.file_io.read_json()
        
        if user_id not in notifications:
            notifications[user_id] = []
            
        notification = {
            "id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "type": type,
            "read": False,
            "timestamp": time.time()
        }
        
        notifications[user_id].append(notification)
        self.file_io.write_json(notifications)
        
        # 1. Send Real-time Push (if applicable)
        await PushService.send_push_notification(user_id, title, message)

        # 2. Send Real-time Socket Event (if connected)
        payload = success("new_notification", notification)
        await self.client_manager.send_personal_message(payload, user_id)

    async def handle_get_notifications(self, websocket, data, user_id):
        """
        Action: 'get_notifications'
        """
        if not user_id:
            return await websocket.send(json.dumps(error("auth", "Authentication required")))

        notifications_db = self.file_io.read_json()
        user_notifications = notifications_db.get(user_id, [])

        # Sort by newest first
        user_notifications.sort(key=lambda x: x["timestamp"], reverse=True)

        await websocket.send(json.dumps(success("notification_list", user_notifications)))

    async def handle_mark_read(self, websocket, data, user_id):
        """
        Action: 'mark_notification_read'
        Payload: { 'notification_id': str }
        """
        if not user_id: return

        notification_id = data.get("notification_id")
        notifications_db = self.file_io.read_json()
        
        if user_id in notifications_db:
            for notif in notifications_db[user_id]:
                if notif["id"] == notification_id:
                    notif["read"] = True
                    self.file_io.write_json(notifications_db)
                    
                    await websocket.send(json.dumps(success("notification_read", {"id": notification_id})))
                    return

        await websocket.send(json.dumps(error("notification", "Notification not found")))