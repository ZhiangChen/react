"""
Detailed test script for mission upload to diagnose and fix upload issues
"""

import sys
import time
from pathlib import Path
from pymavlink import mavutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def parse_qgc_waypoint_file(filepath):
    """Parse QGroundControl waypoint file"""
    waypoints = []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Check header
        if not lines or not lines[0].strip().startswith('QGC WPL'):
            print(f"ERROR: Invalid waypoint file format. Expected 'QGC WPL' header.")
            return None
        
        print(f"✓ Header: {lines[0].strip()}")
        print(f"✓ Total lines: {len(lines)}")
        
        # Parse waypoints (skip header)
        for i, line in enumerate(lines[1:], start=1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) < 12:
                print(f"WARNING: Line {i} has only {len(parts)} parts, expected 12")
                continue
            
            try:
                waypoint = {
                    'seq': int(parts[0]),
                    'current': int(parts[1]),
                    'frame': int(parts[2]),
                    'command': int(parts[3]),
                    'param1': float(parts[4]),
                    'param2': float(parts[5]),
                    'param3': float(parts[6]),
                    'param4': float(parts[7]),
                    'x': float(parts[8]),  # lat
                    'y': float(parts[9]),  # lon
                    'z': float(parts[10]), # alt
                    'autocontinue': int(parts[11])
                }
                waypoints.append(waypoint)
                
            except (ValueError, IndexError) as e:
                print(f"ERROR parsing line {i}: {e}")
                continue
        
        print(f"✓ Successfully parsed {len(waypoints)} waypoints\n")
        return waypoints
        
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return None

def test_mission_upload():
    """Test mission upload with detailed diagnostics"""
    
    print("="*70)
    print("DETAILED MISSION UPLOAD TEST")
    print("="*70)
    
    # Configuration
    waypoint_file = r"C:\Users\chenz\OneDrive\Documents\QGroundControl\Logs\test.waypoints"
    connection_string = "udp:127.0.0.1:14552"
    target_system = 1
    target_component = 1
    
    print(f"\n1. CONFIGURATION")
    print(f"   Waypoint file: {waypoint_file}")
    print(f"   Connection: {connection_string}")
    print(f"   Target: System {target_system}, Component {target_component}")
    
    # Parse waypoint file
    print(f"\n2. PARSING WAYPOINT FILE")
    waypoints = parse_qgc_waypoint_file(waypoint_file)
    
    if not waypoints:
        print("✗ FAILED: Could not parse waypoint file")
        return False
    
    # Print first few waypoints
    print("\n   First 3 waypoints:")
    for i, wp in enumerate(waypoints[:3]):
        cmd_name = {
            16: 'NAV_WAYPOINT',
            22: 'NAV_TAKEOFF',
            21: 'NAV_LAND',
            178: 'DO_CHANGE_SPEED',
            206: 'DO_SET_REVERSE',
        }.get(wp['command'], f"CMD_{wp['command']}")
        print(f"   [{wp['seq']}] {cmd_name}: ({wp['x']:.6f}, {wp['y']:.6f}, {wp['z']:.1f}m)")
    
    # Connect to vehicle
    print(f"\n3. CONNECTING TO VEHICLE")
    print(f"   Attempting connection to {connection_string}...")
    
    try:
        mav = mavutil.mavlink_connection(connection_string)
        print("   ✓ Connection object created")
        
        # Wait for heartbeat
        print("   Waiting for heartbeat...")
        heartbeat = mav.wait_heartbeat(timeout=10)
        if heartbeat:
            print(f"   ✓ Heartbeat received from system {heartbeat.get_srcSystem()}")
            target_system = heartbeat.get_srcSystem()
        else:
            print("   ✗ TIMEOUT: No heartbeat received")
            return False
            
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Send mission count
    print(f"\n4. SENDING MISSION COUNT")
    mission_count = len(waypoints)
    print(f"   Sending MISSION_COUNT: {mission_count} waypoints")
    
    mav.mav.mission_count_send(
        target_system,
        target_component,
        mission_count,
        mavutil.mavlink.MAV_MISSION_TYPE_MISSION
    )
    print("   ✓ MISSION_COUNT sent")
    
    # Wait for mission requests and send waypoints
    print(f"\n5. SENDING WAYPOINTS")
    waypoints_sent = 0
    timeout_time = time.time() + 30
    
    while waypoints_sent < mission_count and time.time() < timeout_time:
        msg = mav.recv_match(
            type=['MISSION_REQUEST', 'MISSION_REQUEST_INT', 'MISSION_ACK'],
            blocking=True,
            timeout=1.0
        )
        
        if msg is None:
            continue
        
        msg_type = msg.get_type()
        
        if msg_type in ['MISSION_REQUEST', 'MISSION_REQUEST_INT']:
            seq = msg.seq
            print(f"   Received request for waypoint {seq}")
            
            if seq >= len(waypoints):
                print(f"   ✗ ERROR: Requested waypoint {seq} out of range")
                continue
            
            wp = waypoints[seq]
            
            # Send waypoint - use MISSION_ITEM_INT for better precision
            if msg_type == 'MISSION_REQUEST_INT':
                mav.mav.mission_item_int_send(
                    target_system,
                    target_component,
                    seq,
                    wp['frame'],
                    wp['command'],
                    wp['current'],
                    wp['autocontinue'],
                    wp['param1'],
                    wp['param2'],
                    wp['param3'],
                    wp['param4'],
                    int(wp['x'] * 1e7),  # lat in 1e7 degrees
                    int(wp['y'] * 1e7),  # lon in 1e7 degrees
                    wp['z'],             # alt in meters
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
                )
                print(f"   ✓ Sent waypoint {seq} (INT format)")
            else:
                mav.mav.mission_item_send(
                    target_system,
                    target_component,
                    seq,
                    wp['frame'],
                    wp['command'],
                    wp['current'],
                    wp['autocontinue'],
                    wp['param1'],
                    wp['param2'],
                    wp['param3'],
                    wp['param4'],
                    wp['x'],  # lat
                    wp['y'],  # lon
                    wp['z'],  # alt
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
                )
                print(f"   ✓ Sent waypoint {seq} (FLOAT format)")
            
            waypoints_sent += 1
            
        elif msg_type == 'MISSION_ACK':
            ack_type = msg.type
            print(f"\n6. MISSION ACK RECEIVED")
            print(f"   ACK Type: {ack_type}")
            
            if ack_type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                print("   ✓ SUCCESS: Mission accepted by vehicle!")
                print(f"   ✓ Total waypoints uploaded: {waypoints_sent}")
                return True
            else:
                error_msgs = {
                    1: "Generic error",
                    2: "Unsupported coordinate frame",
                    3: "Unsupported mission command",
                    4: "No space left on device",
                    5: "Invalid mission",
                    6: "Invalid param1",
                    7: "Invalid param2",
                    8: "Invalid param3",
                    9: "Invalid param4",
                    10: "Invalid param5/X coordinate",
                    11: "Invalid param6/Y coordinate",
                    12: "Invalid param7/altitude",
                    13: "Invalid sequence",
                    14: "Mission denied",
                    15: "Not in a mission",
                    16: "No missions available",
                    17: "Mission out of bounds",
                    18: "Temporary failure",
                }
                error_msg = error_msgs.get(ack_type, f"Unknown error code {ack_type}")
                print(f"   ✗ FAILED: {error_msg}")
                return False
    
    print(f"\n   ✗ TIMEOUT: Sent {waypoints_sent}/{mission_count} waypoints")
    return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("MISSION UPLOAD DIAGNOSTIC TEST")
    print("="*70 + "\n")
    
    success = test_mission_upload()
    
    print("\n" + "="*70)
    if success:
        print("RESULT: ✓ MISSION UPLOAD SUCCESSFUL")
    else:
        print("RESULT: ✗ MISSION UPLOAD FAILED")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)
