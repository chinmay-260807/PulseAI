import requests
import json
import threading
import time
import sseclient

BASE_URL    = "http://localhost:3000"
MACHINE_IDS = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]

latest_readings = {}
stream_status   = {m: "connecting" for m in MACHINE_IDS}
reading_callbacks = []   # functions called on every new reading

def register_callback(fn):
    reading_callbacks.append(fn)

def connect_to_machine(machine_id):
    url     = f"{BASE_URL}/stream/{machine_id}"
    backoff = 2
    while True:
        try:
            stream_status[machine_id] = "connecting"
            response = requests.get(url, stream=True, timeout=15)
            client   = sseclient.SSEClient(response)
            stream_status[machine_id] = "live"
            backoff = 2
            for event in client.events():
                reading = json.loads(event.data)
                latest_readings[machine_id] = reading
                # fire all registered callbacks immediately
                for cb in reading_callbacks:
                    cb(machine_id, reading)
        except Exception as e:
            stream_status[machine_id] = "reconnecting"
            print(f"[STREAM] {machine_id} lost: {e}. Retry in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

def start_all_streams():
    for machine_id in MACHINE_IDS:
        t = threading.Thread(
            target=connect_to_machine,
            args=(machine_id,),
            daemon=True
        )
        t.start()
    print("[STREAM] All 4 streams started.")