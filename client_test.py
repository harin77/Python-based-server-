import asyncio
import websockets
import json

SERVER_URL = "ws://192.168.0.190:8765"

async def send(ws, type_event, data):
    message = json.dumps({"type": type_event, "data": data})
    await ws.send(message)
    print(f"📤 SENT: {type_event}")

async def wait_for(ws, expected_type):
    while True:
        try:
            response = await ws.recv()
            data = json.loads(response)
            print(f"📥 RECV: {json.dumps(data, indent=2)}")
            
            # Return data if it matches what we are looking for
            if data.get("type") == expected_type:
                return data
        except Exception as e:
            print(f"Error: {e}")
            break

async def run_test():
    print(f"Connecting to {SERVER_URL}...")
    try:
        async with websockets.connect(SERVER_URL) as ws:
            print("✅ Connected!")

            # 1. Register
            print("\n--- 1. REGISTERING USER ---")
            await send(ws, "register", {"username": "Alice", "password": "password123"})
            response = await wait_for(ws, "register")
            
            if not response or response.get("status") != "success":
                print("❌ Registration failed")
                return
                
            user = response["data"]
            user_handle = user["handle"]
            user_id = user["id"]
            print(f"👤 Registered as: {user_handle} (ID: {user_id})")

            # 2. Login (Not strictly needed since register auto-logs in, but good to test)
            print("\n--- 2. LOGGING IN ---")
            await send(ws, "login", {"handle": user_handle, "password": "password123"})
            await wait_for(ws, "login")

            # 3. Create Group
            print("\n--- 3. CREATING GROUP ---")
            await send(ws, "create_group", {"name": "Developers Hangout"})
            group_res = await wait_for(ws, "create_group")
            group_id = group_res["data"]["id"]
            print(f"🏠 Group Created: {group_res['data']['name']} (ID: {group_id})")

            # 4. Send Message
            print("\n--- 4. SENDING MESSAGE ---")
            await send(ws, "message", {
                "to": group_id,
                "content": "Hello World! This is a test message.",
                "msg_type": "text"
            })
            
            # We expect a message back (broadcasted to us)
            await wait_for(ws, "message")
            print("\n✅ TEST COMPLETED SUCCESSFULLY")
            
    except ConnectionRefusedError:
        print("❌ Error: Could not connect to server. Is 'server.py' running?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        pass