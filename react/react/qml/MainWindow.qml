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
                                text: "Takeoff"
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
                                    console.log("Takeoff button clicked!")
                                    takeoffDialog.open()
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
                                    // First, check which UAVs to process based on control mode
                                    var uavsToCheck = uavList.controlAllUAVs ? getAllUAVs() : uavList.selectedUAVs
                                    
                                    console.log("Upload Mission: Checking", uavsToCheck.length, "UAV(s)...")
                                    
                                    // Collect UAVs that need uploading
                                    var uavsToUpload = []
                                    var skippedNoTelem1 = 0
                                    var skippedNoMission = 0
                                    
                                    for (var i = 0; i < uavsToCheck.length; i++) {
                                        var uavId = uavsToCheck[i]
                                        
                                        // Check if UAV has telem1 connection
                                        var hasTelem1 = uavList.getTelem1Status(uavId)
                                        if (!hasTelem1) {
                                            console.log("  Skipping", uavId, "- no telem1 connection")
                                            skippedNoTelem1++
                                            continue
                                        }
                                        
                                        // Check if mission file is selected (use full path function)
                                        var missionFileFullPath = uavList.getMissionFileFullPath(uavId)
                                        if (!missionFileFullPath) {
                                            console.log("  Skipping", uavId, "- no mission file selected")
                                            skippedNoMission++
                                            continue
                                        }
                                        
                                        // Add to upload list
                                        uavsToUpload.push({
                                            uavId: uavId,
                                            missionFile: missionFileFullPath
                                        })
                                    }
                                    
                                    // If nothing to upload, show error message and return
                                    if (uavsToUpload.length === 0) {
                                        var message = "No missions uploaded."
                                        if (skippedNoTelem1 > 0) {
                                            message += "\n\n" + skippedNoTelem1 + " UAV(s) skipped (no telem1 connection)."
                                        }
                                        if (skippedNoMission > 0) {
                                            message += "\n" + skippedNoMission + " UAV(s) skipped (no mission file selected)."
                                        }
                                        console.warn(message)
                                        return
                                    }
                                    
                                    // Show upload window and start uploading
                                    missionUploadWindow.reset(uavsToUpload.length)
                                    missionUploadWindow.show()
                                    
                                    // Start uploading each UAV
                                    console.log("Starting uploads for", uavsToUpload.length, "UAV(s)...")
                                    for (var i = 0; i < uavsToUpload.length; i++) {
                                        var uavData = uavsToUpload[i]
                                        missionUploadWindow.addUAV(uavData.uavId)
                                        console.log("  Uploading mission to", uavData.uavId, ":", uavData.missionFile)
                                        backend.load_mission(uavData.uavId, uavData.missionFile)
                                    }
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
                                    // Determine which UAVs to start
                                    var uavsToCheck = uavList.controlAllUAVs ? getAllUAVs() : uavList.selectedUAVs
                                    
                                    console.log("Start Mission: Checking", uavsToCheck.length, "UAV(s)...")
                                    
                                    // Collect UAVs with mission files and waypoint info
                                    var uavsToStart = []
                                    
                                    for (var i = 0; i < uavsToCheck.length; i++) {
                                        var uavId = uavsToCheck[i]
                                        
                                        // Get mission file
                                        var missionFile = uavList.getMissionFileFullPath(uavId)
                                        if (!missionFile) {
                                            console.log("  Skipping", uavId, "- no mission file selected")
                                            continue
                                        }
                                        
                                        // Get UAV status for waypoint info
                                        var status = backend.get_uav_status(uavId)
                                        var originalWaypointIndices = []
                                        if (status && status.mission && status.mission.original_waypoint_indices) {
                                            originalWaypointIndices = status.mission.original_waypoint_indices
                                        }
                                        
                                        // Add to start list with waypoint info
                                        uavsToStart.push({
                                            uavId: uavId,
                                            missionFile: missionFile,
                                            originalWaypointIndices: originalWaypointIndices
                                        })
                                    }
                                    
                                    if (uavsToStart.length === 0) {
                                        console.log("  No UAVs with mission files to start")
                                        return
                                    }
                                    
                                    // Store UAVs to start and show dialog
                                    startMissionDialog.uavsToStart = uavsToStart
                                    startMissionDialog.open()
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
                                    pauseDialog.open()
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
                                    manualDialog.open()
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
                                    resumeDialog.open()
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
                                    // Determine which UAVs to process
                                    var uavsToCheck = uavList.controlAllUAVs ? getAllUAVs() : uavList.selectedUAVs
                                    
                                    console.log("+Resume: Checking", uavsToCheck.length, "UAV(s)...")
                                    
                                    // Collect UAVs eligible for resume
                                    var uavsToResume = []
                                    var skippedNoWaypoints = 0
                                    var skippedNoMission = 0
                                    var skippedNoTelem1 = 0
                                    
                                    for (var i = 0; i < uavsToCheck.length; i++) {
                                        var uavId = uavsToCheck[i]
                                        
                                        // Check if UAV has telem1 connection
                                        var hasTelem1 = uavList.getTelem1Status(uavId)
                                        if (!hasTelem1) {
                                            console.log("  Skipping", uavId, "- no telem1 connection")
                                            skippedNoTelem1++
                                            continue
                                        }
                                        
                                        // Check if UAV has completed waypoints
                                        var status = backend.get_uav_status(uavId)
                                        if (!status || !status.mission || status.mission.last_completed_waypoint < 0) {
                                            console.log("  Skipping", uavId, "- no waypoints completed yet")
                                            skippedNoWaypoints++
                                            continue
                                        }
                                        
                                        // Check if mission file is available
                                        var missionFile = uavList.getMissionFileFullPath(uavId)
                                        if (!missionFile) {
                                            console.log("  Skipping", uavId, "- no mission file selected")
                                            skippedNoMission++
                                            continue
                                        }
                                        
                                        // Add to resume list with detailed waypoint info
                                        uavsToResume.push({
                                            uavId: uavId,
                                            missionFile: missionFile,
                                            lastWaypoint: status.mission.last_completed_waypoint,
                                            nextWaypoint: status.mission.next_resume_waypoint,
                                            totalWaypoints: status.mission.total_waypoints,
                                            originalWaypointIndices: status.mission.original_waypoint_indices || [],
                                            reachedWaypointIndices: status.mission.reached_waypoint_indices || [],
                                            remainingWaypointIndices: status.mission.remaining_waypoint_indices || []
                                        })
                                    }
                                    
                                    // Show error if nothing to resume
                                    if (uavsToResume.length === 0) {
                                        var message = "No missions can be resumed."
                                        if (skippedNoTelem1 > 0) {
                                            message += "\n\n" + skippedNoTelem1 + " UAV(s) skipped (no telem1 connection)."
                                        }
                                        if (skippedNoWaypoints > 0) {
                                            message += "\n" + skippedNoWaypoints + " UAV(s) skipped (no waypoints completed)."
                                        }
                                        if (skippedNoMission > 0) {
                                            message += "\n" + skippedNoMission + " UAV(s) skipped (no mission file)."
                                        }
                                        resumeErrorDialog.text = message
                                        resumeErrorDialog.open()
                                        return
                                    }
                                    
                                    // Store UAVs to resume and show confirmation
                                    resumeConfirmDialog.uavsToResume = uavsToResume
                                    resumeConfirmDialog.open()
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
                                    rtlDialog.open()
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
                                    landDialog.open()
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
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
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
            
            background: Rectangle {
                color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                border.color: "#707070"
                border.width: 1
                radius: 0  // Rectangular button
            }
            
            contentItem: Text {
                text: parent.text
                font: parent.font
                color: "#000000"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
    
    // Hotkeys dialog
    Dialog {
        id: hotkeysDialog
        title: "Keyboard Shortcuts"
        width: 450
        height: 560
        modal: true
        anchors.centerIn: parent
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15
            
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
                text: "UAV Selection Shortcuts:"
                font.bold: true
                font.pointSize: 12
            }
            
            Column {
                spacing: 8
                width: parent.width
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+1-9</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Toggle selection of UAV 1-9" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+0</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Toggle selection of UAV 10" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+C</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Unselect all UAVs" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+A</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Switch to All UAVs mode" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+S</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Switch to Selected UAVs mode" }
                }
                
                Row {
                    spacing: 20
                    Text { 
                        text: "<b>Ctrl+Alt+R</b>"
                        width: 140
                        font.family: "Courier New"
                    }
                    Text { text: "Reverse UAV selection" }
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
            
            background: Rectangle {
                color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                border.color: "#707070"
                border.width: 1
                radius: 0  // Rectangular button
            }
            
            contentItem: Text {
                text: parent.text
                font: parent.font
                color: "#000000"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
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
    
    function getAllUAVs() {
        // Get list of all UAV IDs from backend
        if (!backend) return []
        try {
            var uavList = backend.getAllUAVs()
            var uavIds = []
            for (var i = 0; i < uavList.length; i++) {
                if (uavList[i] && uavList[i].uav_id) {
                    uavIds.push(uavList[i].uav_id)
                }
            }
            return uavIds
        } catch(e) {
            console.log("Error getting UAV list:", e)
            return []
        }
    }

    // Keyboard shortcuts
    Shortcut {
        sequence: "Ctrl+P"
        onActivated: {
            // Highlight button and trigger action
            pauseButtonHighlighted = true
            pauseHighlightTimer.start()
            
            // Open pause confirmation dialog
            pauseDialog.open()
        }
    }

    Shortcut {
        sequence: "Ctrl+M"
        onActivated: {
            // Highlight button and trigger action
            manualButtonHighlighted = true
            manualHighlightTimer.start()
            
            // Open manual mode confirmation dialog
            manualDialog.open()
        }
    }

    Shortcut {
        sequence: "Ctrl+R"
        onActivated: {
            // Highlight button and trigger action
            rtlButtonHighlighted = true
            rtlHighlightTimer.start()
            
            // Open RTL confirmation dialog
            rtlDialog.open()
        }
    }

    Shortcut {
        sequence: "Ctrl+L"
        onActivated: {
            // Highlight button and trigger action
            landButtonHighlighted = true
            landHighlightTimer.start()
            
            // Open land confirmation dialog
            landDialog.open()
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

    // UAV Selection Shortcuts (Ctrl+Alt+Number)
    // UAV 1
    Shortcut {
        sequence: "Ctrl+Alt+1"
        onActivated: {
            console.log("UAV 1 shortcut activated: Ctrl+Alt+1")
            uavList.toggleUAVSelection("UAV_1")
        }
    }
    
    // UAV 2
    Shortcut {
        sequence: "Ctrl+Alt+2"
        onActivated: {
            console.log("UAV 2 shortcut activated: Ctrl+Alt+2")
            uavList.toggleUAVSelection("UAV_2")
        }
    }
    
    // UAV 3
    Shortcut {
        sequence: "Ctrl+Alt+3"
        onActivated: {
            console.log("UAV 3 shortcut activated: Ctrl+Alt+3")
            uavList.toggleUAVSelection("UAV_3")
        }
    }
    
    // UAV 4
    Shortcut {
        sequence: "Ctrl+Alt+4"
        onActivated: {
            console.log("UAV 4 shortcut activated: Ctrl+Alt+4")
            uavList.toggleUAVSelection("UAV_4")
        }
    }
    
    // UAV 5
    Shortcut {
        sequence: "Ctrl+Alt+5"
        onActivated: {
            console.log("UAV 5 shortcut activated: Ctrl+Alt+5")
            uavList.toggleUAVSelection("UAV_5")
        }
    }
    
    // UAV 6
    Shortcut {
        sequence: "Ctrl+Alt+6"
        onActivated: {
            console.log("UAV 6 shortcut activated: Ctrl+Alt+6")
            uavList.toggleUAVSelection("UAV_6")
        }
    }
    
    // UAV 7
    Shortcut {
        sequence: "Ctrl+Alt+7"
        onActivated: {
            console.log("UAV 7 shortcut activated: Ctrl+Alt+7")
            uavList.toggleUAVSelection("UAV_7")
        }
    }
    
    // UAV 8
    Shortcut {
        sequence: "Ctrl+Alt+8"
        onActivated: {
            console.log("UAV 8 shortcut activated: Ctrl+Alt+8")
            uavList.toggleUAVSelection("UAV_8")
        }
    }
    
    // UAV 9
    Shortcut {
        sequence: "Ctrl+Alt+9"
        onActivated: {
            console.log("UAV 9 shortcut activated: Ctrl+Alt+9")
            uavList.toggleUAVSelection("UAV_9")
        }
    }
    
    // UAV 10 - Using Ctrl+Alt+0
    Shortcut {
        sequence: "Ctrl+Alt+0"
        onActivated: {
            console.log("UAV 10 shortcut activated: Ctrl+Alt+0")
            uavList.toggleUAVSelection("UAV_10")
        }
    }

    // Unselect all UAVs hotkey
    Shortcut {
        sequence: "Ctrl+Alt+C"
        onActivated: {
            console.log("Unselect all UAVs shortcut activated: Ctrl+Alt+C")
            uavList.unselectAllUAVs()
        }
    }
    
    // Toggle between All UAVs and Selected UAVs mode
    Shortcut {
        sequence: "Ctrl+Alt+A"
        onActivated: {
            console.log("Toggle UAV control mode shortcut activated: Ctrl+Alt+A")
            uavList.toggleAllUAVs()
        }
    }
    
    // Switch to Selected UAVs mode
    Shortcut {
        sequence: "Ctrl+Alt+S"
        onActivated: {
            console.log("Switch to Selected UAVs mode shortcut activated: Ctrl+Alt+S")
            uavList.toggleSelectedUAVs()
        }
    }
    
    // Reverse UAV selection
    Shortcut {
        sequence: "Ctrl+Alt+R"
        onActivated: {
            console.log("Reverse UAV selection shortcut activated: Ctrl+Alt+R")
            uavList.reverseUAVSelection()
        }
    }

    // Mission Planner Floating Window Instance
    Loader {
        id: missionPlannerWindowLoader
        source: "MissionPlanner.qml"
        active: false
        onLoaded: {
            // Set the mapView reference when the mission planner is loaded
            item.mapView = mapView
        }
    }

    // Takeoff Altitude Dialog
    Dialog {
        id: takeoffDialog
        title: "Takeoff Altitude"
        width: 300
        height: 180
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        property real takeoffAltitude: 1.0  // Default 1 meter
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: takeoffDialog.accept()
            Keys.onEnterPressed: takeoffDialog.accept()
            Keys.onEscapePressed: takeoffDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 15
            
            Text {
                text: "Enter takeoff altitude (meters):"
                font.pointSize: 10
                color: "#333333"
            }
            
            TextField {
                id: altitudeInput
                width: parent.width
                text: "1.0"
                validator: DoubleValidator {
                    bottom: 0.5
                    top: 100.0
                    decimals: 1
                }
                placeholderText: "1.0"
                font.pointSize: 10
                
                onAccepted: {
                    takeoffDialog.accept()
                }
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: takeoffDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "Takeoff"
                    width: 80
                    highlighted: true
                    onClicked: takeoffDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            var altitude = parseFloat(altitudeInput.text)
            if (isNaN(altitude) || altitude < 0.5) {
                altitude = 1.0  // Default to 1 meter if invalid
            }
            
            console.log("Takeoff confirmed with altitude:", altitude)
            
            if (uavList.controlAllUAVs) {
                uavList.takeoffAllUAVs(altitude)
            } else {
                // Takeoff all selected UAVs
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    console.log("Calling takeoff for:", uavList.selectedUAVs[i])
                    try {
                        uavList.takeoffUAV(uavList.selectedUAVs[i], altitude)
                    } catch(e) {
                        console.log("Error calling uavList.takeoffUAV:", e)
                    }
                }
            }
        }
        
        onOpened: {
            altitudeInput.text = "1.0"
            altitudeInput.selectAll()
            altitudeInput.forceActiveFocus()
        }
    }

    // Pause (Brake) Confirmation Dialog
    Dialog {
        id: pauseDialog
        title: "Confirm Pause"
        width: 350
        height: 150
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: pauseDialog.accept()
            Keys.onEnterPressed: pauseDialog.accept()
            Keys.onEscapePressed: pauseDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 20
            
            Text {
                text: uavList.controlAllUAVs ? 
                    "Enter BRAKE mode for all UAVs?" : 
                    "Enter BRAKE mode for " + uavList.selectedUAVs.length + " selected UAV(s)?"
                font.pointSize: 10
                color: "#333333"
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: pauseDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "Pause"
                    width: 80
                    highlighted: true
                    onClicked: pauseDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            if (uavList.controlAllUAVs) {
                uavList.brakeAllUAVs()
            } else {
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.brakeUAV(uavList.selectedUAVs[i])
                }
            }
        }
    }

    // Manual (Loiter) Confirmation Dialog
    Dialog {
        id: manualDialog
        title: "Confirm Manual Mode"
        width: 350
        height: 150
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: manualDialog.accept()
            Keys.onEnterPressed: manualDialog.accept()
            Keys.onEscapePressed: manualDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 20
            
            Text {
                text: uavList.controlAllUAVs ? 
                    "Switch all UAVs to LOITER mode?" : 
                    "Switch " + uavList.selectedUAVs.length + " selected UAV(s) to LOITER mode?"
                font.pointSize: 10
                color: "#333333"
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: manualDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "Manual"
                    width: 80
                    highlighted: true
                    onClicked: manualDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            if (uavList.controlAllUAVs) {
                uavList.setLoiterModeAll()
            } else {
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.setLoiterMode(uavList.selectedUAVs[i])
                }
            }
        }
    }

    // Resume (Auto) Confirmation Dialog
    Dialog {
        id: resumeDialog
        title: "Confirm Resume Mission"
        width: 350
        height: 150
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: resumeDialog.accept()
            Keys.onEnterPressed: resumeDialog.accept()
            Keys.onEscapePressed: resumeDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 20
            
            Text {
                text: uavList.controlAllUAVs ? 
                    "Resume mission (AUTO mode) for all UAVs?" : 
                    "Resume mission (AUTO mode) for " + uavList.selectedUAVs.length + " selected UAV(s)?"
                font.pointSize: 10
                color: "#333333"
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: resumeDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "Resume"
                    width: 80
                    highlighted: true
                    onClicked: resumeDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            if (uavList.controlAllUAVs) {
                uavList.setAutoModeAll()
            } else {
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.setAutoMode(uavList.selectedUAVs[i])
                }
            }
        }
    }

    // RTL Confirmation Dialog
    Dialog {
        id: rtlDialog
        title: "Confirm Return to Launch"
        width: 350
        height: 150
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: rtlDialog.accept()
            Keys.onEnterPressed: rtlDialog.accept()
            Keys.onEscapePressed: rtlDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 20
            
            Text {
                text: uavList.controlAllUAVs ? 
                    "Return to launch for all UAVs?" : 
                    "Return to launch for " + uavList.selectedUAVs.length + " selected UAV(s)?"
                font.pointSize: 10
                color: "#333333"
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: rtlDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "RTL"
                    width: 80
                    highlighted: true
                    onClicked: rtlDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            if (uavList.controlAllUAVs) {
                uavList.returnToLaunchAll()
            } else {
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.returnToLaunch(uavList.selectedUAVs[i])
                }
            }
        }
    }

    // Land Confirmation Dialog
    Dialog {
        id: landDialog
        title: "Confirm Landing"
        width: 350
        height: 150
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: landDialog.accept()
            Keys.onEnterPressed: landDialog.accept()
            Keys.onEscapePressed: landDialog.reject()
        
        Column {
            anchors.fill: parent
            spacing: 20
            
            Text {
                text: uavList.controlAllUAVs ? 
                    "Land all UAVs at current position?" : 
                    "Land " + uavList.selectedUAVs.length + " selected UAV(s)?"
                font.pointSize: 10
                color: "#333333"
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                
                Button {
                    text: "Cancel"
                    width: 80
                    onClicked: landDialog.reject()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                
                Button {
                    text: "Land"
                    width: 80
                    highlighted: true
                    onClicked: landDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                        border.color: "#003d80"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
        }  // End Item wrapper
        
        onAccepted: {
            if (uavList.controlAllUAVs) {
                uavList.landAllUAVs()
            } else {
                for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                    uavList.landUAV(uavList.selectedUAVs[i])
                }
            }
        }
    }

    // Start Mission Confirmation Dialog
    Dialog {
        id: startMissionDialog
        title: "Start Mission"
        width: 500
        height: 320
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        property var uavsToStart: []
        property string validationError: ""
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0
        }
        
        onOpened: {
            // Reset input field to default (0) when dialog opens
            startWaypointInput.text = "0"
            validationError = ""
            startWaypointInput.forceActiveFocus()
            startWaypointInput.selectAll()
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: startMissionDialog.accept()
            Keys.onEnterPressed: startMissionDialog.accept()
            Keys.onEscapePressed: startMissionDialog.reject()
        
            Column {
                anchors.fill: parent
                spacing: 15
                
                // Info text
                Text {
                    text: {
                        if (startMissionDialog.uavsToStart.length === 0) return ""
                        
                        var msg = "Start mission for " + 
                                  startMissionDialog.uavsToStart.length + " UAV(s)\n\n"
                        
                        // Show info for each UAV
                        for (var i = 0; i < Math.min(3, startMissionDialog.uavsToStart.length); i++) {
                            var uav = startMissionDialog.uavsToStart[i]
                            var totalWaypoints = uav.originalWaypointIndices ? uav.originalWaypointIndices.length : 0
                            msg += "• " + uav.uavId + ": " + totalWaypoints + " waypoints\n"
                        }
                        
                        if (startMissionDialog.uavsToStart.length > 3) {
                            msg += "• ... and " + (startMissionDialog.uavsToStart.length - 3) + " more\n"
                        }
                        
                        return msg
                    }
                    font.pointSize: 10
                    color: "#333333"
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
                
                // Waypoint input section
                Column {
                    width: parent.width
                    spacing: 8
                    
                    Text {
                        text: "Start from waypoint (0 = start from beginning):"
                        font.pointSize: 10
                        font.bold: true
                        color: "#333333"
                    }
                    
                    Row {
                        spacing: 10
                        
                        TextField {
                            id: startWaypointInput
                            width: 100
                            placeholderText: ""
                            font.pointSize: 10
                            validator: IntValidator { bottom: 0; top: 9999 }
                            
                            background: Rectangle {
                                color: "white"
                                border.color: startMissionDialog.validationError !== "" ? "#d32f2f" : "#cccccc"
                                border.width: 2
                                radius: 0
                            }
                            
                            onTextChanged: {
                                startMissionDialog.validationError = ""
                            }
                        }
                        
                        Text {
                            text: "(Default: 0)"
                            font.pointSize: 9
                            color: "#666666"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    
                    // Validation error message
                    Text {
                        text: startMissionDialog.validationError
                        font.pointSize: 9
                        color: "#d32f2f"
                        visible: startMissionDialog.validationError !== ""
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }
                }
                
                // Buttons
                Row {
                    spacing: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Button {
                        text: "Cancel"
                        width: 100
                        onClicked: startMissionDialog.reject()
                        
                        background: Rectangle {
                            color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                            border.color: "#707070"
                            border.width: 1
                            radius: 0
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: "#000000"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Button {
                        text: "Start Mission"
                        width: 120
                        highlighted: true
                        onClicked: startMissionDialog.accept()
                        
                        background: Rectangle {
                            color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                            border.color: "#003d80"
                            border.width: 1
                            radius: 0
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
        
        onAccepted: {
            // Validate input waypoint
            var inputText = startWaypointInput.text.trim()
            if (inputText === "") {
                validationError = "Please enter a waypoint number (0 for start)"
                open()
                return
            }
            
            var startFromWaypoint = parseInt(inputText)
            if (isNaN(startFromWaypoint)) {
                validationError = "Invalid waypoint number"
                open()
                return
            }
            
            // If waypoint is 0, just start normally without modifying mission
            if (startFromWaypoint === 0) {
                console.log("Start Mission: Starting from waypoint 0 (normal start)")
                if (uavList.controlAllUAVs) {
                    uavList.startMissionAll()
                } else {
                    for (var i = 0; i < uavList.selectedUAVs.length; i++) {
                        uavList.startMission(uavList.selectedUAVs[i])
                    }
                }
                return
            }
            
            // If waypoint is not 0, validate and upload modified mission
            if (uavsToStart.length > 0) {
                var uav = uavsToStart[0]
                var originalIndices = uav.originalWaypointIndices
                var isValid = false
                
                for (var j = 0; j < originalIndices.length; j++) {
                    if (originalIndices[j] === startFromWaypoint) {
                        isValid = true
                        break
                    }
                }
                
                if (!isValid) {
                    validationError = "Waypoint " + startFromWaypoint + " is not in the original mission. Valid waypoints: " + originalIndices.join(", ")
                    open()
                    return
                }
            }
            
            console.log("Start Mission: Starting from waypoint", startFromWaypoint, "for", uavsToStart.length, "UAV(s)")
            
            // Show upload window (pass true to indicate this is a resume operation for auto-start)
            missionUploadWindow.reset(uavsToStart.length, true)
            missionUploadWindow.show()
            
            // Call backend resume_mission_from_waypoint for each UAV with custom waypoint
            for (var i = 0; i < uavsToStart.length; i++) {
                var uav = uavsToStart[i]
                console.log("  Starting mission for", uav.uavId, "from waypoint", startFromWaypoint)
                missionUploadWindow.addUAV(uav.uavId)
                
                // Call backend.resume_mission_from_waypoint with custom waypoint
                var success = backend.resume_mission_from_waypoint(uav.uavId, uav.missionFile, startFromWaypoint)
                if (!success) {
                    console.error("Failed to start mission for", uav.uavId)
                }
            }
        }
    }

    // Resume Mission Confirmation Dialog
    Dialog {
        id: resumeConfirmDialog
        title: "Confirm Resume Mission"
        width: 450
        height: 220
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        property var uavsToResume: []
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: resumeConfirmDialog.accept()
            Keys.onEnterPressed: resumeConfirmDialog.accept()
            Keys.onEscapePressed: resumeConfirmDialog.reject()
        
            Column {
                anchors.fill: parent
                spacing: 20
                
                Text {
                    text: {
                        if (resumeConfirmDialog.uavsToResume.length === 0) return ""
                        
                        var msg = "Resume mission from last completed waypoint for " + 
                                  resumeConfirmDialog.uavsToResume.length + " UAV(s)?\n\n"
                        
                        // Show waypoint info for each UAV
                        for (var i = 0; i < Math.min(3, resumeConfirmDialog.uavsToResume.length); i++) {
                            var uav = resumeConfirmDialog.uavsToResume[i]
                            
                            // Calculate remaining waypoints from original mission
                            var originalTotal = uav.originalWaypointIndices ? uav.originalWaypointIndices.length : 0
                            var reachedCount = uav.reachedWaypointIndices ? uav.reachedWaypointIndices.length : 0
                            var remainingCount = originalTotal - reachedCount
                            
                            // Use pre-calculated next waypoint
                            var nextWaypoint = uav.nextWaypoint >= 0 ? uav.nextWaypoint : "?"
                            
                            msg += "• " + uav.uavId + ": Last completed WP " + uav.lastWaypoint + 
                                   ", resume from WP " + nextWaypoint + 
                                   " (" + remainingCount + " waypoints remaining)\n"
                        }
                        
                        if (resumeConfirmDialog.uavsToResume.length > 3) {
                            msg += "• ... and " + (resumeConfirmDialog.uavsToResume.length - 3) + " more\n"
                        }
                        
                        return msg
                    }
                    font.pointSize: 10
                    color: "#333333"
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
                
                Row {
                    spacing: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Button {
                        text: "Cancel"
                        width: 100
                        onClicked: resumeConfirmDialog.reject()
                        
                        background: Rectangle {
                            color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                            border.color: "#707070"
                            border.width: 1
                            radius: 0
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: "#000000"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Button {
                        text: "Resume Mission"
                        width: 140
                        highlighted: true
                        onClicked: resumeConfirmDialog.accept()
                        
                        background: Rectangle {
                            color: parent.pressed ? "#0050a0" : (parent.hovered ? "#0060c0" : "#0078d4")
                            border.color: "#003d80"
                            border.width: 1
                            radius: 0
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: "#ffffff"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
        
        onAccepted: {
            console.log("+Resume: Starting mission resume for", uavsToResume.length, "UAV(s)")
            
            // Show upload window (pass true to indicate this is a resume operation)
            missionUploadWindow.reset(uavsToResume.length, true)
            missionUploadWindow.show()
            
            // Call backend resume_mission for each UAV
            for (var i = 0; i < uavsToResume.length; i++) {
                var uav = uavsToResume[i]
                console.log("  Resuming mission for", uav.uavId, "from waypoint", uav.lastWaypoint + 1)
                missionUploadWindow.addUAV(uav.uavId)
                
                // Call backend.resume_mission
                var success = backend.resume_mission(uav.uavId, uav.missionFile)
                if (!success) {
                    console.error("Failed to resume mission for", uav.uavId)
                }
            }
        }
    }

    // Resume Mission Error Dialog
    Dialog {
        id: resumeErrorDialog
        title: "Cannot Resume Mission"
        width: 400
        height: 180
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        
        property string text: ""
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: resumeErrorDialog.accept()
            Keys.onEnterPressed: resumeErrorDialog.accept()
            Keys.onEscapePressed: resumeErrorDialog.reject()
        
            Column {
                anchors.fill: parent
                spacing: 20
                
                Text {
                    text: resumeErrorDialog.text
                    font.pointSize: 10
                    color: "#d32f2f"
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
                
                Button {
                    text: "OK"
                    width: 100
                    anchors.horizontalCenter: parent.horizontalCenter
                    onClicked: resumeErrorDialog.accept()
                    
                    background: Rectangle {
                        color: parent.pressed ? "#d0d0d0" : (parent.hovered ? "#e0e0e0" : "#f0f0f0")
                        border.color: "#707070"
                        border.width: 1
                        radius: 0
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "#000000"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
    
    /* OLD UPLOAD PROGRESS DIALOG - REPLACED BY MissionUploadSummaryDialog
    // Upload Mission Progress Dialog
    Dialog {
        id: uploadMissionProgressDialog
        title: "Uploading Missions"
        width: 450
        height: 280
        modal: true
        anchors.centerIn: parent
        closePolicy: Dialog.NoAutoClose  // Prevent closing during upload
        
        property int totalUAVs: 0
        property int completedUAVs: 0
        property string currentUAVId: ""
        property var uploadQueue: []
        property int skippedNoTelem1: 0
        property int skippedNoMission: 0
        property var uploadResults: ({})  // Track upload success/failure for each UAV
        property int successCount: 0
        property int failureCount: 0
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Timer {
            id: startTimer
            interval: 200  // Delay to allow dialog to render
            repeat: false
            onTriggered: uploadMissionProgressDialog.processNextUpload()
        }
        
        Timer {
            id: uploadTimer
            interval: 500  // 500ms delay between uploads for better UI visibility
            repeat: false
            onTriggered: uploadMissionProgressDialog.processNextUpload()
        }
        
        Timer {
            id: summaryTimer
            interval: 2000  // Wait 2 seconds for all backend results to arrive
            repeat: false
            onTriggered: uploadMissionProgressDialog.showSummary()
        }
        
        function startUpload() {
            // Use timer to ensure dialog is fully rendered before starting upload
            startTimer.start()
        }
        
        function showSummary() {
            var message = "Mission Upload Summary\n\n"
            message += "✓ Success: " + successCount + " UAV(s)\n"
            message += "✗ Failed: " + failureCount + " UAV(s)"
            
            if (skippedNoTelem1 > 0) {
                message += "\n\n⊘ " + skippedNoTelem1 + " UAV(s) skipped (no telem1 connection)"
            }
            if (skippedNoMission > 0) {
                message += "\n⊘ " + skippedNoMission + " UAV(s) skipped (no mission file selected)"
            }
            
            uploadMissionResultDialog.message = message
            uploadMissionProgressDialog.close()
            uploadMissionResultDialog.open()
        }
        
        function processNextUpload() {
            if (uploadQueue.length === 0) {
                // All uploads complete, wait for backend results then show summary
                uploadTimer.stop()
                console.log("All uploads requested, waiting for results...")
                console.log("Current counts - Success:", successCount, "Failed:", failureCount)
                // Wait 2 seconds for backend results to arrive
                summaryTimer.start()
                return
            }
            
            // Get next UAV to upload
            var uploadItem = uploadQueue.shift()
            currentUAVId = uploadItem.uavId
            
            console.log("  Uploading mission to", uploadItem.uavId, ":", uploadItem.missionFile)
            
            // Upload mission
            if (backend) {
                backend.load_mission(uploadItem.uavId, uploadItem.missionFile)
            }
            
            completedUAVs++
            
            // Schedule next upload
            uploadTimer.start()
        }
        
        // Listen to mission upload results from backend
        Connections {
            target: backend
            function onMission_upload_result(uavId, success, message) {
                console.log("✓ Upload result received for", uavId, ":", success, "-", message)
                uploadMissionProgressDialog.uploadResults[uavId] = {success: success, message: message}
                if (success) {
                    uploadMissionProgressDialog.successCount++
                    console.log("  Success count now:", uploadMissionProgressDialog.successCount)
                } else {
                    uploadMissionProgressDialog.failureCount++
                    console.log("  Failure count now:", uploadMissionProgressDialog.failureCount)
                }
            }
        }
        
        Item {
            anchors.fill: parent
            
            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 15
                
                Text {
                    text: "Uploading mission files to UAVs..."
                    font.pointSize: 10
                    font.bold: true
                }
                
                Text {
                    text: uploadMissionProgressDialog.currentUAVId 
                          ? "Currently uploading to: " + uploadMissionProgressDialog.currentUAVId
                          : "Preparing upload..."
                    font.pointSize: 9
                    color: "#666666"
                }
                
                Text {
                    text: "Progress: " + uploadMissionProgressDialog.completedUAVs + " / " + uploadMissionProgressDialog.totalUAVs
                    font.pointSize: 11
                    font.bold: true
                    color: "#0078d4"
                }
                
                Text {
                    text: "✓ Success: " + uploadMissionProgressDialog.successCount + "   ✗ Failed: " + uploadMissionProgressDialog.failureCount
                    font.pointSize: 9
                    color: "#666666"
                }
                
                // Progress bar
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#f0f0f0"
                    border.color: "#cccccc"
                    border.width: 1
                    radius: 0
                    
                    Rectangle {
                        width: uploadMissionProgressDialog.totalUAVs > 0 
                               ? (parent.width * uploadMissionProgressDialog.completedUAVs / uploadMissionProgressDialog.totalUAVs)
                               : 0
                        height: parent.height
                        color: "#0078d4"
                        radius: 0
                    }
                    
                    Text {
                        anchors.centerIn: parent
                        text: uploadMissionProgressDialog.totalUAVs > 0 
                              ? Math.round(100 * uploadMissionProgressDialog.completedUAVs / uploadMissionProgressDialog.totalUAVs) + "%"
                              : "0%"
                        font.pointSize: 9
                        color: uploadMissionProgressDialog.completedUAVs > uploadMissionProgressDialog.totalUAVs / 2 ? "white" : "#333333"
                    }
                }
            }
        }
    }
    END OF OLD UPLOAD PROGRESS DIALOG */
    
    /* OLD UPLOAD RESULT DIALOG - REPLACED BY MissionUploadSummaryDialog
    // Upload Mission Result Dialog
    Dialog {
        id: uploadMissionResultDialog
        title: "Upload Mission"
        width: 450
        height: 250
        modal: true
        anchors.centerIn: parent
        
        property string message: ""
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 0  // Rectangular corners
        }
        
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onReturnPressed: uploadMissionResultDialog.accept()
            Keys.onEnterPressed: uploadMissionResultDialog.accept()
            Keys.onEscapePressed: uploadMissionResultDialog.reject()
            
            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 20
                
                Text {
                    text: uploadMissionResultDialog.message
                    font.pointSize: 10
                    width: parent.width - 20
                    wrapMode: Text.WordWrap
                }
                
                Row {
                    spacing: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Button {
                        text: "OK"
                        width: 100
                        height: 35
                        background: Rectangle {
                            color: parent.pressed ? "#005a9e" : (parent.hovered ? "#0078d4" : "#0078d4")
                            border.color: "#707070"
                            border.width: 1
                            radius: 0  // Rectangular
                        }
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: "white"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: uploadMissionResultDialog.accept()
                    }
                }
            }
        }
    }
    END OF OLD UPLOAD RESULT DIALOG */
    
    // Mission Upload Window
    MissionUpload {
        id: missionUploadWindow
    }
    
    // Listen for upload progress updates
    Connections {
        target: backend
        function onMission_upload_progress(uavId, statusMessage, progressPercent) {
            console.log("Upload progress for", uavId, ":", statusMessage, "-", progressPercent + "%")
            missionUploadWindow.updateProgress(uavId, statusMessage, progressPercent)
        }
    }
    
    // Listen for upload completion
    Connections {
        target: backend
        function onMission_upload_result(uavId, success, message) {
            console.log("✓ Upload completed for", uavId, ":", success, "-", message)
            missionUploadWindow.setComplete(uavId, success, message)
        }
    }
}




