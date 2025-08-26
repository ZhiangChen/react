#!/usr/bin/env python3
"""
One-way telemetry command sender

This script repeatedly sends flight mode commands via master SiK radio.
Monitor the results in Mission Planner which is connected to Pixhawk via USB.

Configuration is set via variables below - no command line arguments needed.
"""

from pymavlink import mavutil
import time

# Configuration variables
MASTER_PORT = "COM17"          # Master SiK radio COM port
TARGET_SYSTEM_ID = 1           # Target system ID (sysid_thismav)
COMMAND_INTERVAL = 2           # Seconds between commands
SOURCE_SYSTEM = 240            # Our system ID
SOURCE_COMPONENT = 190         # Our component ID

# ArduCopter flight mode numbers
FLIGHT_MODES = {
    "STABILIZE": 0,
    "ACRO": 1,
    "ALT_HOLD": 2,
    "AUTO": 3,
    "GUIDED": 4,
    "LOITER": 5,
    "RTL": 6,
    "CIRCLE": 7,
    "LAND": 9,
    "POSHOLD": 16,
    "BRAKE": 17
}

def send_commands_repeatedly():
    """Send flight mode commands repeatedly via master SiK radio."""
    
    print(f"[i] Connecting to master SiK radio: {MASTER_PORT}")
    try:
        # Use explicit device format for Windows COM port
        master = mavutil.mavlink_connection(
            device=MASTER_PORT, 
            baud=57600,
            source_system=SOURCE_SYSTEM,
            source_component=SOURCE_COMPONENT
        )
        print(f"[✓] Connected to master SiK radio")
    except Exception as e:
        print(f"[!] Failed to connect: {e}")
        return
    
    print(f"[i] Starting command transmission (target system: {TARGET_SYSTEM_ID})")
    print(f"[i] Monitor flight mode changes in Mission Planner")
    print(f"[i] Press Ctrl+C to stop")
    print("-" * 50)
    
    # Alternate between these two modes only
    test_modes = ["STABILIZE", "LOITER"]
    mode_index = 0
    command_count = 0
    
    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1
    
    try:
        while True:
            current_mode = test_modes[mode_index]
            mode_number = FLIGHT_MODES[current_mode]
            
            command_count += 1
            timestamp = time.strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Command #{command_count}: Sending {current_mode} (mode {mode_number})")
            
            # Send flight mode command multiple times for reliability
            for i in range(3):  # Send 20 times
                master.mav.command_long_send(
                    TARGET_SYSTEM_ID,                    # target_system
                    1,                                   # target_component (autopilot)
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE, # command
                    0,                                   # confirmation
                    1,                                   # param1: mode (1=custom mode)
                    mode_number,                         # param2: custom mode number
                    0, 0, 0, 0, 0                       # param3-7: unused
                )
                time.sleep(0.025)  # Delay for SiK radio timing

                master.mav.command_long_send(
                    TARGET_SYSTEM_ID,
                    1,
                    mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
                    0,
                    1,
                    0,
                    0, 0, 0, 0, 0
                )


            print(f"           Command transmitted via SiK radio")
            print(f"           Check Mission Planner for mode change...")

            # Move to next mode in cycle
            mode_index = (mode_index + 1) % len(test_modes)
            
            # Wait before next command
            print(f"           Waiting {COMMAND_INTERVAL} seconds before next command...")
            time.sleep(COMMAND_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n[i] Transmission stopped after {command_count} commands")
    except Exception as e:
        print(f"\n[!] Error during transmission: {e}")
    finally:
        master.close()
        print("[i] Connection closed")

if __name__ == "__main__":
    print("=" * 60)
    print("ONE-WAY TELEMETRY COMMAND SENDER")
    print("=" * 60)
    print(f"Master SiK Radio: {MASTER_PORT}")
    print(f"Target System ID: {TARGET_SYSTEM_ID}")
    print(f"Command Interval: {COMMAND_INTERVAL} seconds")
    print("=" * 60)
    
    send_commands_repeatedly()
