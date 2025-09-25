import QtQuick 2.15
import QtQuick.Controls 2.15
import QtWebEngine 1.15
import QtWebChannel 1.15
import QtPositioning 5.15

Item {
    id: mapContainer
    
    // Properties for UAV data
    property var currentUAV: "UAV_1"
    property var uavPosition: QtPositioning.coordinate(0, 0)
    property var homePosition: QtPositioning.coordinate(0, 0)
    property var waypoints: []
    property var geofences: []
    
    // Map interaction signals
    signal uavSelected(string uavId)
    signal mapClicked(real latitude, real longitude)
    signal webMapReady()
    
    // WebChannel for Qt <-> JS communication
    WebChannel {
        id: webChannel
        registeredObjects: [mapBridge]
    }
    
    // Bridge object for communication with JavaScript
    QtObject {
        id: mapBridge
        
        // WebChannel ID required for registration
        WebChannel.id: "mapBridge"
        
        // Signals to send data to JavaScript
        signal uavPositionChanged(string uavId, real lat, real lon, real heading, string mode, bool armed)
        signal homePositionChanged(real lat, real lon)
        signal missionPathChanged(var waypoints)
        signal geofencesChanged(var geofences)
        
        // Slots to receive data from JavaScript
        function uavSelected(uavId) {
            console.log("UAV selected from web:", uavId)
            mapContainer.uavSelected(uavId)
        }
        
        function mapClicked(latitude, longitude) {
            console.log("Map clicked at:", latitude, longitude)
            mapContainer.mapClicked(latitude, longitude)
        }
        
        function webMapReady() {
            console.log("Web map is ready")
            mapContainer.webMapReady()
        }
    }
    
    // WebEngine View
    WebEngineView {
        id: webView
        anchors.fill: parent
        
        // Load from same HTTP origin - should resolve QtWebEngine security issues
        url: "http://127.0.0.1:8081/satellite_map.html"
        
        // Enable web channel
        webChannel: webChannel
        
        // Enable settings for dynamic tile loading
        settings.allowRunningInsecureContent: true
        settings.localContentCanAccessRemoteUrls: true
        settings.javascriptEnabled: true
        // settings.webSecurityEnabled: false (reverted due to crash)
        
        // Handle loading states
        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                console.log("Same-origin map loaded successfully from:", loadRequest.url)
            } else if (loadRequest.status === WebEngineView.LoadFailedStatus) {
                console.log("Failed to load same-origin map:", loadRequest.errorString)
            }
        }
        
        Component.onCompleted: {
            console.log("WebEngineView initialized for same-origin loading")
        }
    }
    
    // Timer to update UAV positions
    Timer {
        id: updateTimer
        interval: 1000
        running: true
        repeat: true
        
        onTriggered: {
            updateUAVData()
        }
    }
    
    // Functions to interact with the map
    function updateUAVData() {
        // Get UAV data from backend
        if (typeof backend !== 'undefined') {
            try {
                var position = backend.getUAVPosition(currentUAV)
                if (position && position.isValid && position.latitude !== 0) {
                    var heading = backend.getUAVHeading(currentUAV) || 0
                    var mode = backend.getUAVMode(currentUAV) || "UNKNOWN"
                    var armed = backend.getArmedState(currentUAV) === "ARMED"
                    
                    // Send to web map
                    mapBridge.uavPositionChanged(
                        currentUAV, 
                        position.latitude, 
                        position.longitude, 
                        heading, 
                        mode, 
                        armed
                    )
                }
                
                // Update home position
                var home = backend.getHomePosition(currentUAV)
                if (home && home.isValid && home.latitude !== 0) {
                    if (homePosition.latitude !== home.latitude || homePosition.longitude !== home.longitude) {
                        homePosition = home
                        mapBridge.homePositionChanged(home.latitude, home.longitude)
                    }
                }
                
                // Update waypoints
                var newWaypoints = backend.getWaypoints(currentUAV)
                if (newWaypoints && newWaypoints.length > 0) {
                    if (JSON.stringify(waypoints) !== JSON.stringify(newWaypoints)) {
                        waypoints = newWaypoints
                        mapBridge.missionPathChanged(waypoints)
                    }
                }
                
                // Update geofences
                var newGeofences = backend.getGeofences()
                if (newGeofences && newGeofences.length > 0) {
                    if (JSON.stringify(geofences) !== JSON.stringify(newGeofences)) {
                        geofences = newGeofences
                        mapBridge.geofencesChanged(geofences)
                    }
                }
                
            } catch (e) {
                // Backend methods not available - use test data
                console.log("Backend not available, using test data")
            }
        }
    }
    
    // Functions to control the map
    function centerOnUAV() {
        webView.runJavaScript("centerOnUAV()")
    }
    
    function fitAllUAVs() {
        webView.runJavaScript("fitAllUAVs()")
    }
    
    function changeMapType(mapType) {
        webView.runJavaScript("changeMapType('" + mapType + "')")
    }
    
    function setMapCenter(latitude, longitude, zoom) {
        webView.runJavaScript("map.setView([" + latitude + ", " + longitude + "], " + zoom + ")")
    }
    
    // Handle component initialization
    Component.onCompleted: {
        console.log("MapContainer initialized")
        
        // Connect to web map ready signal
        webMapReady.connect(function() {
            console.log("Web map ready, starting updates")
            // Send initial test data
            mapBridge.uavPositionChanged("UAV_1", 37.7849, -122.4094, 45, "AUTO", false)
            mapBridge.homePositionChanged(37.7749, -122.4194)
            
            var testWaypoints = [
                { lat: 37.7749, lon: -122.4194, type: "mission" },
                { lat: 37.7849, lon: -122.4094, type: "mission" },
                { lat: 37.7949, lon: -122.3994, type: "mission" }
            ]
            mapBridge.missionPathChanged(testWaypoints)
        })
    }
    
    // Handle map click events
    onMapClicked: {
        console.log("Map clicked in QML:", latitude, longitude)
        // Handle waypoint addition, etc.
    }
    
    // Handle UAV selection
    onUavSelected: {
        console.log("UAV selected in QML:", uavId)
        currentUAV = uavId
    }
}