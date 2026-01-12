from chat_server.utils.response import success

def check_health():
    """
    Returns server status with a standardized success response.
    Used for heartbeat checks by the client.
    """
    return success("health_check", {
        "service": "Chat WebSocket Server",
        "status": "operational",
        "maintenance": False,
        "version": "1.0.0"
    })