/**
 * generate-history.js
 * Generates 7 days of realistic sensor history for 4 machines.
 * Run once automatically on first server start.
 */

const MACHINES = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"];

const BASELINES = {
  CNC_01:      { temp: 72,  vib: 1.8, rpm: 1480, current: 12.5 },
  CNC_02:      { temp: 68,  vib: 1.5, rpm: 1490, current: 11.8 },
  PUMP_03:     { temp: 55,  vib: 2.2, rpm: 2950, current: 18.0 },
  CONVEYOR_04: { temp: 45,  vib: 0.9, rpm:  720, current:  8.5 },
};

const rand  = (min, max) => Math.random() * (max - min) + min;
const noise = (base, pct) => base + rand(-base * pct, base * pct);
const fix   = (n, d = 2)  => parseFloat(n.toFixed(d));

function generateReading(machineId, timestamp, dayOffset, progress) {
  const b = BASELINES[machineId];
  let temp    = noise(b.temp,    0.03);
  let vib     = noise(b.vib,     0.04);
  let rpm     = noise(b.rpm,     0.015);
  let current = noise(b.current, 0.03);
  let status  = "running";

  // CNC_01 – gradual bearing wear: vibration + temp climb over last 3 days
  if (machineId === "CNC_01") {
    const degradeDays = Math.max(0, 3 - dayOffset);
    const d = degradeDays / 3;
    vib     += d * 3.5;
    temp    += d * 12;
    current += d * 2.5;
    if (d > 0.6) status = "warning";
    if (d > 0.9 && progress > 0.8) status = "fault";
  }

  // CNC_02 – thermal runaway in afternoon shift; fault event on day 1
  if (machineId === "CNC_02") {
    const afternoon = progress > 0.5 && progress < 0.75;
    if (afternoon && dayOffset < 2) {
      temp    += rand(15, 30);
      current += rand(2,  5);
      if (temp > 95) status = "warning";
    }
    if (dayOffset === 1 && progress > 0.60 && progress < 0.65) {
      temp    = 112 + rand(0, 8);
      current =  22 + rand(0, 3);
      status  = "fault";
    }
  }

  // PUMP_03 – cavitation bursts + slow RPM drop (developing clog)
  if (machineId === "PUMP_03") {
    if (Math.random() < 0.08) {
      vib     += rand(2, 6);
      current += rand(1, 3);
      if (vib > 6) status = "warning";
    }
    const rpmDrop = ((7 - dayOffset) / 7) * 180;
    rpm -= rpmDrop;
    if (rpm < 2820) status = "warning";
  }

  // CONVEYOR_04 – mostly healthy; one brief warning 4 days ago
  if (machineId === "CONVEYOR_04") {
    if (dayOffset === 4 && progress > 0.4 && progress < 0.45) {
      vib    += rand(1, 2);
      status  = "warning";
    }
  }

  temp    = Math.max(20,   Math.min(130, temp));
  vib     = Math.max(0.1,  Math.min(12,  vib));
  rpm     = Math.max(100,  Math.min(4000, rpm));
  current = Math.max(1,    Math.min(30,  current));

  return {
    machine_id:      machineId,
    timestamp:       timestamp.toISOString(),
    temperature_C:   fix(temp),
    vibration_mm_s:  fix(vib),
    rpm:             fix(rpm, 0),
    current_A:       fix(current),
    status,
  };
}

/**
 * Returns an object keyed by machine_id, each containing an array of readings
 * sampled every 60 seconds for the past 7 days.
 */
function generateAllHistory() {
  const history = {};
  const now     = Date.now();
  const DAYS    = 7;
  const STEP_MS = 60 * 1000; // 1 reading per minute (7 days × 1440 = 10 080 rows each)
  const TOTAL_MS = DAYS * 24 * 60 * 60 * 1000;

  for (const machineId of MACHINES) {
    history[machineId] = [];
    for (let offset = TOTAL_MS; offset >= 0; offset -= STEP_MS) {
      const ts         = new Date(now - offset);
      const dayOffset  = Math.floor(offset / (24 * 60 * 60 * 1000)); // 0=today, 6=oldest
      const progress   = (ts.getHours() * 3600 + ts.getMinutes() * 60 + ts.getSeconds()) / 86400;
      history[machineId].push(generateReading(machineId, ts, dayOffset, progress));
    }
  }
  return history;
}

module.exports = { generateAllHistory, generateReading, MACHINES, BASELINES };
