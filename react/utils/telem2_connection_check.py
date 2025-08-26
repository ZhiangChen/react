from pymavlink import mavutil
import time

# -----------------------------
# Configuration variables
# -----------------------------
PORT   = "COM17"         # Telem2 master SiK radio port
BAUD   = 57600          # must match SiK radio and Pixhawk SERIAL2_BAUD
SYSID  = 255            # our GCS system ID
COMPID = 190            # our component ID
TARGET_SYSID = 1        # Target Pixhawk system ID (since we can't discover it)
TARGET_COMPID = 1       # Target autopilot component ID
RATE_HZ = 1.0           # how many times per second to send heartbeat
# -----------------------------

def main():
    print(f"[INFO] Connecting to one-way telem2 radio: {PORT}")
    master = mavutil.mavlink_connection(
        PORT, 
        baud=BAUD, 
        source_system=SYSID, 
        source_component=COMPID
    )
    
    # No wait_heartbeat() - this is one-way communication
    print(f"[INFO] Connected to telem2 radio (one-way transmission)")
    print(f"[INFO] Sending to target sysid={TARGET_SYSID}, compid={TARGET_COMPID}")
    print(f"[INFO] No response expected - one-way communication only")

    period = 1.0 / max(RATE_HZ, 0.1)
    val = 0
    while True:
        val += 1
        
        # Send parameter set to fixed target (no response expected)
        master.mav.param_set_send(
            TARGET_SYSID,          # Fixed target system ID
            TARGET_COMPID,         # Fixed target component ID
            b"SCR_USER1",          # Lua script watches this param
            float(val),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        print(f"[INFO] Sent param SCR_USER1={val} via one-way telem2")
        time.sleep(period)

if __name__ == "__main__":
    main()
