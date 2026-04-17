import requests
import numpy as np

BASE_URL = "http://localhost:3000"
MACHINE_IDS = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]
SENSORS = ["temperature_C", "vibration_mm_s", "rpm", "current_A"]

def fetch_baselines():
    baselines = {}
    for machine_id in MACHINE_IDS:
        print(f"Fetching history for {machine_id}...")
        r = requests.get(f"{BASE_URL}/history/{machine_id}", timeout=30)
        history = r.json()

        baselines[machine_id] = {}
        for sensor in SENSORS:
            values = [
                float(reading[sensor])
                for reading in history
                if sensor in reading and reading[sensor] is not None
            ]
            if not values:
                continue
            arr = np.array(values)
            baselines[machine_id][sensor] = {
                "mean": float(arr.mean()),
                "std":  float(max(arr.std(), 0.01)),
                "p95":  float(np.percentile(arr, 95)),
                "p05":  float(np.percentile(arr, 5)),
            }

        print(f"  {machine_id} baselines ready.")
    return baselines

def adapt_baseline(baselines, machine_id, sensor, resolved_value, alpha=0.03):
    """Self-learning: slowly nudge baseline toward observed reality."""
    b = baselines[machine_id][sensor]
    b["mean"] = (1 - alpha) * b["mean"] + alpha * resolved_value
    return baselines