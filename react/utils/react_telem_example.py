#!/usr/bin/env python3
from pymavlink import mavutil
import time

HOST = "127.0.0.1"
PORT = 14551  # one of MAVProxy's --out ports

# Hard fallback for ArduCopter mode numbers (used only when we actively set a mode)
ARDUCOPTER_MODES = {
    0:"STABILIZE", 1:"ACRO", 2:"ALT_HOLD", 3:"AUTO", 4:"GUIDED", 5:"LOITER",
    6:"RTL", 7:"CIRCLE", 9:"LAND", 11:"DRIFT", 13:"SPORT", 14:"FLIP",
    15:"AUTOTUNE", 16:"POSHOLD", 17:"BRAKE", 18:"THROW", 19:"AVOID_ADSB",
    20:"GUIDED_NOGPS", 21:"SMART_RTL"
}

def num(v, scale=1.0, nd=2):
    if v is None: return "—"
    try:
        return f"{(v/scale):.{nd}f}"
    except Exception:
        return "—"

def main():
    print(f"[i] Connecting to MAVProxy udp:{HOST}:{PORT}")
    m = mavutil.mavlink_connection(f"udp:{HOST}:{PORT}",
                                   source_system=240, source_component=190)

    hb = m.wait_heartbeat(timeout=10)
    if not hb:
        raise SystemExit("[!] No heartbeat from vehicle.")
    print(f"[✓] Heartbeat: sys={m.target_system}, comp={m.target_component}")

    # Try to set mode to STABILIZE (ArduCopter)
    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
    print("[i] Requesting STABILIZE mode…")
    m.mav.set_mode_send(m.target_system, MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 0)  # 0 = STABILIZE

    last = {
        "mode": "—",
        "lat": None, "lon": None, "alt_mm": None, "rel_mm": None,
        "roll": None, "pitch": None, "yaw": None,
        "bat_mV": None, "bat_cA": None, "bat_rem": None,
        "sats": None, "fix": None
    }

    print("[i] Receiving telemetry (Ctrl+C to stop)…")
    try:
        while True:
            msg = m.recv_match(blocking=True, timeout=2)
            if not msg:
                continue

            t = msg.get_type()

            if t == "HEARTBEAT":
                # Safely decode mode from the heartbeat
                last["mode"] = mavutil.mode_string_v10(msg)

            elif t == "GLOBAL_POSITION_INT":
                last["lat"] = msg.lat
                last["lon"] = msg.lon
                last["alt_mm"] = msg.alt
                last["rel_mm"] = getattr(msg, "relative_alt", None)

            elif t == "ATTITUDE":
                last["roll"] = msg.roll
                last["pitch"] = msg.pitch
                last["yaw"] = msg.yaw

            elif t == "SYS_STATUS":
                last["bat_mV"] = msg.voltage_battery
                last["bat_cA"] = msg.current_battery
                last["bat_rem"] = msg.battery_remaining

            elif t == "GPS_RAW_INT":
                last["sats"] = msg.satellites_visible
                last["fix"] = msg.fix_type

            # Print a compact line whenever we get a GLOBAL_POSITION_INT or HEARTBEAT
            if t in ("GLOBAL_POSITION_INT", "HEARTBEAT"):
                lat = num(last["lat"], 1e7, 7)
                lon = num(last["lon"], 1e7, 7)
                alt = num(last["alt_mm"], 1000.0, 1)
                rel = num(last["rel_mm"], 1000.0, 1)
                bat_v = num(last["bat_mV"], 1000.0, 2)
                bat_i = num(last["bat_cA"], 100.0, 2)
                sats = last["sats"] if last["sats"] is not None else "—"
                fix  = last["fix"] if last["fix"] is not None else "—"
                print(f"[{last['mode']}] lat {lat}, lon {lon}, altMSL {alt} m (rel {rel} m) | "
                      f"GPS fix {fix} sats {sats} | Batt {bat_v} V {bat_i} A rem {last['bat_rem'] if last['bat_rem'] is not None else '—'}%")

    except KeyboardInterrupt:
        print("\n[✓] Stopped.")

if __name__ == "__main__":
    main()
