import QtQuick 2.15
import QtLocation 5.15
import QtPositioning 5.15

Map {
    id: mapView
    anchors.fill: parent
    
    plugin: Plugin {
        name: "osm" // OpenStreetMap plugin
    }

    // Default center - will be updated when UAV connects
    center: QtPositioning.coordinate(37.7749, -122.4194)
    zoomLevel: 15
    
    property var currentUAV: "UAV_1"
    property var uavPosition: QtPositioning.coordinate(0, 0)
    
    // Timer to update map data
    Timer {
        id: mapUpdateTimer
        interval: 1000  // Update every second
        running: true
        repeat: true
        onTriggered: {
            updateUAVPosition()
        }
    }
    
    // UAV marker
    MapQuickItem {
        id: uavMarker
        coordinate: uavPosition
        visible: uavPosition.isValid && uavPosition.latitude !== 0
        
        sourceItem: Rectangle {
            width: 24
            height: 24
            radius: 12
            color: getUAVMarkerColor()
            border.color: "white"
            border.width: 2
            
            // UAV heading indicator
            Rectangle {
                width: 3
                height: 12
                color: "white"
                anchors.centerIn: parent
                transformOrigin: Item.Bottom
                rotation: getUAVHeading()
            }
            
            // Status indicator
            Rectangle {
                width: 8
                height: 8
                radius: 4
                color: getArmedState() === "ARMED" ? "red" : "green"
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: -2
                border.color: "white"
                border.width: 1
            }
        }
        
        // Click handler for UAV marker
        MouseArea {
            anchors.fill: parent
            onClicked: {
                showUAVInfo()
            }
        }
    }
    
    // Home/Launch position marker
    MapQuickItem {
        id: homeMarker
        coordinate: getHomePosition()
        visible: getHomePosition().isValid
        
        sourceItem: Rectangle {
            width: 16
            height: 16
            color: "green"
            border.color: "white"
            border.width: 2
            
            Text {
                text: "H"
                color: "white"
                font.bold: true
                font.pointSize: 8
                anchors.centerIn: parent
            }
        }
    }
    
    // Mission waypoints
    Repeater {
        model: getMissionWaypoints()
        
        MapQuickItem {
            coordinate: QtPositioning.coordinate(modelData.lat, modelData.lon)
            
            sourceItem: Rectangle {
                width: 12
                height: 12
                radius: 6
                color: "blue"
                border.color: "white"
                border.width: 1
                
                Text {
                    text: (index + 1).toString()
                    color: "white"
                    font.pointSize: 6
                    anchors.centerIn: parent
                }
            }
        }
    }
    
    // Mission path
    MapPolyline {
        path: getMissionPath()
        strokeColor: "blue"
        strokeWidth: 2
        strokeStyle: "DashLine"
    }
    
    // UAV flight path (breadcrumb trail)
    MapPolyline {
        path: getFlightPath()
        strokeColor: getUAVPathColor()
        strokeWidth: 3
    }
    
    // Map controls
    Column {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 5
        
        Button {
            text: "Center on UAV"
            width: 100
            enabled: uavPosition.isValid
            onClicked: centerOnUAV()
        }
        
        Button {
            text: "Zoom In"
            width: 100
            onClicked: mapView.zoomLevel += 1
        }
        
        Button {
            text: "Zoom Out"
            width: 100
            onClicked: mapView.zoomLevel -= 1
        }
        
        Button {
            text: "Clear Path"
            width: 100
            onClicked: clearFlightPath()
        }
    }
    
    // Map info overlay
    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 10
        width: 200
        height: 80
        color: "white"
        opacity: 0.9
        border.color: "#ccc"
        radius: 5
        
        Column {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 3
            
            Text {
                text: "Map Information"
                font.bold: true
                font.pointSize: 10
            }
            
            Text {
                text: "Zoom: " + mapView.zoomLevel.toFixed(1)
                font.pointSize: 9
            }
            
            Text {
                text: "UAV Alt: " + getUAVAltitude().toFixed(1) + "m"
                font.pointSize: 9
            }
            
            Text {
                text: "Speed: " + getUAVSpeed().toFixed(1) + " m/s"
                font.pointSize: 9
            }
        }
    }
    
    // Functions to interact with backend
    function updateUAVPosition() {
        if (backend) {
            try {
                var status = backend.get_uav_status(currentUAV)
                if (status && status.position) {
                    var newPos = QtPositioning.coordinate(
                        status.position.latitude || 0,
                        status.position.longitude || 0
                    )
                    if (newPos.isValid && newPos.latitude !== 0) {
                        uavPosition = newPos
                        
                        // Auto-center on first valid position
                        if (mapView.center.latitude === 37.7749) {
                            mapView.center = newPos
                        }
                    }
                }
            } catch(e) {
                console.log("Error updating UAV position:", e)
            }
        }
    }
    
    function getUAVMarkerColor() {
        if (!backend) return "gray"
        try {
            var status = backend.get_uav_status(currentUAV)
            if (!status) return "gray"
            
            var mode = status.flight_status ? status.flight_status.flight_mode : "UNKNOWN"
            var armed = status.flight_status ? status.flight_status.armed : false
            
            if (armed) {
                if (mode === "AUTO") return "blue"
                if (mode === "GUIDED") return "purple"
                if (mode === "RTL") return "orange"
                return "red"  // Armed but other mode
            }
            return "green"  // Disarmed
        } catch(e) {
            return "gray"
        }
    }
    
    function getUAVPathColor() {
        var armed = getArmedState() === "ARMED"
        return armed ? "red" : "green"
    }
    
    function getUAVHeading() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.attitude ? status.attitude.yaw * 180 / Math.PI : 0
        } catch(e) {
            return 0
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
    
    function getHomePosition() {
        if (!backend) return QtPositioning.coordinate(0, 0)
        try {
            var status = backend.get_uav_status(currentUAV)
            if (status && status.home_position) {
                return QtPositioning.coordinate(
                    status.home_position.latitude || 0,
                    status.home_position.longitude || 0
                )
            }
            return QtPositioning.coordinate(0, 0)
        } catch(e) {
            return QtPositioning.coordinate(0, 0)
        }
    }
    
    function getUAVAltitude() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.position ? status.position.altitude_msl || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getUAVSpeed() {
        if (!backend) return 0
        try {
            var status = backend.get_uav_status(currentUAV)
            return status && status.position ? status.position.ground_speed || 0 : 0
        } catch(e) {
            return 0
        }
    }
    
    function getMissionWaypoints() {
        // Return array of waypoint objects with lat/lon
        if (!backend) return []
        try {
            var missionStatus = backend.get_mission_status(currentUAV)
            return missionStatus && missionStatus.waypoints ? missionStatus.waypoints : []
        } catch(e) {
            return []
        }
    }
    
    function getMissionPath() {
        var waypoints = getMissionWaypoints()
        var path = []
        for (var i = 0; i < waypoints.length; i++) {
            path.push(QtPositioning.coordinate(waypoints[i].lat, waypoints[i].lon))
        }
        return path
    }
    
    function getFlightPath() {
        // This would need to be implemented to track UAV breadcrumb trail
        // For now, return empty path
        return []
    }
    
    function centerOnUAV() {
        if (uavPosition.isValid) {
            mapView.center = uavPosition
        }
    }
    
    function showUAVInfo() {
        console.log("UAV marker clicked - showing info for:", currentUAV)
        // Could open a popup with detailed UAV information
    }
    
    function clearFlightPath() {
        console.log("Clear flight path requested")
        // Implementation would clear the breadcrumb trail
    }
}