#!/usr/bin/env python3
"""Test script for mission resume waypoint trimming logic."""

import os
import tempfile

def test_resume_mission():
    """Test the waypoint trimming and re-indexing logic."""
    
    # Create a sample mission file
    test_mission = """QGC WPL 110
0	1	0	16	0	0	0	0	47.397742	8.545594	488.000000	1
1	0	0	16	0.00000000	0.00000000	0.00000000	0.00000000	47.398297	8.545889	50.000000	1
2	0	0	16	0.00000000	0.00000000	0.00000000	0.00000000	47.398564	8.546156	50.000000	1
3	0	0	16	0.00000000	0.00000000	0.00000000	0.00000000	47.398831	8.546423	50.000000	1
4	0	0	16	0.00000000	0.00000000	0.00000000	0.00000000	47.399098	8.546690	50.000000	1
5	0	0	16	0.00000000	0.00000000	0.00000000	0.00000000	47.399365	8.546957	50.000000	1
"""
    
    # Write test mission to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.waypoints', delete=False) as f:
        f.write(test_mission)
        test_file = f.name
    
    print(f"Created test mission file: {test_file}")
    print("=" * 70)
    
    try:
        # Simulate resume mission logic
        last_completed = 3  # User completed waypoints 0, 1, 2, 3
        original_waypoint_indices = [0, 1, 2, 3, 4, 5]
        
        print(f"Original waypoint indices: {original_waypoint_indices}")
        print(f"Last completed waypoint: {last_completed}")
        print()
        
        # Read the mission file
        with open(test_file, 'r') as f:
            lines = f.readlines()
        
        header = lines[0].strip()
        
        # Build waypoint dict
        waypoint_dict = {}
        for line in lines[1:]:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) > 0:
                    wp_index = int(parts[0])
                    waypoint_dict[wp_index] = line
        
        print(f"Parsed waypoint dict keys: {sorted(waypoint_dict.keys())}")
        print()
        
        # Find position of last_completed
        last_completed_idx = original_waypoint_indices.index(last_completed)
        print(f"Last completed index in list: {last_completed_idx}")
        print()
        
        # CRITICAL: Always include HOME waypoint (0) + last_completed + remaining
        remaining_wp_indices = []
        
        # Always include waypoint 0 (HOME)
        if 0 in original_waypoint_indices:
            remaining_wp_indices.append(0)
            print(f"Including HOME waypoint (index 0) - required by ArduPilot")
        
        # Get remaining waypoints (INCLUDING last completed, but skip 0 if already added)
        for i in range(last_completed_idx, len(original_waypoint_indices)):
            wp_idx = original_waypoint_indices[i]
            if wp_idx != 0:  # Don't duplicate waypoint 0
                remaining_wp_indices.append(wp_idx)
        
        print(f"Remaining waypoint indices (with HOME): {remaining_wp_indices}")
        print(f"HOME waypoint: {remaining_wp_indices[0]} (should always be 0)")
        print(f"First mission waypoint: {remaining_wp_indices[1] if len(remaining_wp_indices) > 1 else 'none'} (should be {last_completed})")
        
        if remaining_wp_indices[0] != 0:
            print(f"❌ ERROR: First waypoint {remaining_wp_indices[0]} is not HOME (0)")
            return False
        if len(remaining_wp_indices) > 1 and remaining_wp_indices[1] != last_completed:
            print(f"❌ ERROR: First mission waypoint {remaining_wp_indices[1]} != last completed {last_completed}")
            return False
        else:
            print(f"✓ HOME waypoint included, first mission waypoint matches last completed")
        print()
        
        # Re-index waypoints
        print("Re-indexing waypoints:")
        remaining_waypoints = []
        for new_idx, wp_idx in enumerate(remaining_wp_indices):
            if wp_idx in waypoint_dict:
                wp_line = waypoint_dict[wp_idx]
                parts = wp_line.split('\t')
                if len(parts) > 0:
                    old_idx = parts[0]
                    parts[0] = str(new_idx)
                    remaining_waypoints.append('\t'.join(parts))
                    print(f"  Original WP {old_idx} -> new index {new_idx}")
        
        print()
        print(f"Created {len(remaining_waypoints)} re-indexed waypoints")
        print()
        
        # Create output file
        output_file = test_file.replace('.waypoints', '_resumed.waypoints')
        with open(output_file, 'w') as f:
            f.write(header + '\n')
            for wp_line in remaining_waypoints:
                f.write(wp_line + '\n')
        
        print(f"Created resumed mission file: {output_file}")
        print()
        
        # Show contents of both files
        print("=" * 70)
        print("ORIGINAL MISSION:")
        print("=" * 70)
        with open(test_file, 'r') as f:
            print(f.read())
        
        print("=" * 70)
        print("RESUMED MISSION:")
        print("=" * 70)
        with open(output_file, 'r') as f:
            content = f.read()
            print(content)
        
        # Verify the resumed mission
        resumed_lines = content.strip().split('\n')
        if len(resumed_lines) < 3:  # Header + HOME + at least one mission waypoint
            print("❌ ERROR: Resumed mission has fewer than 2 waypoints (HOME + mission)!")
            return False
        
        home_wp_line = resumed_lines[1]  # First waypoint after header (should be HOME)
        home_wp_parts = home_wp_line.split('\t')
        home_wp_new_idx = int(home_wp_parts[0])
        
        first_mission_wp_line = resumed_lines[2]  # Second waypoint (first mission waypoint)
        first_mission_wp_parts = first_mission_wp_line.split('\t')
        first_mission_wp_new_idx = int(first_mission_wp_parts[0])
        
        print()
        print("=" * 70)
        print("VERIFICATION:")
        print("=" * 70)
        print(f"HOME waypoint (index {home_wp_new_idx}): expected 0")
        print(f"First mission waypoint (index {first_mission_wp_new_idx}): expected 1")
        
        if home_wp_new_idx != 0:
            print(f"❌ ERROR: HOME waypoint has index {home_wp_new_idx}, not 0!")
            return False
        else:
            print("✓ HOME waypoint correctly indexed as 0")
        
        if first_mission_wp_new_idx != 1:
            print(f"❌ ERROR: First mission waypoint has index {first_mission_wp_new_idx}, not 1!")
            return False
        else:
            print("✓ First mission waypoint correctly indexed as 1")
        
        # Check the coordinates of HOME (should match original WP 0)
        original_wp0 = waypoint_dict[0].split('\t')
        print()
        print(f"Original WP 0 (HOME) coordinates: lat={original_wp0[8]}, lon={original_wp0[9]}")
        print(f"Resumed WP 0 (HOME) coordinates: lat={home_wp_parts[8]}, lon={home_wp_parts[9]}")
        
        if original_wp0[8] == home_wp_parts[8] and original_wp0[9] == home_wp_parts[9]:
            print("✓ HOME coordinates match!")
        else:
            print("❌ ERROR: HOME coordinates don't match!")
            return False
        
        # Check the coordinates match the original waypoint 3
        original_wp3 = waypoint_dict[3].split('\t')
        
        print()
        print(f"Original WP 3 coordinates: lat={original_wp3[8]}, lon={original_wp3[9]}")
        print(f"Resumed WP 1 coordinates: lat={first_mission_wp_parts[8]}, lon={first_mission_wp_parts[9]}")
        
        if original_wp3[8] == first_mission_wp_parts[8] and original_wp3[9] == first_mission_wp_parts[9]:
            print("✓ Coordinates match! First mission waypoint is original WP 3")
            print()
            print("=" * 70)
            print("✓✓✓ TEST PASSED! ✓✓✓")
            print("=" * 70)
            return True
        else:
            print("❌ ERROR: Coordinates don't match!")
            return False
        
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        output_file = test_file.replace('.waypoints', '_resumed.waypoints')
        if os.path.exists(output_file):
            print(f"\nKeeping resumed mission file for inspection: {output_file}")

if __name__ == '__main__':
    success = test_resume_mission()
    exit(0 if success else 1)
