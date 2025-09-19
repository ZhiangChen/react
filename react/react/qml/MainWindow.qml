import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1200
    height: 800
    title: "REACT - Ground Control Station"
    
    property bool connected: backend ? backend.get_uav_status("UAV_1") !== null : false

    MenuBar {
        Menu {
            title: "File"
            Action {
                text: "Load Mission..."
                onTriggered: missionFileDialog.open()
            }
            MenuSeparator {}
            Action {
                text: "Exit"
                onTriggered: Qt.quit()
            }
        }
        
        Menu {
            title: "UAV"
            Action {
                text: "Connect"
                enabled: !connected
                onTriggered: connectUAV()
            }
            Action {
                text: "Disconnect" 
                enabled: connected
                onTriggered: disconnectUAV()
            }
            MenuSeparator {}
            Action {
                text: "Arm"
                enabled: connected
                onTriggered: armUAV()
            }
            Action {
                text: "Disarm"
                enabled: connected
                onTriggered: disarmUAV()
            }
            MenuSeparator {}
            Action {
                text: "Emergency RTL"
                enabled: connected
                onTriggered: emergencyRTL()
            }
            Action {
                text: "Emergency Stop All"
                onTriggered: emergencyStopAll()
            }
        }
        
        Menu {
            title: "Mission"
            Action {
                text: "Start Mission"
                enabled: connected
                onTriggered: startMission()
            }
            Action {
                text: "Pause Mission"
                enabled: connected
                onTriggered: pauseMission()
            }
            Action {
                text: "Abort Mission"
                enabled: connected
                onTriggered: abortMission()
            }
        }
        
        Menu {
            title: "View"
            Action {
                text: "Center Map on UAV"
                enabled: connected
                onTriggered: mapView.centerOnUAV()
            }
            Action {
                text: "Clear Flight Path"
                onTriggered: mapView.clearFlightPath()
            }
        }
        
        Menu {
            title: "Help"
            Action {
                text: "About REACT"
                onTriggered: aboutDialog.open()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        MapView {
            id: mapView
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        UAVList {
            id: uavList
            Layout.preferredWidth: 320
            Layout.fillHeight: true
        }
    }

    StatusBar {
        RowLayout {
            anchors.fill: parent
            
            Text {
                text: connected ? "Connected" : "Disconnected"
                color: connected ? "green" : "red"
                font.bold: true
            }
            
            Text {
                text: " | "
                color: "#666"
            }
            
            Text {
                text: "UAVs: " + getConnectedUAVCount()
                color: "#333"
            }
            
            Text {
                text: " | "
                color: "#666"
            }
            
            Text {
                text: getCurrentTime()
                color: "#333"
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: getMissionStatus()
                color: "#333"
            }
        }
    }
    
    // File dialogs
    FileDialog {
        id: missionFileDialog
        title: "Select Mission File"
        nameFilters: ["Mission files (*.waypoints *.mission)", "All files (*)"]
        onAccepted: {
            if (backend) {
                console.log("Loading mission file:", selectedFile)
                backend.load_mission("UAV_1", selectedFile.toString())
            }
        }
    }
    
    // About dialog
    Dialog {
        id: aboutDialog
        title: "About REACT"
        width: 400
        height: 300
        modal: true
        anchors.centerIn: parent
        
        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15
            
            Text {
                text: "REACT Ground Control Station"
                font.bold: true
                font.pointSize: 16
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Text {
                text: "Robust Emergency Aircraft Control Terminal"
                font.pointSize: 12
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Rectangle {
                width: parent.width
                height: 1
                color: "#ccc"
            }
            
            Text {
                text: "Features:"
                font.bold: true
            }
            
            Column {
                spacing: 5
                Text { text: "• Dual telemetry architecture" }
                Text { text: "• Real-time UAV monitoring" }
                Text { text: "• Mission planning and execution" }
                Text { text: "• Emergency safety systems" }
                Text { text: "• Multi-UAV fleet management" }
            }
            
            Rectangle {
                width: parent.width
                height: 1
                color: "#ccc"
            }
            
            Text {
                text: "Built with Qt/QML and Python"
                font.pointSize: 10
                color: "#666"
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
        
        Button {
            text: "Close"
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            onClicked: aboutDialog.close()
        }
    }
    
    // Timer for status updates
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            // This will trigger property updates
            connected = backend ? backend.get_uav_status("UAV_1") !== null : false
        }
    }
    
    // JavaScript functions
    function connectUAV() {
        console.log("Connect UAV requested")
        // Backend connection is automatically handled
    }
    
    function disconnectUAV() {
        console.log("Disconnect UAV requested") 
        if (backend) {
            try {
                backend.stop()
            } catch(e) {
                console.log("Error disconnecting:", e)
            }
        }
    }
    
    function armUAV() {
        if (backend && backend.uav_controller) {
            try {
                backend.uav_controller.arm_uav("UAV_1")
            } catch(e) {
                console.log("Error arming UAV:", e)
            }
        }
    }
    
    function disarmUAV() {
        if (backend && backend.uav_controller) {
            try {
                backend.uav_controller.disarm_uav("UAV_1")
            } catch(e) {
                console.log("Error disarming UAV:", e)
            }
        }
    }
    
    function emergencyRTL() {
        if (backend && backend.uav_controller) {
            try {
                backend.uav_controller.emergency_rtl("UAV_1")
            } catch(e) {
                console.log("Error emergency RTL:", e)
            }
        }
    }
    
    function emergencyStopAll() {
        if (backend) {
            try {
                backend.emergency_stop_all()
            } catch(e) {
                console.log("Error emergency stop all:", e)
            }
        }
    }
    
    function startMission() {
        if (backend) {
            try {
                backend.start_mission("UAV_1")
            } catch(e) {
                console.log("Error starting mission:", e)
            }
        }
    }
    
    function pauseMission() {
        if (backend) {
            try {
                backend.pause_mission("UAV_1")
            } catch(e) {
                console.log("Error pausing mission:", e)
            }
        }
    }
    
    function abortMission() {
        if (backend) {
            try {
                backend.abort_mission("UAV_1")
            } catch(e) {
                console.log("Error aborting mission:", e)
            }
        }
    }
    
    function getConnectedUAVCount() {
        if (!backend || !backend.uav_states) return 0
        try {
            return Object.keys(backend.uav_states).length
        } catch(e) {
            return 0
        }
    }
    
    function getCurrentTime() {
        return new Date().toLocaleTimeString()
    }
    
    function getMissionStatus() {
        if (!backend) return "No mission"
        try {
            var status = backend.get_mission_status("UAV_1")
            if (status && status.active) {
                return "Mission: " + status.current_waypoint + "/" + status.total_waypoints
            }
            return "No active mission"
        } catch(e) {
            return "No mission"
        }
    }
}