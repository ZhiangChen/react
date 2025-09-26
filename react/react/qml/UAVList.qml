import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs

Rectangle {
    id: uavPanel
    color: "#f5f5f5"
    border.color: "#ddd"
    border.width: 1
    
    property var currentUAV: "UAV_1"  // Default UAV selection
    property int maxUAVs: 1  // Default to 1, will be updated when backend is ready
    property bool configLoaded: false  // Track if config has been loaded
    property bool controlAllUAVs: false  // false = selected UAV only, true = all UAVs
    property var missionFilePaths: ({})  // Object to store mission file paths for each UAV
    property int missionFileUpdateCounter: 0  // Counter to trigger UI updates when mission files change
    property var selectedUAVs: []  // Array to track multiple selected UAVs
    property int selectionUpdateCounter: 0  // Counter to force UI updates when selection changes
    
    onWidthChanged: {
        // Binding chain handles Grid updates: panel -> ScrollView -> Column -> Grid
    }
    
    onMaxUAVsChanged: {
        // UAV count updated - Grid will automatically adjust layout
    }
    
    // Timer to continuously check for backend availability and update maxUAVs
    Timer {
        id: backendCheckTimer
        interval: 500  // Check every 500ms
        running: true
        repeat: true
        onTriggered: {
            if (backend && backend.getMaxUAVs) {
                var newMaxUAVs = backend.getMaxUAVs()
                if (newMaxUAVs !== maxUAVs) {
                    maxUAVs = newMaxUAVs
                    configLoaded = true  // Mark config as loaded
                } else if (!configLoaded && newMaxUAVs > 1) {
                    // If maxUAVs is already correct but configLoaded is false, set it
                    configLoaded = true
                }
            }
        }
    }
    
    // Timer to refresh telemetry data
    Timer {
        id: refreshTimer
        interval: 500  // Update every 500ms
        running: true
        repeat: true
        onTriggered: {
            if (backend && backend.get_uav_status) {
                // Trigger UI updates - QML will automatically refresh bindings
                uavPanel.update()
            }
        }
    }
    
    ScrollView {
        id: scrollView
        anchors.fill: parent
        anchors.margins: 10
        
        onWidthChanged: {
            // Width changes propagate to Column and Grid automatically
        }
        
        Column {
            width: scrollView.width  // Use ScrollView width directly
            spacing: 12  // Consistent spacing between major sections
            
            onWidthChanged: {
                // Force Grid to recalculate when Column width changes
                uavGrid.width = width
            }
            
            // Loading indicator when config not yet loaded
            Rectangle {
                visible: !configLoaded
                width: parent.width
                height: 100
                color: "transparent"
                
                Text {
                    anchors.centerIn: parent
                    text: "Loading UAV configuration..."
                    font.pointSize: 12
                    color: "#666"
                }
            }
            
            // UAV Status Grid
            Grid {
                visible: configLoaded  // Only show grid after config is loaded
                id: uavGrid
                width: parent.width  // Use parent (Column) width
                columns: Math.max(1, Math.floor(width / (100 + spacing)))  // Dynamic columns based on 100px box width + spacing
                spacing: 8  // Tight spacing between UAV boxes
                
                onWidthChanged: {
                    var newColumns = Math.max(1, Math.floor(width / (100 + spacing)))
                    // Columns will be updated automatically by the binding
                }
                
                onColumnsChanged: {
                    // Grid layout automatically adjusts to new column count
                }
                
                Repeater {
                    model: configLoaded ? maxUAVs : 0  // Only show UAVs after config is loaded
                    
                    onItemAdded: {
                        // UAV rectangle added to grid
                    }
                    
                    onItemRemoved: {
                        // UAV rectangle removed from grid
                    }
                    
                    // UAV Status Template Component
                    Rectangle {
                        width: 100  // Fixed width for each UAV status box
                        height: 200  // Fixed height for each UAV status box
                        color: "white"
                        border.color: {
                            // Force reevaluation when selectionUpdateCounter changes
                            var dummy = selectionUpdateCounter
                            return selectedUAVs.indexOf(uavId) !== -1 ? "#2196F3" : "#ddd"
                        }
                        border.width: 1  // Keep border width consistent
                        radius: 3  // Smaller radius for tighter look
                        
                        property string uavId: "UAV_" + (index + 1)
                        
                        Component.onCompleted: {
                            // UAV status rectangle initialized
                        }
                        
                        Component.onDestruction: {
                            // UAV status rectangle cleaned up
                        }
                        
                        Column {
                            anchors.fill: parent
                            anchors.margins: 8  // Reduced margins
                            spacing: 2  // Even tighter spacing
                            
                            // Armed/Disarmed Status Light with UAV ID
                            Rectangle {
                                width: parent.width * 0.65  // Even narrower
                                height: 20  // Even smaller height
                                radius: 10  // Adjusted for smaller height
                                color: getArmedState(uavId) === "ARMED" ? "#4CAF50" : "#F44336"  // Green for armed, red for disarmed
                                
                                anchors.horizontalCenter: parent.horizontalCenter  // Center the light
                                
                                Text {
                                    text: uavId
                                    anchors.centerIn: parent
                                    font.bold: true
                                    font.pointSize: 8  // Even smaller font
                                    color: "white"  // White text for contrast against colored background
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        var index = selectedUAVs.indexOf(uavId)
                                        var newSelectedUAVs = selectedUAVs.slice()  // Create a copy
                                        if (index !== -1) {
                                            // UAV is already selected, remove it
                                            newSelectedUAVs.splice(index, 1)
                                            console.log("Deselected UAV:", uavId)
                                        } else {
                                            // UAV is not selected, add it
                                            newSelectedUAVs.push(uavId)
                                            console.log("Selected UAV:", uavId)
                                        }
                                        selectedUAVs = newSelectedUAVs  // Assign the new array to trigger binding update
                                        selectionUpdateCounter++  // Force UI update
                                        console.log("Currently selected UAVs:", selectedUAVs.join(", "))
                                        
                                        // Update currentUAV to the last selected UAV for control panel
                                        if (selectedUAVs.length > 0) {
                                            currentUAV = selectedUAVs[selectedUAVs.length - 1]
                                        } else {
                                            currentUAV = "UAV_1"  // Default fallback
                                        }
                                    }
                                }
                            }
                            
                            // Status indicator lights row with emojis
                            Row {
                                width: parent.width
                                spacing: 8  // Spacing between light+emoji columns
                                anchors.horizontalCenter: parent.horizontalCenter
                                
                                // Telem1 status light with emoji
                                Column {
                                    spacing: 2
                                    Rectangle {
                                        width: 12
                                        height: 12
                                        radius: 6  // Circular light
                                        color: getTelem1Status(uavId) ? "#4CAF50" : "#F44336"
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        text: "📡"
                                        font.pointSize: 8
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                                
                                // Telem2 status light with emoji
                                Column {
                                    spacing: 2
                                    Rectangle {
                                        width: 12
                                        height: 12
                                        radius: 6  // Circular light
                                        color: getTelem2Status(uavId) ? "#4CAF50" : "#F44336"
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        text: "📡"
                                        font.pointSize: 8
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                                
                                // GPS status light with emoji
                                Column {
                                    spacing: 2
                                    Rectangle {
                                        width: 12
                                        height: 12
                                        radius: 6  // Circular light
                                        color: getGPSStatus(uavId) ? "#4CAF50" : "#F44336"
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        text: "🛰️"
                                        font.pointSize: 8
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                                
                                // Battery status light with emoji
                                Column {
                                    spacing: 2
                                    Rectangle {
                                        width: 12
                                        height: 12
                                        radius: 6  // Circular light
                                        color: getBatteryStatus(uavId)
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        text: "🔋"
                                        font.pointSize: 8
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                            }
                            
                            Row {
                                width: parent.width
                                spacing: 8
                                Text { 
                                    text: "Mode: " + getFlightMode(uavId)
                                    font.pointSize: 9 
                                    width: parent.width
                                    elide: Text.ElideRight
                                }
                            }
                            
                            Text { 
                                text: "Battery: " + getBatteryLevel(uavId) + "%"
                                font.pointSize: 9
                                color: getBatteryLevel(uavId) < 25 ? "red" : (getBatteryLevel(uavId) < 50 ? "orange" : "green")
                            }
                            
                            Text { 
                                text: "Dist: " + getDistanceFromHome(uavId) + "m"
                                font.pointSize: 8
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            
                            Text { 
                                text: "Alt: " + getAltitude(uavId).toFixed(1) + "m"
                                font.pointSize: 9
                            }
                            
                            Text { 
                                text: "Speed: " + getGroundSpeed(uavId).toFixed(1) + " m/s"
                                font.pointSize: 9
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            
                            Text { 
                                text: "GPS: " + getGPSInfo(uavId)
                                font.pointSize: 9
                                color: getGPSFixType(uavId) >= 3 ? "green" : "orange"
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            
                            // Clickable mission file selector
                            Item {
                                width: parent.width
                                height: 14
                                
                                Text { 
                                    id: missionText
                                    text: {
                                        missionFileUpdateCounter  // This ensures the binding updates when counter changes
                                        var missionName = getMissionFilePath(uavId)
                                        return missionName === "Click to select..." ? "Mission: " + missionName : missionName
                                    }
                                    font.pointSize: 9
                                    color: "#0066cc"
                                    width: parent.width
                                    elide: Text.ElideRight
                                }
                                
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        uavMissionFileDialog.targetUAV = uavId
                                        uavMissionFileDialog.title = "Select Mission File for " + uavId
                                        uavMissionFileDialog.open()
                                    }
                                    onEntered: missionText.color = "#0099ff"
                                    onExited: missionText.color = "#0066cc"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Mission file dialog for individual UAVs
    FileDialog {
        id: uavMissionFileDialog
        title: "Select Mission File for UAV"
        nameFilters: ["Mission files (*.waypoints *.mission)", "All files (*)"]
        property string targetUAV: ""  // Store which UAV this dialog is for
        
        onAccepted: {
            var filePath = selectedFile.toString().replace("file:///", "")
            missionFilePaths[targetUAV] = filePath
            missionFileUpdateCounter++  // Trigger UI update
            console.log("Selected mission file for", targetUAV, ":", filePath)
            
            // Load the mission for the UAV
            if (backend) {
                try {
                    backend.load_mission(targetUAV, filePath)
                } catch(e) {
                    console.log("Error loading mission:", e)
                }
            }
        }
    }
    
    // JavaScript functions to interface with backend
    function getConnectionStatus() {
        if (!backend || !backend.uav_states) return false
        try {
            var status = backend.get_uav_status(currentUAV)
            return status !== null && status !== undefined
        } catch(e) {
            return false
        }
    }
    
    function getFlightMode(uavId) {
        if (!backend) return "UNKNOWN"
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.flight_status ? status.flight_status.flight_mode || "UNKNOWN" : "UNKNOWN"
        } catch(e) {
            return "UNKNOWN"
        }
    }
    
    function getArmedState(uavId) {
        if (!backend) return "DISARMED"
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.flight_status && status.flight_status.armed ? "ARMED" : "DISARMED"
        } catch(e) {
            return "DISARMED"
        }
    }
    
    function getBatteryLevel(uavId) {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.battery ? status.battery.remaining_percent || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getPosition(uavId) {
        if (!backend) return "N/A"
        try {
            var status = backend.get_uav_status(uavId)
            if (status && status.position) {
                var lat = status.position.latitude || 0
                var lon = status.position.longitude || 0
                return lat.toFixed(6) + ", " + lon.toFixed(6)
            }
            return "N/A"
        } catch(e) {
            return "N/A"
        }
    }
    
    function getDistanceFromHome(uavId) {
        if (!backend) return "N/A"
        try {
            var status = backend.get_uav_status(uavId)
            if (status && status.position) {
                // Get home position from config or use default
                var homeLat = 40.7128  // Default NYC coordinates
                var homeLon = -76.0060
                
                // Try to get home position from backend config
                if (backend && backend.config && backend.config.default_home_position) {
                    homeLat = backend.config.default_home_position.latitude || homeLat
                    homeLon = backend.config.default_home_position.longitude || homeLon
                }
                
                var uavLat = status.position.latitude || 0
                var uavLon = status.position.longitude || 0
                
                // Calculate distance using haversine formula approximation
                var dLat = (uavLat - homeLat) * Math.PI / 180
                var dLon = (uavLon - homeLon) * Math.PI / 180
                var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                        Math.cos(homeLat * Math.PI / 180) * Math.cos(uavLat * Math.PI / 180) *
                        Math.sin(dLon/2) * Math.sin(dLon/2)
                var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
                var distance = 6371000 * c  // Earth radius in meters
                
                return distance.toFixed(0)  // Return as integer meters
            }
            return "N/A"
        } catch(e) {
            return "N/A"
        }
    }
    
    function getAltitude(uavId) {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.position ? status.position.altitude_msl || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGroundSpeed(uavId) {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.position ? status.position.ground_speed || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGPSFixType(uavId) {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.gps ? status.gps.fix_type || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGPSInfo(uavId) {
        if (!backend) return "No GPS"
        try {
            var status = backend.get_uav_status(uavId)
            if (status && status.gps) {
                var sats = status.gps.satellites_visible || 0
                var fix = status.gps.fix_type || 0
                return sats + " sats (Fix: " + fix + ")"
            }
            return "No GPS"
        } catch(e) {
            return "No GPS"
        }
    }
    
    function getMissionNumber(uavId) {
        if (!backend) return "N/A"
        try {
            var status = backend.get_uav_status(uavId)
            return status && status.mission ? status.mission.current || "N/A" : "N/A"
        } catch(e) {
            return "N/A"
        }
    }
    
    function getMissionFilePath(uavId) {
        var filePath = missionFilePaths[uavId]
        if (filePath) {
            // Extract just the filename from the path and remove extension
            var fileName = filePath.split('/').pop().split('\\').pop()
            // Remove file extension
            var lastDotIndex = fileName.lastIndexOf('.')
            if (lastDotIndex > 0) {
                fileName = fileName.substring(0, lastDotIndex)
            }
            return fileName
        }
        return "Click to select..."
    }
    
    function getTelem1Status(uavId) {
        if (!backend) return false
        try {
            // Check if telem1 connection is active for this UAV
            var status = backend.get_uav_status(uavId)
            return status && status.telemetry && status.telemetry.telem1_connected
        } catch(e) {
            return false
        }
    }
    
    function getTelem2Status(uavId) {
        if (!backend) return false
        try {
            // Check if telem2 connection is active for this UAV
            var status = backend.get_uav_status(uavId)
            return status && status.telemetry && status.telemetry.telem2_connected
        } catch(e) {
            return false
        }
    }
    
    function getGPSStatus(uavId) {
        if (!backend) return false
        try {
            var status = backend.get_uav_status(uavId)
            // Consider GPS good if fix type >= 3 (3D fix)
            return status && status.gps && status.gps.fix_type >= 3
        } catch(e) {
            return false
        }
    }
    
    function getBatteryStatus(uavId) {
        if (!backend) return "#9E9E9E"  // Gray for unknown
        try {
            var batteryLevel = getBatteryLevel(uavId)
            if (batteryLevel >= 50) return "#4CAF50"  // Green for good
            if (batteryLevel >= 25) return "#FF9800"  // Orange for warning
            if (batteryLevel >= 10) return "#F44336"  // Red for critical
            return "#9E9E9E"  // Gray for unknown/no data
        } catch(e) {
            return "#9E9E9E"  // Gray for unknown
        }
    }
    
    // Control functions
    function armUAV(uavId) {
        if (backend && backend.uav_controller) {
            console.log("Arming UAV:", uavId)
            try {
                backend.uav_controller.arm_uav(uavId)
            } catch(e) {
                console.log("Error arming UAV:", e)
            }
        }
    }
    
    function disarmUAV(uavId) {
        if (backend && backend.uav_controller) {
            console.log("Disarming UAV:", uavId)
            try {
                backend.uav_controller.disarm_uav(uavId)
            } catch(e) {
                console.log("Error disarming UAV:", e)
            }
        }
    }
    
    function returnToLaunch(uavId) {
        if (backend && backend.uav_controller) {
            console.log("RTL for UAV:", uavId)
            try {
                backend.uav_controller.return_to_launch(uavId)
            } catch(e) {
                console.log("Error RTL:", e)
            }
        }
    }
    
    function landUAV(uavId) {
        if (backend && backend.uav_controller) {
            console.log("Landing UAV:", uavId)
            try {
                backend.uav_controller.land(uavId)
            } catch(e) {
                console.log("Error landing:", e)
            }
        }
    }
    
    function emergencyStop() {
        if (backend) {
            console.log("EMERGENCY STOP ALL")
            try {
                backend.emergency_stop_all()
            } catch(e) {
                console.log("Error emergency stop:", e)
            }
        }
    }
    
    function armAllUAVs() {
        if (backend && backend.uav_controller) {
            console.log("Arming ALL UAVs")
            for (var i = 1; i <= maxUAVs; i++) {
                var uavId = "UAV " + i
                try {
                    backend.uav_controller.arm_uav(uavId)
                } catch(e) {
                    console.log("Error arming UAV", uavId, ":", e)
                }
            }
        }
    }
    
    function disarmAllUAVs() {
        if (backend && backend.uav_controller) {
            console.log("Disarming ALL UAVs")
            for (var i = 1; i <= maxUAVs; i++) {
                var uavId = "UAV " + i
                try {
                    backend.uav_controller.disarm_uav(uavId)
                } catch(e) {
                    console.log("Error disarming UAV", uavId, ":", e)
                }
            }
        }
    }
    
    function returnToLaunchAll() {
        if (backend && backend.uav_controller) {
            console.log("RTL for ALL UAVs")
            for (var i = 1; i <= maxUAVs; i++) {
                var uavId = "UAV " + i
                try {
                    backend.uav_controller.return_to_launch(uavId)
                } catch(e) {
                    console.log("Error RTL for UAV", uavId, ":", e)
                }
            }
        }
    }
    
    function landAllUAVs() {
        if (backend && backend.uav_controller) {
            console.log("Landing ALL UAVs")
            for (var i = 1; i <= maxUAVs; i++) {
                var uavId = "UAV " + i
                try {
                    backend.uav_controller.land(uavId)
                } catch(e) {
                    console.log("Error landing UAV", uavId, ":", e)
                }
            }
        }
    }
    
    function loadMission(uavId) {
        console.log("Load mission requested for UAV:", uavId)
        var filePath = missionFilePaths[uavId]
        if (!filePath) {
            console.log("No mission file selected for UAV:", uavId)
            return
        }
        
        if (backend) {
            try {
                backend.load_mission(uavId, filePath)
                console.log("Mission loaded for", uavId, "from", filePath)
            } catch(e) {
                console.log("Error loading mission:", e)
            }
        }
    }
    
    function startMission(uavId) {
        if (backend) {
            console.log("Starting mission for UAV:", uavId)
            try {
                backend.start_mission(uavId)
            } catch(e) {
                console.log("Error starting mission:", e)
            }
        }
    }
}