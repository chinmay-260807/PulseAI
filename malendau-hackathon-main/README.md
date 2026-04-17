# 🏭 HACK MALENDAU 2026 — Sensor Simulation Server

A locally-hosted simulation server that streams live industrial sensor data from 4 machines. Built for the **Predictive Maintenance** hackathon challenge.

---

## ⚡ Quick Start (any OS)

### Prerequisites
You only need **Node.js** (v16 or newer).

| OS | Download |
|----|----------|
| Windows | https://nodejs.org → click "LTS" → run the `.msi` installer |
| macOS | https://nodejs.org → click "LTS" → run the `.pkg` installer |
| Linux (Debian/Ubuntu) | `sudo apt install nodejs npm` |
| Linux (Fedora/RHEL) | `sudo dnf install nodejs` |

Verify it works: open a terminal and type `node -v` — you should see `v16` or higher.

---

### 1 — Download / Clone this repo

**Option A – Git:**
```bash
git clone https://github.com/YOUR_ORG/malendau-hackathon-server.git
cd malendau-hackathon
```

**Option B – ZIP:**  
Download and unzip, then `cd` into the folder.

---

### 2 — Install dependencies

```bash
npm install
```

This installs `express` and `cors`. No internet access needed after this step.

---

### 3 — Start the server

```bash
npm start
```

You will see:
```
⚙️  Generating 7-day sensor history…
✅  History ready: 4 machines × 10080 readings each.

╔══════════════════════════════════════════════════════════╗
║  🏭  HACK MALENDAU 2026 — Sensor Simulation Server       ║
╠══════════════════════════════════════════════════════════╣
║  Dashboard   →  http://localhost:3000                    ║
║  Stream      →  GET  /stream/{machine_id}                ║
║  History     →  GET  /history/{machine_id}               ║
║  Alert       →  POST /alert                              ║
║  Maintenance →  POST /schedule-maintenance               ║
╚══════════════════════════════════════════════════════════╝
```

Open **http://localhost:3000** in your browser to see the live dashboard.

---

## 📡 API Reference

### Machines
| machine_id | Type | Failure Pattern |
|------------|------|-----------------|
| `CNC_01` | CNC Mill | Bearing wear — vibration + temp gradually rise |
| `CNC_02` | CNC Lathe | Thermal runaway — afternoon temperature spikes |
| `PUMP_03` | Pump | Cavitation + slow RPM drop (developing clog) |
| `CONVEYOR_04` | Conveyor | Mostly healthy — use as baseline |

---

### GET `/stream/{machine_id}`
Server-Sent Events stream — **1 reading per second**.

```bash
curl http://localhost:3000/stream/CNC_01
```

**Response (each event):**
```json
{
  "machine_id":      "CNC_01",
  "timestamp":       "2026-04-06T09:00:01Z",
  "temperature_C":   84.7,
  "vibration_mm_s":  1.92,
  "rpm":             1475,
  "current_A":       13.4,
  "status":          "running"
}
```

**Consuming SSE in Python:**
```python
import sseclient, requests

url = "http://localhost:3000/stream/CNC_01"
response = requests.get(url, stream=True)
client = sseclient.SSEClient(response)
for event in client.events():
    print(event.data)
```

**Consuming SSE in JavaScript:**
```javascript
const es = new EventSource("http://localhost:3000/stream/CNC_01");
es.onmessage = (e) => {
  const reading = JSON.parse(e.data);
  console.log(reading);
};
```

---

### GET `/history/{machine_id}`
Returns ~10 080 readings (1 per minute × 7 days) as JSON.

```bash
curl http://localhost:3000/history/CNC_01
```

---

### POST `/alert`
Your agent calls this when it detects a machine at risk.

```bash
curl -X POST http://localhost:3000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "CNC_01",
    "reason": "Vibration has increased 180% over baseline across the last 10 minutes, suggesting bearing wear.",
    "reading": { "vibration_mm_s": 5.1, "temperature_C": 96.3 }
  }'
```

**Body fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `machine_id` | ✅ | One of the 4 machine IDs |
| `reason` | ✅ | Human-readable explanation of the anomaly |
| `reading` | optional | The sensor reading that triggered the alert |

---

### POST `/schedule-maintenance` *(Bonus)*
Books a maintenance slot (auto-assigned to next business morning if you don't specify one).

```bash
curl -X POST http://localhost:3000/schedule-maintenance \
  -H "Content-Type: application/json" \
  -d '{ "machine_id": "CNC_01", "proposed_slot": "2026-04-07T06:00:00Z" }'
```

---

### GET `/alerts`
Returns all alerts raised so far — useful for your agent's dashboard.

### GET `/machines`
Returns all machine IDs and their baseline specs.

---

## 🗺️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│              Simulation Server (this repo)           │
│                                                      │
│  generate-history.js  →  7-day historical dataset   │
│  server.js            →  Express API                 │
│     /stream/:id            SSE, 1 reading/sec        │
│     /history/:id           Full 7-day history JSON   │
│     /alert                 Receive agent alerts      │
│     /schedule-maintenance  Book maintenance slots    │
└──────────────────┬──────────────────────────────────┘
                   │  HTTP / SSE
         ┌─────────▼──────────┐
         │   Your AI Agent    │
         │  (what you build!) │
         │                    │
         │  1. Ingest stream  │
         │  2. Detect anomaly │
         │  3. POST /alert    │
         │  4. (Bonus) POST   │
         │     /schedule-…    │
         └────────────────────┘
```

---

## 🔧 Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `PORT` | `3000` | Port the server listens on |

Example: `PORT=8080 npm start`

---

## 📁 File Structure

```
malendau-hackathon-server/
├── server.js            ← Main API server
├── generate-history.js  ← 7-day historical data generator
├── package.json
├── public/
│   └── index.html       ← Live web dashboard
└── README.md
```

---

Good luck! 🚀
