from chat_server.utils.time_utils import get_current_timestamp

def make_response(status, type_event, data=None, message=None):
    """
    Standardizes JSON responses.
    
    Args:
        status (str): "success" or "error"
        type_event (str): The event type (e.g., "login", "message")
        data (dict, optional): The data payload.
        message (str, optional): Error message or status description.

    Returns:
        dict: The standardized response payload.
    """
    payload = {
        "status": status,
        "type": type_event,
        "timestamp": get_current_timestamp()
    }
    
    if data is not None:
        payload["data"] = data
        
    if message is not None:
        payload["message"] = message
        
    return payload  # Returns a dict; the handler/dispatcher will json.dumps() it.

def success(type_event, data=None):
    """Helper for success responses."""
    return make_response("success", type_event, data=data)

def error(type_event, message):
    """Helper for error responses."""
    return make_response("error", type_event, message=message)