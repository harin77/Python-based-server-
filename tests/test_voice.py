import asyncio
import websockets
import json
import uuid

URI = "ws://localhost:8765"

async def wait_for_response(websocket, expected_type):
    """
    Helper: Keeps receiving messages until one matches the expected_type.
    Ignores background noise like 'presence' or 'notification'.
    """
    while True:
        raw_msg = await websocket.recv()
        data = json.loads(raw_msg)
        
        # Debug print to see what we are skipping
        if data.get("type") != expected_type:
            print(f"   (Skipping background message: {data.get('type')})")
            continue
            
        return data

async def run_voice_test():
    print("🎤 Starting Voice Channel Test (Robust Mode)...")

    # --- Step 1: Setup Two Users ---
    ws1 = await websockets.connect(URI)
    ws2 = await websockets.connect(URI)

    try:
        # User A Registration
        print("\n🔹 Registering User A...")
        await ws1.send(json.dumps({
            "type": "register",
            "data": {"username": "Alice", "password": "pw"}
        }))
        
        # FIXED: Wait specifically for 'register' response
        reg_response_a = await wait_for_response(ws1, "register")
        user_a = reg_response_a["data"]
        print(f"✅ User A Registered: {user_a['handle']}")

        # Login A
        await ws1.send(json.dumps({
            "type": "login", 
            "data": {"handle": user_a["handle"], "password": "pw"}
        }))
        await wait_for_response(ws1, "login")

        # User B Registration
        print("🔹 Registering User B...")
        await ws2.send(json.dumps({
            "type": "register",
            "data": {"username": "Bob", "password": "pw"}
        }))
        
        # FIXED: Wait specifically for 'register' response
        reg_response_b = await wait_for_response(ws2, "register")
        user_b = reg_response_b["data"]
        print(f"✅ User B Registered: {user_b['handle']}")

        # Login B
        await ws2.send(json.dumps({
            "type": "login", 
            "data": {"handle": user_b["handle"], "password": "pw"}
        }))
        await wait_for_response(ws2, "login")

        # --- Step 2: Create a Group ---
        print("\n🔹 User A Creating Group...")
        await ws1.send(json.dumps({
            "type": "create_group",
            "data": {"name": "Voice Lounge"}
        }))
        
        group_response = await wait_for_response(ws1, "create_group")
        group_id = group_response["data"]["id"]
        join_code = group_response["data"]["join_code"]
        print(f"   Group Created: {group_id} (Code: {join_code})")

        # User B Joins Group
        print("🔹 User B Joining Group...")
        await ws2.send(json.dumps({
            "type": "join_group",
            "data": {"join_code": join_code}
        }))
        
        await wait_for_response(ws2, "join_group") # Wait for B's success
        await wait_for_response(ws1, "group_member_joined") # A gets notified

        # --- Step 3: Voice Logic ---
        
        # 1. User A Joins Voice Channel
        print("\n🎧 User A Joining Voice Channel...")
        await ws1.send(json.dumps({
            "type": "join_voice",
            "data": {"group_id": group_id}
        }))
        resp = await wait_for_response(ws1, "voice_joined")
        print(f"   A Received: {resp['type']} (Participants: {len(resp['data']['participants'])})")

        # 2. User B Joins Voice Channel
        print("🎧 User B Joining Voice Channel...")
        await ws2.send(json.dumps({
            "type": "join_voice",
            "data": {"group_id": group_id}
        }))
        
        # B gets success response
        resp_b = await wait_for_response(ws2, "voice_joined")
        print(f"   B Received: {resp_b['type']} (Participants: {len(resp_b['data']['participants'])})")

        # A gets notification that B joined
        notify_a = await wait_for_response(ws1, "voice_user_joined")
        print(f"   A Notified: {notify_a['type']} -> {notify_a['data']['user']['id']} joined")

        # 3. Mute/Unmute State Update
        print("\nChange State: User B Unmutes...")
        await ws2.send(json.dumps({
            "type": "voice_state_update",
            "data": {"group_id": group_id, "is_muted": False, "is_speaking": True}
        }))
        
        # A should receive the update
        state_update = await wait_for_response(ws1, "voice_state_updated")
        print(f"   A Saw Update: User {state_update['data']['user_id']} muted={state_update['data']['state']['is_muted']}")

        # 4. WebRTC Signaling (Offer/Answer simulation)
        print("\n📡 Signaling: User A sends 'Offer' to User B...")
        await ws1.send(json.dumps({
            "type": "voice_signal",
            "data": {
                "target_id": user_b["id"],
                "signal_type": "offer",
                "payload": {"sdp": "mock-sdp-data"}
            }
        }))

        # B should receive the signal
        signal = await wait_for_response(ws2, "voice_signal")
        print(f"   B Received Signal: {signal['data']['signal_type']} from {signal['data']['from']}")

        # 5. Leave Voice
        print("\n🚪 User A Leaving Voice...")
        await ws1.send(json.dumps({
            "type": "leave_voice",
            "data": {"group_id": group_id}
        }))
        
        # B gets notification
        leave_notify = await wait_for_response(ws2, "voice_user_left")
        print(f"   B Notified: User {leave_notify['data']['user_id']} left voice")

        print("\n✅ Voice Test Complete!")

    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ws1.close()
        await ws2.close()

if __name__ == "__main__":
    asyncio.run(run_voice_test())