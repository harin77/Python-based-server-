import asyncio
import websockets
import logging
import os
import traceback
from chat_server.config import HOST, PORT, BASE_DIR
from chat_server.core.client_manager import manager
from chat_server.core.dispatcher import Dispatcher
from chat_server.core.connection import ConnectionWrapper

# --- Logging Configuration ---
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# General Logger (Console + server.log)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "server.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Error Logger (errors.log only)
error_logger = logging.getLogger("error_logger")
error_handler = logging.FileHandler(os.path.join(LOG_DIR, "errors.log"), encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s\n%(exc_info)s"))
error_logger.addHandler(error_handler)

# --- Server Initialization ---
dispatcher = Dispatcher(manager)

async def connection_handler(websocket):
    """
    Handles the lifecycle of a WebSocket connection.
    """
    # Wrap socket for helper methods (send_json, etc.)
    ws_wrapper = ConnectionWrapper(websocket)
    current_user_id = None
    
    logging.info(f"New connection request from {websocket.remote_address}")

    try:
        async for message in websocket:
            # Lookup user ID associated with this specific wrapper instance
            # The AuthHandler registers this wrapper in the manager upon login.
            current_user_id = manager.ws_to_user.get(ws_wrapper)
            
            try:
                # Dispatch message to the appropriate handler
                await dispatcher.dispatch(ws_wrapper, message)
            except Exception as e:
                logging.error(f"Error processing message from {current_user_id or 'Anonymous'}: {e}")
                error_logger.error(f"Message processing failed: {e}", exc_info=True)
            
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"Connection closed: {current_user_id or websocket.remote_address}")
        
    except Exception as e:
        logging.critical(f"❌ CRITICAL SERVER ERROR: {e}")
        error_logger.critical(f"Critical error in connection handler: {e}", exc_info=True)
        
    finally:
        # Cleanup connection
        if ws_wrapper:
            await manager.remove_client(ws_wrapper)

async def main():
    logging.info("------------------------------------------------")
    logging.info(f"🚀 Chat Server starting on {HOST}:{PORT}")
    logging.info(f"📂 Database Path: {BASE_DIR}/database")
    logging.info("------------------------------------------------")
    
    # Start WebSocket Server
    # 'ping_interval' and 'ping_timeout' keep connections alive
    async with websockets.serve(connection_handler, HOST, PORT, ping_interval=20, ping_timeout=20):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\n🛑 Server stopped by user.")