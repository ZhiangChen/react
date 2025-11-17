import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

Window {
    id: missionPlannerWindow
    title: "Mission Planner Tools"
    width: 320
    height: 600
    minimumWidth: 320
    minimumHeight: 550
    maximumWidth: 320
    maximumHeight: 650
    flags: Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowSystemMenuHint
    modality: Qt.NonModal

    // Reference to the map view (set from MainWindow)
    property var mapView: null
    
    // List model for polygons (each polygon has its own tab)
    ListModel {
        id: polygonListModel
        // Each item will have: polygonId, polygonName, polygonPoints, polygonArea
    }
    
    property int nextPolygonId: 1
    property int currentDrawingPolygonId: 0  // Track which polygon is currently being drawn
    
    // Store flight planning settings for each polygon
    property var polygonFlightSettings: ({})
    
    // Update flight settings for a specific polygon
    function updatePolygonFlightSetting(polygonId, settingName, value) {
        if (!polygonFlightSettings[polygonId]) {
            polygonFlightSettings[polygonId] = {}
        }
        polygonFlightSettings[polygonId][settingName] = value
        console.log("Updated polygon", polygonId, settingName, "to", value)
    }
    
    // Get flight settings for a specific polygon
    function getPolygonFlightSettings(polygonId) {
        return polygonFlightSettings[polygonId] || {
            pattern: "lawnmower",
            numFlights: 1,
            altitude: 50,
            speed: 5,
            forwardOverlap: 70,
            lateralOverlap: 70,
            angle: 0
        }
    }
    
    // Center the window on screen when opened
    Component.onCompleted: {
        x = (Screen.width - width) / 2
        y = (Screen.height - height) / 2
    }

    Rectangle {
        anchors.fill: parent
        color: "#f8f8f8"
        border.color: "#ddd"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            // Area of Interest Section
            GroupBox {
                title: "Area of Interest"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300
                Layout.fillWidth: true

                RowLayout {
                    width: 280
                    spacing: 5

                    Button {
                        text: "Draw Polygon"
                        Layout.preferredWidth: 135
                        background: Rectangle {
                            color: parent.hovered ? "#e3f2fd" : "#f5f5f5"
                            border.color: "#2196F3"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#1976D2"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            console.log("Draw Polygon tool activated")
                            if (mapView) {
                                // Pass the next polygon ID to the drawing function and track it
                                currentDrawingPolygonId = nextPolygonId
                                mapView.startDrawingPolygon(currentDrawingPolygonId)
                            } else {
                                console.error("Map view not available")
                            }
                        }
                    }

                    Button {
                        text: "Clear Selected"
                        Layout.preferredWidth: 135
                        enabled: polygonTabBar.count > 0
                        background: Rectangle {
                            color: parent.enabled ? (parent.hovered ? "#ffebee" : "#f5f5f5") : "#eeeeee"
                            border.color: parent.enabled ? "#f44336" : "#cccccc"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.enabled ? "#d32f2f" : "#999999"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            if (polygonTabBar.currentIndex >= 0 && polygonTabBar.currentIndex < polygonListModel.count) {
                                var polygonId = polygonListModel.get(polygonTabBar.currentIndex).polygonId
                                console.log("Clearing polygon", polygonId)
                                
                                // Clear polygon from map
                                if (mapView) {
                                    mapView.clearPolygonById(polygonId)
                                }
                                
                                // Remove from list
                                polygonListModel.remove(polygonTabBar.currentIndex)
                                
                                // Adjust current index if needed
                                if (polygonTabBar.currentIndex >= polygonListModel.count) {
                                    polygonTabBar.currentIndex = polygonListModel.count - 1
                                }
                            }
                        }
                    }
                }
            }

            // Polygon Tabs Section
            GroupBox {
                title: "Polygons"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300
                Layout.fillWidth: true
                Layout.preferredHeight: 450
                Layout.maximumHeight: 450

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 5

                    // Tab Bar for polygons
                    TabBar {
                        id: polygonTabBar
                        Layout.fillWidth: true
                        Layout.preferredHeight: polygonListModel.count > 0 ? 35 : 0
                        visible: polygonListModel.count > 0

                        Repeater {
                            model: polygonListModel
                            TabButton {
                                text: model.polygonName
                                width: implicitWidth
                            }
                        }
                    }

                    // Stack Layout for polygon content
                    StackLayout {
                        id: polygonStackLayout
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: polygonTabBar.currentIndex
                        visible: polygonListModel.count > 0

                        // Polygon details repeater
                        Repeater {
                            model: polygonListModel
                            
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                
                                ScrollView {
                                    anchors.fill: parent
                                    contentWidth: availableWidth
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                    
                                    ColumnLayout {
                                        width: parent.parent.width - 20
                                        spacing: 10
                                        
                                        // Flight Planning Section
                                        GroupBox {
                                            title: "Flight Planning"
                                            Layout.fillWidth: true
                                            
                                            ColumnLayout {
                                                width: parent.width - 20
                                                spacing: 10
                                                
                                                // Pattern Selection
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Pattern:"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 3
                                                        
                                                        ButtonGroup {
                                                            id: patternButtonGroup
                                                        }
                                                        
                                                        RadioButton {
                                                            id: lawnmowerButton
                                                            text: "Lawnmower"
                                                            checked: true
                                                            ButtonGroup.group: patternButtonGroup
                                                            font.pointSize: 8
                                                            
                                                            property int polygonId: model.polygonId
                                                            
                                                            onCheckedChanged: {
                                                                if (checked) {
                                                                    updatePolygonFlightSetting(polygonId, "pattern", "lawnmower")
                                                                }
                                                            }
                                                        }
                                                        
                                                        RadioButton {
                                                            id: gridButton
                                                            text: "Grid"
                                                            ButtonGroup.group: patternButtonGroup
                                                            font.pointSize: 8
                                                            
                                                            property int polygonId: model.polygonId
                                                            
                                                            onCheckedChanged: {
                                                                if (checked) {
                                                                    updatePolygonFlightSetting(polygonId, "pattern", "grid")
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                                
                                                // Number of Flights
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "# Flights:"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: numFlightsSpinBox
                                                        from: 1
                                                        to: 10
                                                        value: 1
                                                        stepSize: 1
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "numFlights", value)
                                                        }
                                                    }
                                                }
                                                
                                                // Altitude
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Altitude (m):"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: altitudeSpinBox
                                                        from: 10
                                                        to: 500
                                                        value: 50
                                                        stepSize: 5
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "altitude", value)
                                                            // Update altitude in map for GSD calculation
                                                            mapView.updatePolygonAltitude(polygonId, value)
                                                        }
                                                    }
                                                }
                                                
                                                // Speed
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Speed (m/s):"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: speedSpinBox
                                                        from: 1
                                                        to: 20
                                                        value: 5
                                                        stepSize: 1
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "speed", value)
                                                        }
                                                    }
                                                }
                                                
                                                // Forward Overlap
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Fwd Overlap (%):"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: forwardOverlapSpinBox
                                                        from: 0
                                                        to: 90
                                                        value: 70
                                                        stepSize: 5
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "forwardOverlap", value)
                                                        }
                                                    }
                                                }
                                                
                                                // Lateral Overlap
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Lat Overlap (%):"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: lateralOverlapSpinBox
                                                        from: 0
                                                        to: 90
                                                        value: 70
                                                        stepSize: 5
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "lateralOverlap", value)
                                                        }
                                                    }
                                                }
                                                
                                                // Angle
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 5
                                                    
                                                    Label {
                                                        text: "Angle (°):"
                                                        font.pointSize: 8
                                                        Layout.preferredWidth: 80
                                                    }
                                                    SpinBox {
                                                        id: angleSpinBox
                                                        from: 0
                                                        to: 180
                                                        value: 0
                                                        stepSize: 5
                                                        editable: true
                                                        Layout.fillWidth: true
                                                        
                                                        property int polygonId: model.polygonId
                                                        
                                                        onValueChanged: {
                                                            updatePolygonFlightSetting(polygonId, "angle", value)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Default view when no polygons
                    Text {
                        anchors.centerIn: parent
                        text: "No polygons created yet.\n\nClick 'Draw Polygon' to start."
                        horizontalAlignment: Text.AlignHCenter
                        color: "#666666"
                        font.pointSize: 9
                        visible: polygonListModel.count === 0
                    }
                }
            }
            
            // Generate Mission Button (outside polygons section, applies to all)
            Button {
                text: "Generate Mission"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                enabled: polygonListModel.count > 0
                
                background: Rectangle {
                    color: parent.enabled ? (parent.hovered ? "#4CAF50" : "#66BB6A") : "#cccccc"
                    border.color: parent.enabled ? "#4CAF50" : "#999999"
                    border.width: 1
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: "white"
                    font.pointSize: 10
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    console.log("Generate mission for all", polygonListModel.count, "polygons")
                    // TODO: Implement mission generation for all polygons
                    // Can access polygonListModel for polygon data
                    // Can access polygonFlightSettings for each polygon's settings
                }
            }
        }
    }

    FileDialog {
        id: missionSaveDialog
        title: "Save Mission Files"
        nameFilters: ["Mission files (*.mission)", "Waypoint files (*.waypoints)", "All files (*)"]
        onAccepted: {
            console.log("Save missions to:", selectedFile)
            // TODO: Save generated mission files
        }
    }

    // Connections to handle polygon completion from map
    Connections {
        target: mapView
        function onPolygonCompleted(points) {
            console.log("MissionPlanner: Polygon completed with", points.length, "points")
            
            // Use the ID that was set when drawing started
            var polygonId = currentDrawingPolygonId
            if (polygonId === 0) {
                console.error("No polygon ID was set before drawing!")
                polygonId = nextPolygonId
            }
            
            // Calculate approximate area
            var area = calculatePolygonArea(points)
            
            // Add new polygon to the list
            polygonListModel.append({
                polygonId: polygonId,
                polygonName: "Polygon " + polygonId,
                polygonPoints: points,
                polygonArea: area
            })
            
            // Initialize flight settings for this polygon with defaults
            polygonFlightSettings[polygonId] = {
                pattern: "lawnmower",
                numFlights: 1,
                altitude: 50,
                speed: 5,
                forwardOverlap: 70,
                lateralOverlap: 70,
                angle: 0
            }
            
            // Switch to the new tab
            polygonTabBar.currentIndex = polygonListModel.count - 1
            
            // Increment nextPolygonId for the next polygon
            nextPolygonId++
            
            // Reset current drawing ID
            currentDrawingPolygonId = 0
        }
        
        function onPolygonUpdated(polygonId, points) {
            console.log("MissionPlanner: Polygon", polygonId, "updated with", points.length, "points")
            
            // Find the polygon in the list model
            for (var i = 0; i < polygonListModel.count; i++) {
                if (polygonListModel.get(i).polygonId === polygonId) {
                    // Calculate new area
                    var area = calculatePolygonArea(points)
                    
                    // Update the polygon data
                    polygonListModel.setProperty(i, "polygonPoints", points)
                    polygonListModel.setProperty(i, "polygonArea", area)
                    
                    console.log("Updated polygon", polygonId, "- new area:", area.toFixed(3), "km²")
                    break
                }
            }
        }
    }
    
    // Helper function to calculate polygon area
    function calculatePolygonArea(points) {
        if (points.length < 3) return 0
        
        var toRad = Math.PI / 180
        var R = 6371 // Earth's radius in km
        
        var area = 0
        var n = points.length
        
        for (var i = 0; i < n; i++) {
            var p1 = points[i]
            var p2 = points[(i + 1) % n]
            
            var lat1 = p1.lat * toRad
            var lat2 = p2.lat * toRad
            var dLon = (p2.lon - p1.lon) * toRad
            
            area += dLon * (2 + Math.sin(lat1) + Math.sin(lat2))
        }
        
        area = Math.abs(area * R * R / 2)
        return area
    }

    // Handle window close
    onClosing: {
        console.log("Mission Planner window closed")
    }
}