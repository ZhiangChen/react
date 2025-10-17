# Per-UAV Mission Timer Implementation Summary

## Overview
Replaced the global mission timer in the main window with individual mission timers for each UAV. Each UAV now tracks its own mission time independently.

## Changes Made

### 1. Removed Global Mission Timer from MainWindow.qml

**Removed:**
- Property `missionTimer: getMissionTimer()` (line 20)
- Mission timer Text display from status bar (lines 602-608)
- Timer update in Timer.onTriggered (line 893)
- `getMissionTimer()` function (lines 1034-1047)

**Result:** Main window no longer shows a global mission timer.

### 2. Added Mission Timer to UAVState (core/uav_state.py)

**Added Properties:**
```python
self.mission_start_time = None  # Timestamp when mission started (takeoff)
self.mission_elapsed_time = 0.0  # Elapsed mission time in seconds
self.mission_running = False  # True if mission timer is running
```

**Added Methods:**
- `start_mission_timer()` - Starts the timer when UAV takes off
- `stop_mission_timer()` - Stops the timer when UAV lands
- `get_mission_elapsed_time()` - Returns current elapsed time in seconds
- `reset_mission_timer()` - Resets timer when new mission starts

**Updated to_dict():**
- Added `mission_elapsed_time` and `mission_running` to telemetry data

### 3. Added Timer Display to UAVList.qml

**Added UI Row (after mission name):**
```qml
Text {
    text: {
        telemetryUpdateCounter  // Update when telemetry changes
        return "Time: " + getMissionTime(uavId)
    }
    font.pointSize: 9
    color: "#666666"
    width: parent.width
    elide: Text.ElideRight
}
```

**Added Helper Function:**
```javascript
function getMissionTime(uavId) {
    // Formats mission_elapsed_time as HH:MM:SS
    // Returns "00:00:00" if timer not running
}
```

### 4. Implemented Timer Logic (core/telemetry_manager.py)

**HEARTBEAT Message Handler:**
Monitors armed status and flight mode changes to automatically start/stop timer:

**Start Timer When:**
- UAV is armed AND
- Mode changes to flying mode: GUIDED, AUTO, LOITER, POSHOLD, or ALT_HOLD
- Timer not already running

**Stop Timer When:**
- UAV disarms (lands and motors stop) OR
- UAV enters LAND mode

**Example Flow:**
1. UAV arms → Wait for mode change
2. Mode changes to GUIDED → Timer starts
3. UAV flies mission
4. UAV enters LAND mode → Timer stops
5. UAV disarms → Timer stays stopped

### 5. Reset Timer on New Mission (core/mission_manager.py)

**start_mission() Method:**
- Calls `uav_state.reset_mission_timer()` before starting mission
- Ensures timer starts at 00:00:00 for each new mission
- Logs timer reset event

## Timer Behavior

### Automatic Start
- Timer starts when UAV enters a flying mode after arming
- Detects transition from ground modes (STABILIZE, etc.) to flying modes
- Only starts once per flight session

### Automatic Stop
- Timer stops when UAV enters LAND mode
- Also stops when UAV disarms
- Preserves final time after stopping (doesn't reset to zero)

### Manual Reset
- Timer resets to 00:00:00 when "Start Mission" command is sent
- Allows fresh timing for each mission attempt
- Independent of armed/disarmed state

## UI Display

### Per-UAV Status Panel
Each UAV's status panel now shows:
```
UAV_1
Mode: GUIDED
Alt: 15.2m
Dist: 234m
Speed: 5.2 m/s
Batt: 85%
GPS: 3D Fix (12)
Mission: waypoint_mission.mission
Time: 00:03:45  ← NEW!
```

### Format
- **HH:MM:SS** format (hours:minutes:seconds)
- Updates every second while timer is running
- Shows last elapsed time when stopped
- Shows "00:00:00" when reset or never started

## Files Modified

1. **qml/MainWindow.qml**
   - Removed global mission timer property
   - Removed mission timer display from status bar
   - Removed getMissionTimer() function

2. **core/uav_state.py**
   - Added mission_start_time, mission_elapsed_time, mission_running properties
   - Added start_mission_timer(), stop_mission_timer(), get_mission_elapsed_time(), reset_mission_timer() methods
   - Updated to_dict() to include timer data

3. **qml/UAVList.qml**
   - Added mission timer Text element after mission name
   - Added getMissionTime(uavId) helper function
   - Timer updates with telemetryUpdateCounter

4. **core/telemetry_manager.py**
   - Enhanced HEARTBEAT message handler
   - Added logic to detect takeoff (mode change while armed)
   - Added logic to detect landing (LAND mode or disarming)
   - Automatic timer start/stop based on flight state

5. **core/mission_manager.py**
   - Enhanced start_mission() method
   - Calls reset_mission_timer() when new mission starts
   - Logs timer reset event

## Testing Scenarios

### Test 1: Normal Flight
1. Arm UAV → Timer stays at 00:00:00
2. Takeoff (mode changes to GUIDED) → Timer starts
3. Fly for 5 minutes → Timer shows 00:05:00
4. Land → Timer stops at final time
5. Disarm → Timer preserves final time

### Test 2: Multiple Flights
1. First flight → Timer shows 00:03:30
2. Land and disarm → Timer stops at 00:03:30
3. Arm and takeoff again → Timer continues from 00:03:30
4. Land → Timer shows cumulative time (e.g., 00:07:45)

### Test 3: New Mission
1. Timer shows 00:07:45 from previous flight
2. Click "Start Mission" → Timer resets to 00:00:00
3. Arm and takeoff → Timer starts fresh from 00:00:00

### Test 4: Multiple UAVs
1. UAV_1 flies for 5 minutes → Shows 00:05:00
2. UAV_2 flies for 3 minutes → Shows 00:03:00
3. Each UAV has independent timer
4. Timers don't affect each other

## Benefits

✅ **Per-UAV Tracking:** Each UAV has its own independent mission timer
✅ **Automatic Operation:** No manual start/stop needed - based on flight state
✅ **Persistent Time:** Timer preserves value after landing (until reset)
✅ **Mission-Based Reset:** Fresh timer for each new mission
✅ **Real-time Updates:** Updates every second while running
✅ **Clear Display:** Easy-to-read HH:MM:SS format
✅ **Multi-UAV Support:** Scales to any number of UAVs

## Implementation Notes

### Flight Mode Detection
The timer uses flight modes to detect when UAV is actually flying:
- **Flying Modes:** GUIDED, AUTO, LOITER, POSHOLD, ALT_HOLD
- **Ground Modes:** STABILIZE, ACRO, LAND (not counted as mission time)

### Time Accuracy
- Updates based on system time (time.time())
- Millisecond precision internally
- Displayed as integer seconds
- No drift or accumulation errors

### Edge Cases Handled
- Multiple arm/disarm cycles → Timer continues
- Mode changes while flying → Timer keeps running
- Network interruptions → Timer state preserved
- Application restart → Timer resets (by design)

## Date
October 16, 2025
