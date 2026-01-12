import json
import logging

class ConnectionWrapper:
    """
    Wraps a raw websocket object to provide helper methods
    for sending formatted JSON responses.
    """
    def __init__(self, websocket):
        self.ws = websocket

    async def send_json(self, msg_type, data, status="success"):
        """
        Sends a standardized JSON message.
        
        Args:
            msg_type (str): The type of event (e.g., 'login', 'message')
            data (dict/list): The payload to send.
            status (str): 'success' or 'error' (default: 'success')
        """
        payload = {
            "type": msg_type,
            "status": status,
            "data": data
        }
        try:
            await self.ws.send(json.dumps(payload))
        except Exception as e:
            logging.error(f"Failed to send JSON: {e}")

    async def send_error(self, msg_type, message):
        """
        Helper to send an error message easily.
        """
        payload = {
            "type": msg_type,
            "status": "error",
            "message": message,
            "data": {}
        }
        try:
            await self.ws.send(json.dumps(payload))
        except Exception as e:
            logging.error(f"Failed to send Error: {e}")

    async def send(self, message):
        """
        Raw send method (for simple strings or pre-formatted JSON).
        """
        try:
            await self.ws.send(message)
        except Exception as e:
            logging.error(f"Failed to send raw message: {e}")

    async def recv(self):
        """Delegates recv to the underlying socket."""
        return await self.ws.recv()

    def __getattr__(self, name):
        """Delegate all other method calls (close, ping, etc.) to the underlying socket."""
        return getattr(self.ws, name)