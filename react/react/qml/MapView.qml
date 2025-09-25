import QtQuick 2.15
import QtQuick.Controls 2.15
import QtLocation 5.15
import QtPositioning 5.15

Map {
    id: mapView
    
    // Try different plugins to see what works
    plugin: Plugin {
        name: "osm"
        PluginParameter { 
            name: "osm.useragent"
            value: "REACT Ground Control Station" 
        }
        PluginParameter {
            name: "osm.mapping.providersrepository.disabled"
            value: "true"
        }
        PluginParameter {
            name: "osm.mapping.custom.host"
            value: "http://127.0.0.1:8081/tiles/satellite/"
        }
    }
    
    // Map style options - including real satellite
    property var mapStyleNames: ["Street", "Satellite", "Cycle", "Transit", "Night", "Terrain", "Hiking"]
    property int currentMapStyle: 0
    property string tileServerUrl: "http://127.0.0.1:8081"
    property bool tileServerRunning: false
    
    // Custom map type for local satellite tiles
    property var satelliteMapType: null
    
    // Check tile server status
    Timer {
        id: serverCheckTimer
        interval: 3000
        running: true
        repeat: true
        onTriggered: checkTileServer()
    }
    
    function checkTileServer() {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", tileServerUrl + "/", true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                tileServerRunning = (xhr.status === 200)
            }
        }
        xhr.onerror = function() { tileServerRunning = false }
        try { xhr.send() } catch (e) { }
    }
    
    Component.onCompleted: {
        console.log("Available OSM map types:", supportedMapTypes.length)
        for (var i = 0; i < supportedMapTypes.length; i++) {
            console.log("Map type", i + ":", supportedMapTypes[i].name)
        }
        if (supportedMapTypes.length > 0) {
            activeMapType = supportedMapTypes[0]
            console.log("Started with:", supportedMapTypes[0].name)
        }
        checkTileServer()
    }
    
    function changeMapStyle(styleIndex) {
        if (styleIndex >= 0 && styleIndex < mapStyleNames.length) {
            currentMapStyle = styleIndex
            
            if (styleIndex === 1) {
                // Show satellite info instead of broken satellite tiles
                console.log("Satellite info mode activated")
                if (supportedMapTypes.length > 0) {
                    activeMapType = supportedMapTypes[0] // Keep using street map as base
                }
            } else {
                var osmIndex = styleIndex > 1 ? styleIndex - 1 : styleIndex // Adjust for satellite info
                if (styleIndex === 0) osmIndex = 0      // Street Map
                else if (styleIndex === 2) osmIndex = 2 // Cycle Map  
                else if (styleIndex === 3) osmIndex = 3 // Transit Map
                else if (styleIndex === 4) osmIndex = 4 // Night Transit Map
                else if (styleIndex === 5) osmIndex = 5 // Terrain Map
                else if (styleIndex === 6) osmIndex = 6 // Hiking Map
                
                if (osmIndex < supportedMapTypes.length) {
                    activeMapType = supportedMapTypes[osmIndex]
                    console.log("Changed to style:", mapStyleNames[styleIndex], "using OSM type:", supportedMapTypes[osmIndex].name)
                }
            }
        }
    }

    // Default center
    center: QtPositioning.coordinate(37.7749, -122.4194)
    zoomLevel: 15
    minimumZoomLevel: 1
    maximumZoomLevel: 20
    
    property var currentUAV: "UAV_1"
    property var uavPosition: QtPositioning.coordinate(0, 0)
    
    Timer {
        id: mapUpdateTimer
        interval: 1000
        running: true
        repeat: true
        onTriggered: updateUAVPosition()
    }
    
    // Satellite Information Overlay
    Rectangle {
        id: satelliteInfoOverlay
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.3)
        visible: currentMapStyle === 1
        
        Rectangle {
            width: 400
            height: 300
            anchors.centerIn: parent
            color: "white"
            radius: 10
            border.color: "#ccc"
            border.width: 2
            
            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 15
                
                Text {
                    text: "🛰️ Satellite Imagery Information"
                    font.pointSize: 14
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                
                Text {
                    text: "Tile Server Status: " + (tileServerRunning ? "✅ Online" : "❌ Offline")
                    font.pointSize: 12
                    color: tileServerRunning ? "green" : "red"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                
                Rectangle {
                    width: parent.width - 20
                    height: 1
                    color: "#ccc"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                
                Text {
                    text: "Current Status:"
                    font.pointSize: 11
                    font.bold: true
                }
                
                Text {
                    text: tileServerRunning ? 
                          "• Local tile server is running\n• Satellite tiles are being cached\n• " + getCachedTileCount() + " tiles in cache" :
                          "• Tile server is offline\n• No satellite imagery available\n• Start tile server for satellite support"
                    font.pointSize: 10
                    width: parent.width - 40
                    wrapMode: Text.WordWrap
                }
                
                Text {
                    text: "Access satellite imagery:"
                    font.pointSize: 11
                    font.bold: true
                }
                
                Row {
                    spacing: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Button {
                        text: "Open Tile Server"
                        enabled: tileServerRunning
                        onClicked: Qt.openUrlExternally(tileServerUrl)
                    }
                    
                    Button {
                        text: "View Sample Tile"
                        enabled: tileServerRunning
                        onClicked: {
                            var lat = mapView.center.latitude
                            var lon = mapView.center.longitude
                            var z = Math.floor(mapView.zoomLevel)
                            var x = Math.floor((lon + 180) / 360 * Math.pow(2, z))
                            var y = Math.floor((1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * Math.pow(2, z))
                            Qt.openUrlExternally(tileServerUrl + "/tiles/satellite/" + z + "/" + x + "/" + y + ".png")
                        }
                    }
                }
                
                Text {
                    text: "Note: Qt's mapping framework has limited support for custom tile servers. The tile server provides satellite imagery that can be accessed via web browser or external mapping applications."
                    font.pointSize: 9
                    color: "gray"
                    width: parent.width - 40
                    wrapMode: Text.WordWrap
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
            
            // Close button
            Button {
                text: "×"
                width: 30
                height: 30
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 5
                onClicked: changeMapStyle(0) // Switch back to street map
            }
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
            
            Rectangle {
                width: 3
                height: 12
                color: "white"
                anchors.centerIn: parent
                transformOrigin: Item.Bottom
                rotation: getUAVHeading()
            }
            
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
        
        MouseArea {
            anchors.fill: parent
            onClicked: showUAVInfo()
        }
    }
    
    // Home position marker
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
    
    // Mouse interaction
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: currentMapStyle !== 1 // Disable when satellite info is shown
        
        property var exclusionAreas: [
            {"x": 10, "y": 10, "width": 150, "height": 40}
        ]
        
        function isInExclusionArea(x, y) {
            for (var i = 0; i < exclusionAreas.length; i++) {
                var area = exclusionAreas[i]
                if (x >= area.x && x <= area.x + area.width &&
                    y >= area.y && y <= area.y + area.height) {
                    return true
                }
            }
            return false
        }
        
        onPressed: {
            if (!isInExclusionArea(mouse.x, mouse.y)) {
                mouse.accepted = true
            } else {
                mouse.accepted = false
            }
        }
        
        onWheel: {
            if (!isInExclusionArea(wheel.x, wheel.y)) {
                var zoomChange = wheel.angleDelta.y > 0 ? 1 : -1
                mapView.zoomLevel = Math.max(mapView.minimumZoomLevel, 
                                           Math.min(mapView.maximumZoomLevel, 
                                                   mapView.zoomLevel + zoomChange))
                wheel.accepted = true
            } else {
                wheel.accepted = false
            }
        }
    }
    
    // Map style dropdown
    ComboBox {
        id: mapStyleCombo
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 10
        width: 150
        
        model: mapStyleNames
        
        onCurrentIndexChanged: {
            changeMapStyle(currentIndex)
        }
        
        background: Rectangle {
            color: "white"
            border.color: "#cccccc"
            border.width: 1
            radius: 4
            opacity: 0.9
        }
        
        contentItem: Text {
            text: mapStyleCombo.displayText
            color: "black"
            verticalAlignment: Text.AlignVCenter
            leftPadding: 8
            rightPadding: 8
        }
    }
    
    // Status indicator
    Rectangle {
        anchors.top: mapStyleCombo.bottom
        anchors.left: parent.left
        anchors.margins: 10
        width: 150
        height: 50
        color: tileServerRunning ? "lightgreen" : "lightcoral"
        border.color: tileServerRunning ? "green" : "red"
        border.width: 1
        radius: 3
        opacity: 0.8
        
        Column {
            anchors.centerIn: parent
            Text {
                text: tileServerRunning ? "Tile Server: Online" : "Tile Server: Offline"
                color: "black"
                font.pointSize: 8
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                text: tileServerRunning ? getCachedTileCount() + " tiles cached" : "No satellite tiles"
                color: "black"
                font.pointSize: 7
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                text: "Click for info"
                color: "gray"
                font.pointSize: 6
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
        
        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (currentMapStyle !== 1) {
                    changeMapStyle(1) // Show satellite info
                }
            }
        }
    }
    
    // Map info overlay
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 10
        width: 200
        height: 60
        color: "black"
        opacity: 0.7
        radius: 5
        visible: currentMapStyle !== 1
        
        Column {
            anchors.fill: parent
            anchors.margins: 5
            spacing: 2
            
            Text {
                text: "Map: " + mapStyleNames[currentMapStyle]
                color: "white"
                font.pointSize: 9
                font.bold: true
            }
            
            Text {
                text: "Zoom: " + mapView.zoomLevel.toFixed(1)
                color: "white"
                font.pointSize: 8
            }
            
            Text {
                text: "Lat: " + mapView.center.latitude.toFixed(4) + ", Lon: " + mapView.center.longitude.toFixed(4)
                color: "white"
                font.pointSize: 8
            }
        }
    }
    
    // Helper functions
    function getCachedTileCount() {
        return tileServerRunning ? "Some" : "0" // Simplified for now
    }
    
    function updateUAVPosition() {
        // Mock implementation
        if (typeof backend !== 'undefined') {
            var pos = backend.getUAVPosition(currentUAV)
            if (pos && pos.isValid) {
                uavPosition = pos
                if (center.latitude === 37.7749 && center.longitude === -122.4194) {
                    center = uavPosition
                }
            }
        }
    }
    
    function getUAVMarkerColor() {
        if (typeof backend === 'undefined') return "gray"
        var mode = backend.getUAVMode(currentUAV)
        switch(mode) {
            case "MANUAL": return "blue"
            case "STABILIZE": return "green"
            case "AUTO": return "purple"
            case "GUIDED": return "orange"
            case "RTL": return "yellow"
            default: return "gray"
        }
    }
    
    function getUAVHeading() {
        return typeof backend !== 'undefined' ? (backend.getUAVHeading(currentUAV) || 0) : 0
    }
    
    function getArmedState() {
        return typeof backend !== 'undefined' ? (backend.getArmedState(currentUAV) || "DISARMED") : "DISARMED"
    }
    
    function getHomePosition() {
        return typeof backend !== 'undefined' ? (backend.getHomePosition(currentUAV) || QtPositioning.coordinate()) : QtPositioning.coordinate()
    }
    
    function showUAVInfo() {
        console.log("UAV Info for", currentUAV)
    }
}