import json
import asyncio
import logging

class ClientManager:
    def __init__(self):
        # Maps user_id -> set of websocket connections (supports multi-device)
        self.active_connections: dict[str, set] = {}
        # Maps websocket -> user_id (for fast reverse lookup on disconnect)
        self.ws_to_user: dict = {}

    # ==========================================
    # CORE CONNECTION LOGIC
    # ==========================================

    async def register_client(self, user_id, wrapper):
        """
        Registers a new connection.
        Called by AuthHandler.
        """
        is_new_user = user_id not in self.active_connections
        
        if is_new_user:
            self.active_connections[user_id] = set()
            
        self.active_connections[user_id].add(wrapper)
        self.ws_to_user[wrapper] = user_id
        
        logging.info(f"✅ User {user_id} registered (Total connections: {len(self.ws_to_user)})")
        
        # Broadcast "online" status only if this is their first active connection
        if is_new_user:
            await self._broadcast_presence(user_id, "online")

    async def remove_client(self, wrapper):
        """
        Unregisters a connection.
        Called by server.py when socket closes.
        """
        user_id = self.ws_to_user.get(wrapper)
        
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(wrapper)
                
                # If no more connections, user is offline
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    await self._broadcast_presence(user_id, "offline")
            
            if wrapper in self.ws_to_user:
                del self.ws_to_user[wrapper]
                
            logging.info(f"❌ User {user_id} disconnected.")
            return user_id
        
        return None

    # ==========================================
    # LOOKUP METHODS
    # ==========================================

    def get_user_id(self, wrapper):
        """
        Helper to find who sent a message.
        Used by Dispatcher.
        """
        return self.ws_to_user.get(wrapper)

    def get_user_sockets(self, user_id):
        """Returns a set of all active websockets for a user."""
        return self.active_connections.get(user_id, set())

    def is_online(self, user_id):
        """Checks if a user has any active connections."""
        return user_id in self.active_connections

    # ==========================================
    # MESSAGING HELPERS
    # ==========================================

    async def send_to_user(self, user_id, msg_type, data):
        """
        Sends a standardized JSON message to a specific user.
        Used by Handlers (Group, Message, etc).
        """
        payload = {"type": msg_type, "data": data, "status": "success"}
        await self.send_personal_message(payload, user_id)

    async def send_personal_message(self, message, user_id):
        """
        Sends a raw message to all connected devices of a specific user.
        """
        if isinstance(message, dict):
            message = json.dumps(message)
            
        sockets = self.get_user_sockets(user_id)
        for ws_wrapper in sockets:
            try:
                # Use the wrapper's send method if available
                if hasattr(ws_wrapper, 'send'):
                    await ws_wrapper.send(message)
                # Fallback for raw websockets
                elif hasattr(ws_wrapper, 'send_text'): 
                     await ws_wrapper.send_text(message)
                else:
                     await ws_wrapper.send(message)
            except Exception as e:
                logging.error(f"Error sending to {user_id}: {e}")

    async def broadcast(self, message, exclude_user=None):
        """Sends a message to all connected users."""
        if isinstance(message, dict):
            message = json.dumps(message)

        for user_id, sockets in self.active_connections.items():
            if user_id == exclude_user:
                continue
            
            for ws in sockets:
                try:
                    if hasattr(ws, 'send'): await ws.send(message)
                    else: await ws.send(message)
                except:
                    pass

    # ==========================================
    # INTERNAL LOGIC
    # ==========================================

    async def _broadcast_presence(self, user_id, status):
        """Notifies all users when someone comes online or goes offline."""
        payload = json.dumps({
            "type": "presence", 
            "data": {"user_id": user_id, "status": status}
        })
        
        # Broadcast to ALL connected sockets
        for sockets in self.active_connections.values():
            for ws in sockets:
                try:
                    if hasattr(ws, 'send'): await ws.send(payload)
                    else: await ws.send(payload)
                except:
                    pass

# Singleton Instance
manager = ClientManager()