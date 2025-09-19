import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: uavPanel
    color: "#f5f5f5"
    border.color: "#ddd"
    border.width: 1
    
    property var currentUAV: "UAV_1"  // Default UAV selection
    
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
        anchors.fill: parent
        anchors.margins: 10
        
        Column {
            width: parent.width
            spacing: 15
            
            // Header
            Text {
                text: "UAV Status Panel"
                font.bold: true
                font.pointSize: 14
                color: "#333"
            }
            
            // Connection Status
            Rectangle {
                width: parent.width
                height: 60
                color: getConnectionStatus() ? "#d4edda" : "#f8d7da"
                border.color: getConnectionStatus() ? "#c3e6cb" : "#f5c6cb"
                radius: 5
                
                Column {
                    anchors.centerIn: parent
                    Text {
                        text: "Connection: " + (getConnectionStatus() ? "Connected" : "Disconnected")
                        font.bold: true
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: "Status: Ready"
                        font.pointSize: 10
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }
            
            // Current UAV Telemetry
            Rectangle {
                width: parent.width
                height: 250
                color: "white"
                border.color: "#ddd"
                radius: 5
                
                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 8
                    
                    Text {
                        text: "UAV: " + currentUAV
                        font.bold: true
                        font.pointSize: 12
                        color: "#333"
                    }
                    
                    Row {
                        spacing: 20
                        Text { 
                            text: "Mode: " + getFlightMode()
                            font.pointSize: 10 
                        }
                        Text { 
                            text: getArmedState()
                            font.pointSize: 10
                            color: getArmedState() === "ARMED" ? "red" : "green"
                            font.bold: getArmedState() === "ARMED"
                        }
                    }
                    
                    Text { 
                        text: "Battery: " + getBatteryLevel() + "%"
                        font.pointSize: 10
                        color: getBatteryLevel() < 25 ? "red" : (getBatteryLevel() < 50 ? "orange" : "green")
                    }
                    
                    Text { 
                        text: "Position: " + getPosition()
                        font.pointSize: 9
                        wrapMode: Text.WordWrap
                    }
                    
                    Text { 
                        text: "Altitude: " + getAltitude().toFixed(1) + "m"
                        font.pointSize: 10
                    }
                    
                    Text { 
                        text: "Ground Speed: " + getGroundSpeed().toFixed(1) + " m/s"
                        font.pointSize: 10
                    }
                    
                    Text { 
                        text: "GPS: " + getGPSInfo()
                        font.pointSize: 10
                        color: getGPSFixType() >= 3 ? "green" : "orange"
                    }
                }
            }
            
            // Control Buttons
            Rectangle {
                width: parent.width
                height: 180
                color: "white"
                border.color: "#ddd"
                radius: 5
                
                Column {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10
                    
                    Text {
                        text: "Quick Controls"
                        font.bold: true
                        font.pointSize: 12
                        color: "#333"
                    }
                    
                    Row {
                        spacing: 10
                        
                        Button {
                            text: getArmedState() === "ARMED" ? "Disarm" : "Arm"
                            enabled: getConnectionStatus()
                            onClicked: {
                                if (getArmedState() === "ARMED") {
                                    disarmUAV()
                                } else {
                                    armUAV()
                                }
                            }
                        }
                        
                        Button {
                            text: "RTL"
                            enabled: getArmedState() === "ARMED"
                            onClicked: returnToLaunch()
                        }
                    }
                    
                    Row {
                        spacing: 10
                        
                        Button {
                            text: "Land"
                            enabled: getArmedState() === "ARMED"
                            onClicked: landUAV()
                        }
                        
                        Button {
                            text: "EMERGENCY STOP"
                            background: Rectangle {
                                color: parent.pressed ? "#c82333" : "#dc3545"
                                radius: 4
                            }
                            onClicked: emergencyStop()
                        }
                    }
                    
                    Row {
                        spacing: 10
                        
                        Button {
                            text: "Load Mission"
                            onClicked: loadMission()
                        }
                        
                        Button {
                            text: "Start Mission"
                            enabled: getConnectionStatus() && getArmedState() === "ARMED"
                            onClicked: startMission()
                        }
                    }
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
    
    function getFlightMode() {
        if (!backend) return "UNKNOWN"
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.flight_status ? status.flight_status.flight_mode || "UNKNOWN" : "UNKNOWN"
        } catch(e) {
            return "UNKNOWN"
        }
    }
    
    function getArmedState() {
        if (!backend) return "DISARMED"
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.flight_status && status.flight_status.armed ? "ARMED" : "DISARMED"
        } catch(e) {
            return "DISARMED"
        }
    }
    
    function getBatteryLevel() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.battery ? status.battery.remaining_percent || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getPosition() {
        if (!backend) return "N/A"
        try {
            var status = backend.get_uav_status(currentUAV)
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
    
    function getAltitude() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.position ? status.position.altitude_msl || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGroundSpeed() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.position ? status.position.ground_speed || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGPSFixType() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.gps ? status.gps.fix_type || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getGPSInfo() {
        if (!backend) return "No GPS"
        try {
            var status = backend.get_uav_status(currentUAV)
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
    
    // Control functions
    function armUAV() {
        if (backend && backend.uav_controller) {
            console.log("Arming UAV:", currentUAV)
            try {
                backend.uav_controller.arm_uav(currentUAV)
            } catch(e) {
                console.log("Error arming UAV:", e)
            }
        }
    }
    
    function disarmUAV() {
        if (backend && backend.uav_controller) {
            console.log("Disarming UAV:", currentUAV)
            try {
                backend.uav_controller.disarm_uav(currentUAV)
            } catch(e) {
                console.log("Error disarming UAV:", e)
            }
        }
    }
    
    function returnToLaunch() {
        if (backend && backend.uav_controller) {
            console.log("RTL for UAV:", currentUAV)
            try {
                backend.uav_controller.return_to_launch(currentUAV)
            } catch(e) {
                console.log("Error RTL:", e)
            }
        }
    }
    
    function landUAV() {
        if (backend && backend.uav_controller) {
            console.log("Landing UAV:", currentUAV)
            try {
                backend.uav_controller.land(currentUAV)
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
    
    function loadMission() {
        console.log("Load mission requested")
        // This would typically open a file dialog
        // For now, we'll use a hardcoded path as example
        if (backend) {
            try {
                backend.load_mission(currentUAV, "missions/example.waypoints")
            } catch(e) {
                console.log("Error loading mission:", e)
            }
        }
    }
    
    function startMission() {
        if (backend) {
            console.log("Starting mission for UAV:", currentUAV)
            try {
                backend.start_mission(currentUAV)
            } catch(e) {
                console.log("Error starting mission:", e)
            }
        }
    }
}