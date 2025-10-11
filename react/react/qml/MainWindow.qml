import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Controls.Material 2.15

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1200
    height: 700
    title: "REACT - Ground Control Station"
    
    Material.theme: Material.Light
    Material.primary: Material.Blue
    Material.accent: Material.Orange
    
    property bool connected: backend ? backend.get_uav_status("UAV_1") !== null : false
    property string currentTime: getCurrentTime()
    property string missionTimer: getMissionTimer()

    // Button highlight properties for keyboard shortcuts
    property bool pauseButtonHighlighted: false
    property bool manualButtonHighlighted: false
    property bool rtlButtonHighlighted: false
    property bool landButtonHighlighted: false
    property bool stopButtonHighlighted: false

    menuBar: MenuBar {
        Material.background: "#000000"
        Material.foreground: "#ffffff"
        Material.theme: Material.Dark
        
        background: Rectangle {
            color: "#000000"
            border.color: "#333333"
            border.width: 1
            
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: "#404040"
            }
        }
        
        Menu {
            title: "File"
            
            Action {
                text: "Load Mission..."
                icon.name: "document-open"
                onTriggered: missionFileDialog.open()
            }
            MenuSeparator {}
            Action {
                text: "Exit"
                icon.name: "application-exit"
                onTriggered: Qt.quit()
            }
        }
        
        Menu {
            title: "UAV"
            
            Action {
                text: "Connect"
                enabled: !connected
                icon.name: "network-connect"
                onTriggered: connectUAV()
            }
            Action {
                text: "Disconnect" 
                enabled: connected
                icon.name: "network-disconnect"
                onTriggered: disconnectUAV()
            }
            MenuSeparator {}
            Action {
                text: "Arm"
                enabled: connected
                icon.name: "media-playback-start"
                onTriggered: armUAV()
            }
            Action {
                text: "Disarm"
                enabled: connected
                icon.name: "media-playback-stop"
                onTriggered: disarmUAV()
            }
            MenuSeparator {}
            Action {
                text: "Emergency RTL"
                enabled: connected
                icon.name: "go-home"
                onTriggered: emergencyRTL()
            }
            Action {
                text: "Emergency Stop All"
                icon.name: "process-stop"
                onTriggered: emergencyStopAll()
            }
        }
        
        Menu {
            title: "Mission"
            
            Action {
                text: "Start Mission"
                enabled: connected
                icon.name: "media-playback-start"
                onTriggered: startMission()
            }
            Action {
                text: "Pause Mission"
                enabled: connected
                icon.name: "media-playback-pause"
                onTriggered: pauseMission()
            }
            Action {
                text: "Abort Mission"
                enabled: connected
                icon.name: "process-stop"
                onTriggered: abortMission()
            }
        }
        
        Menu {
            title: "View"
            
            Action {
                text: "Center Map on UAV"
                enabled: connected
                icon.name: "zoom-fit-best"
                onTriggered: console.log("Center UAV - functionality to be added to web map")
            }
            Action {
                text: "Next Map Type"
                icon.name: "view-refresh"
                onTriggered: console.log("Toggle map layer - functionality to be added to web map")
            }
            Action {
                text: "Show Satellite Info"
                icon.name: "dialog-information"
                onTriggered: console.log("Show satellite info - functionality to be added to web map")
            }
        }
        
        Menu {
            title: "Help"
            
            Action {
                text: "Hotkeys"
                icon.name: "help-hint"
                onTriggered: hotkeysDialog.open()
            }
            MenuSeparator {}
            Action {
                text: "About REACT"
                icon.name: "help-about"
                onTriggered: aboutDialog.open()
            }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        // Map Container (left - half width by default)
        MapContainer {
            id: mapView
            SplitView.minimumWidth: 50
            SplitView.preferredWidth: parent.width * 0.5  // Half width by default

            onUavSelected: function(uavId) {
                console.log("UAV selected from web map:", uavId)
                // Update UAV selection in the list
                uavList.currentUAV = uavId
            }

            onMapClicked: function(latitude, longitude) {
                console.log("Map clicked from web map:", latitude, longitude)
                // Handle waypoint addition or other map interactions
            }

            onWebMapReady: function() {
                console.log("Web-based satellite map is ready in MainWindow")
            }
        }

        // Right side: UAV Status (top) and Controls (bottom)
        SplitView {
            orientation: Qt.Vertical
            SplitView.minimumWidth: 50
            SplitView.preferredWidth: parent.width * 0.5  // Half width by default

            // UAV Status Panel (top right)
            UAVList {
                id: uavList
                SplitView.fillHeight: true
                SplitView.minimumHeight: 300
            }

            // Control Panel (bottom right)
            Rectangle {
                id: controlPanel
                SplitView.minimumHeight: 170
                SplitView.preferredHeight: 200
                color: "#f5f5f5"
                border.color: "#ddd"
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 10

                    // Left side: Control buttons
                    Column {
                        width: parent.width - Math.max(parent.width * 0.3, 120) - parent.spacing  // Remaining space after time displays
                        spacing: -2

                        Row {
                            spacing: -1
                            Button {
                                width: 70
                                height: 35
                                text: "Selected"
                                font.pointSize: 8
                                background: Rectangle {
                                    color: uavList.controlAllUAVs ? "#ffffff" : (parent.hovered ? "#c8e6c9" : "#e8f5e8")
                                    border.color: "#999999"
                                    border.width: 1
                                    radius: 0
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                onClicked: uavList.controlAllUAVs = false
                            }

                            Button {
                                width: 70
                                height: 35
                                text: "All UAVs"
                                font.pointSize: 8
                                background: Rectangle {
                                    color: uavList.controlAllUAVs ? (parent.hovered ? "#c8e6c9" : "#e8f5e8") : "#ffffff"
                                    border.color: "#999999"
                                    border.width: 1
                                    radius: 0
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                onClicked: uavList.controlAllUAVs = true
                            }
                        }

                        Row {
                            spacing: 2

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "Arm"
                                background: Rectangle {
                                    color: parent.hovered ? "#f0f0f0" : "#f8f8f8"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                onClicked: {
                                    console.log("Arm button clicked!")
                                    console.log("controlAllUAVs:", uavList.controlAllUAVs)
                                    console.log("selectedUAVs:", uavList.selectedUAVs)
                                    console.log("uavList object:", uavList)
                                    console.log("uavList.armUAV function:", uavList.armUAV)
                                    if (uavList.controlAllUAVs) {
                                        uavList.armAllUAVs()
                                    } else {
                                        // Arm all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            console.log("Calling armUAV for:", uavList.selectedUAVs[i])
                                            try {
                                                uavList.armUAV(uavList.selectedUAVs[i])
                                            } catch(e) {
                                                console.log("Error calling uavList.armUAV:", e)
                                            }
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "Upload Mission"
                                background: Rectangle {
                                    color: parent.hovered ? "#f0f0f0" : "#f8f8f8"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                onClicked: {
                                    missionFileDialog.open()
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "Start Mission"
                                background: Rectangle {
                                    color: parent.hovered ? "#f0f0f0" : "#f8f8f8"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                onClicked: {
                                    if (backend) {
                                        if (uavList.controlAllUAVs) {
                                            console.log("Start mission for all UAVs")
                                        } else {
                                            // Start mission for all selected UAVs
                                            for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                                console.log("Start mission for UAV", uavList.selectedUAVs[i])
                                                backend.start_mission(uavList.selectedUAVs[i])
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Row {
                            spacing: 2

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "&Pause"
                                background: Rectangle {
                                    color: pauseButtonHighlighted ? "#ffff99" : (parent.hovered ? "#f0f0f0" : "#f8f8f8")
                                    border.color: pauseButtonHighlighted ? "#ffcc00" : "#cccccc"
                                    border.width: pauseButtonHighlighted ? 2 : 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: "<b>P</b>ause"
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        console.log("Pause all UAVs")
                                    } else {
                                        // Pause all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            console.log("Pause UAV", uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "Manual"
                                background: Rectangle {
                                    color: manualButtonHighlighted ? "#ffff99" : (parent.hovered ? "#f0f0f0" : "#f8f8f8")
                                    border.color: manualButtonHighlighted ? "#ffcc00" : "#cccccc"
                                    border.width: manualButtonHighlighted ? 2 : 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: "<b>M</b>anual"
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        console.log("Switch all UAVs to manual mode")
                                    } else {
                                        // Switch all selected UAVs to manual mode
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            console.log("Switch UAV to manual mode", uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "Resume"
                                background: Rectangle {
                                    color: parent.hovered ? "#f0f0f0" : "#f8f8f8"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        console.log("Resume all UAVs")
                                    } else {
                                        // Resume all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            console.log("Resume UAV", uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "+Resume"
                                background: Rectangle {
                                    color: parent.hovered ? "#f0f0f0" : "#f8f8f8"
                                    border.color: "#cccccc"
                                    border.width: 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: parent.text
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        console.log("Prev Resume all UAVs")
                                    } else {
                                        // Prev Resume all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            console.log("Prev Resume UAV", uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }
                        }

                        Row {
                            spacing: 2

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "&RTL"
                                background: Rectangle {
                                    color: rtlButtonHighlighted ? "#ffff99" : (parent.hovered ? "#f0f0f0" : "#f8f8f8")
                                    border.color: rtlButtonHighlighted ? "#ffcc00" : "#cccccc"
                                    border.width: rtlButtonHighlighted ? 2 : 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: "<b>R</b>TL"
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        uavList.returnToLaunchAll()
                                    } else {
                                        // RTL all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            uavList.returnToLaunch(uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "&Land"
                                background: Rectangle {
                                    color: landButtonHighlighted ? "#ffff99" : (parent.hovered ? "#f0f0f0" : "#f8f8f8")
                                    border.color: landButtonHighlighted ? "#ffcc00" : "#cccccc"
                                    border.width: landButtonHighlighted ? 2 : 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: "<b>L</b>and"
                                    font: parent.font
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                enabled: true
                                onClicked: {
                                    if (uavList.controlAllUAVs) {
                                        uavList.landAllUAVs()
                                    } else {
                                        // Land all selected UAVs
                                        for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                                            uavList.landUAV(uavList.selectedUAVs[i])
                                        }
                                    }
                                }
                            }

                            Button {
                                width: 90
                                height: 50
                                font.pointSize: 8
                                text: "&STOP"
                                background: Rectangle {
                                    color: stopButtonHighlighted ? "#ffff99" : (parent.hovered ? "#f0f0f0" : "#f8f8f8")
                                    border.color: stopButtonHighlighted ? "#ffcc00" : "#cccccc"
                                    border.width: stopButtonHighlighted ? 2 : 1
                                    radius: 2
                                }
                                contentItem: Text {
                                    text: "<b>S</b>TOP"
                                    color: "#333333"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    width: parent.width
                                    height: parent.height
                                }
                                onClicked: {
                                    uavList.emergencyStop()
                                }
                            }
                        }
                    }

                    // Right side: Time displays
                    Column {
                        width: Math.max(parent.width * 0.3, 120)  // 30% width for times, minimum 120px
                        spacing: 8

                        Text {
                            width: parent.width
                            text: currentTime
                            font.pointSize: 16
                            font.bold: true
                            color: "#2E7D32"
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Text {
                            width: parent.width
                            text: "Mission: " + missionTimer
                            font.pointSize: 12
                            font.bold: true
                            color: "#1976D2"
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Button {
                            anchors.horizontalCenter: parent.horizontalCenter  // Center the button horizontally
                            width: parent.width * 0.8  // 80% width to make it narrower
                            height: 40
                            text: "Mission Planner"
                            font.pointSize: 10
                            font.bold: true
                            background: Rectangle {
                                color: parent.hovered ? "#e3f2fd" : "#f5f5f5"
                                border.color: "#2196F3"
                                border.width: 1
                                radius: 3
                            }
                            contentItem: Text {
                                text: parent.text
                                font: parent.font
                                color: "#1976D2"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: {
                                if (!missionPlannerWindowLoader.active) {
                                    missionPlannerWindowLoader.active = true
                                }
                                missionPlannerWindowLoader.item.show()
                                missionPlannerWindowLoader.item.raise()
                                missionPlannerWindowLoader.item.requestActivate()
                            }
                        }
                    }
                }
            }
        }
    }

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
    
    // Hotkeys dialog
    Dialog {
        id: hotkeysDialog
        title: "Keyboard Shortcuts"
        width: 450
        height: 350
        modal: true
        anchors.centerIn: parent
        
        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15
            
            Text {
                text: "Keyboard Shortcuts"
                font.bold: true
                font.pointSize: 16
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Rectangle {
                width: parent.width
                height: 1
                color: "#ccc"
            }
            
            Text {
                text: "Control Panel Shortcuts:"
                font.bold: true
                font.pointSize: 12
            }
            
            Column {
                spacing: 8
                width: parent.width
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+P</b>"
                        width: 60
                        font.family: "Courier New"
                    }
                    Text { text: "Pause mission" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+M</b>"
                        width: 60
                        font.family: "Courier New"
                    }
                    Text { text: "Switch to Manual mode" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+R</b>"
                        width: 60
                        font.family: "Courier New"
                    }
                    Text { text: "Return to Launch (RTL)" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+L</b>"
                        width: 60
                        font.family: "Courier New"
                    }
                    Text { text: "Land UAV" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+S</b>"
                        width: 60
                        font.family: "Courier New"
                    }
                    Text { text: "Emergency STOP" }
                }
            }
            
            Rectangle {
                width: parent.width
                height: 1
                color: "#ccc"
            }
            
            Text {
                text: "Note: Bold letters in button text indicate available shortcuts."
                font.pointSize: 10
                color: "#666"
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
        
        Button {
            text: "Close"
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            onClicked: hotkeysDialog.close()
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
            // Update live time displays
            currentTime = getCurrentTime()
            missionTimer = getMissionTimer()
        }
    }

    // Button highlight reset timers
    Timer {
        id: pauseHighlightTimer
        interval: 500
        repeat: false
        onTriggered: pauseButtonHighlighted = false
    }

    Timer {
        id: manualHighlightTimer
        interval: 500
        repeat: false
        onTriggered: manualButtonHighlighted = false
    }

    Timer {
        id: rtlHighlightTimer
        interval: 500
        repeat: false
        onTriggered: rtlButtonHighlighted = false
    }

    Timer {
        id: landHighlightTimer
        interval: 500
        repeat: false
        onTriggered: landButtonHighlighted = false
    }

    Timer {
        id: stopHighlightTimer
        interval: 500
        repeat: false
        onTriggered: stopButtonHighlighted = false
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
        console.log("MainWindow.armUAV() called")
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
    
    function getMissionTimer() {
        if (!backend) return "00:00:00"
        try {
            var status = backend.get_mission_status("UAV_1")
            if (status && status.active && status.start_time) {
                var elapsed = Math.floor((new Date() - new Date(status.start_time * 1000)) / 1000)
                var hours = Math.floor(elapsed / 3600)
                var minutes = Math.floor((elapsed % 3600) / 60)
                var seconds = elapsed % 60
                return String(hours).padStart(2, '0') + ":" + 
                       String(minutes).padStart(2, '0') + ":" + 
                       String(seconds).padStart(2, '0')
            }
            return "00:00:00"
        } catch(e) {
            return "00:00:00"
        }
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

    // Keyboard shortcuts
    Shortcut {
        sequence: "Ctrl+P"
        onActivated: {
            // Highlight button and trigger action
            pauseButtonHighlighted = true
            pauseHighlightTimer.start()
            
            // Trigger Pause button
            if (uavList.controlAllUAVs) {
                console.log("Pause all UAVs (shortcut)")
            } else {
                // Pause all selected UAVs
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    console.log("Pause UAV", uavList.selectedUAVs[i], "(shortcut)")
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+M"
        onActivated: {
            // Highlight button and trigger action
            manualButtonHighlighted = true
            manualHighlightTimer.start()
            
            // Trigger Manual button
            if (uavList.controlAllUAVs) {
                console.log("Switch all UAVs to manual mode (shortcut)")
            } else {
                // Switch all selected UAVs to manual mode
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    console.log("Switch UAV to manual mode", uavList.selectedUAVs[i], "(shortcut)")
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+R"
        onActivated: {
            // Highlight button and trigger action
            rtlButtonHighlighted = true
            rtlHighlightTimer.start()
            
            // Trigger RTL button
            if (uavList.controlAllUAVs) {
                uavList.returnToLaunchAll()
            } else {
                // RTL all selected UAVs
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.returnToLaunch(uavList.selectedUAVs[i])
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+L"
        onActivated: {
            // Highlight button and trigger action
            landButtonHighlighted = true
            landHighlightTimer.start()
            
            // Trigger Land button
            if (uavList.controlAllUAVs) {
                uavList.landAllUAVs()
            } else {
                // Land all selected UAVs
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.landUAV(uavList.selectedUAVs[i])
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+S"
        onActivated: {
            // Highlight button and trigger action
            stopButtonHighlighted = true
            stopHighlightTimer.start()
            
            // Trigger STOP button
            uavList.emergencyStop()
        }
    }

    // Mission Planner Floating Window Instance
    Loader {
        id: missionPlannerWindowLoader
        source: "MissionPlanner.qml"
        active: false
    }
}
