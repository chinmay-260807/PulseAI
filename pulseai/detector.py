import time
from collections import defaultdict, deque

SENSORS = ["temperature_C", "vibration_mm_s", "rpm", "current_A"]

# Rolling history per machine (last 20 readings)
reading_history   = defaultdict(lambda: deque(maxlen=20))
# Consecutive anomaly count per machine (transient suppression)
consecutive_count = defaultdict(int)
CONSECUTIVE_THRESHOLD = 3

# Cross-machine: recent alert log
recent_sensor_alerts = defaultdict(list)  # machine_id -> [{sensor, time}]

COMPOUND_PATTERNS = [
    ({"vibration_mm_s", "current_A"},            "Bearing failure signature",      0.15),
    ({"temperature_C", "current_A"},             "Motor overload signature",        0.15),
    ({"vibration_mm_s", "rpm"},                  "Mechanical resonance signature",  0.12),
    ({"temperature_C", "vibration_mm_s", "current_A"}, "Imminent failure signature", 0.25),
    ({"rpm", "current_A"},                       "Developing clog signature",       0.12),
]

def sigma(value, stats):
    return abs(value - stats["mean"]) / stats["std"]

def detect_drift(machine_id, sensor):
    history = reading_history[machine_id]
    if len(history) < 8:
        return False, 0.0, ""
    values = [r.get(sensor, 0) for r in list(history)[-10:]]
    diffs  = [values[i+1] - values[i] for i in range(len(values)-1)]
    avg    = sum(diffs) / len(diffs)
    all_same_dir = all(d > 0 for d in diffs) or all(d < 0 for d in diffs)
    if all_same_dir and abs(avg) > 0.2:
        return True, round(avg, 3), ("rising" if avg > 0 else "falling")
    return False, 0.0, ""

def estimate_ttf(machine_id, sensor, current_value, stats):
    _, rate, direction = detect_drift(machine_id, sensor)
    if not rate or direction != "rising":
        return None
    threshold = stats["mean"] + 4 * stats["std"]
    gap = threshold - current_value
    if gap <= 0:
        return 0
    readings_to_breach = gap / abs(rate)
    return round(readings_to_breach / 60, 1)  # convert to minutes

def detect_compound(triggered_sensors):
    names = {t["sensor"] for t in triggered_sensors}
    for pattern_set, label, boost in COMPOUND_PATTERNS:
        if pattern_set <= names:
            return label, boost
    return None, 0.0

def check_cross_machine(machine_id, sensor):
    now = time.time()
    correlated = []
    for mid, alerts in recent_sensor_alerts.items():
        if mid == machine_id:
            continue
        if any(a["sensor"] == sensor and now - a["t"] < 90 for a in alerts):
            correlated.append(mid)
    return correlated

def compute_health_score(readings, baselines, machine_id):
    """0–100 health score. 100 = perfect, 0 = critical."""
    if machine_id not in baselines:
        return 100
    sigmas = []
    for sensor in SENSORS:
        r = readings.get(machine_id, {})
        b = baselines[machine_id].get(sensor)
        if not b or sensor not in r:
            continue
        sigmas.append(sigma(r[sensor], b))
    if not sigmas:
        return 100
    avg_sigma = sum(sigmas) / len(sigmas)
    return max(0, min(100, int(100 - avg_sigma * 20)))

def analyze(machine_id, reading, baselines):
    reading_history[machine_id].append(reading)
    baseline = baselines.get(machine_id, {})

    triggered   = []
    drift_flags = []
    max_sig     = 0

    for sensor in SENSORS:
        if sensor not in reading or sensor not in baseline:
            continue
        val   = reading[sensor]
        stats = baseline[sensor]
        sig   = sigma(val, stats)

        if sig > 2.0:
            triggered.append({
                "sensor": sensor,
                "value":  round(val, 2),
                "mean":   round(stats["mean"], 2),
                "sigma":  round(sig, 2),
            })
            max_sig = max(max_sig, sig)
            recent_sensor_alerts[machine_id].append({"sensor": sensor, "t": time.time()})

        is_drifting, rate, direction = detect_drift(machine_id, sensor)
        if is_drifting:
            ttf = estimate_ttf(machine_id, sensor, val, stats)
            drift_flags.append({
                "sensor":    sensor,
                "rate":      rate,
                "direction": direction,
                "ttf_min":   ttf,
                "value":     round(val, 2),
            })

    # Transient suppression
    if triggered:
        consecutive_count[machine_id] += 1
    else:
        consecutive_count[machine_id] = 0

    suppressed = consecutive_count[machine_id] < CONSECUTIVE_THRESHOLD
    effective_triggered = [] if suppressed else triggered

    compound_name, compound_boost = detect_compound(effective_triggered)
    base_score  = min(95, int((max_sig / 5.0) * 100))
    risk_score  = min(100, int(base_score * (1 + compound_boost)))
    confidence  = min(99, 55 + risk_score // 3 + (10 if compound_name else 0))

    correlated = []
    for t in effective_triggered:
        correlated.extend(check_cross_machine(machine_id, t["sensor"]))
    correlated = list(set(correlated))

    severity = classify_severity(risk_score if effective_triggered else 0)

    return {
        "risk_score":   risk_score if effective_triggered else 0,
        "triggered":    effective_triggered,
        "drift_flags":  drift_flags,
        "compound":     compound_name,
        "confidence":   confidence,
        "correlated":   correlated,
        "severity":     severity,
        "suppressed":   suppressed,
    }

def classify_severity(score):
    if score >= 80: return "CRITICAL"
    if score >= 60: return "HIGH"
    if score >= 40: return "MEDIUM"
    return "LOW"