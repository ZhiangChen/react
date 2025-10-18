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
    
    // Track last known home positions to avoid redundant updates
    property var lastHomePositions: ({})
    
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
        signal launchLocationChanged(string uavId, real lat, real lon)  // New signal for launch locations
        signal gcsHomePositionChanged(real lat, real lon)  // New signal for GCS home position
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
        
        function setGCSHome(latitude, longitude) {
            console.log("Set GCS home from web:", latitude, longitude)
            if (backend) {
                backend.setGCSHomePosition(latitude, longitude, 0.0)
            }
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
        running: false  // Don't start until map is ready
        repeat: true
        
        onTriggered: {
            updateUAVData()
        }
    }
    
    // Connect to telemetry updates to catch home position changes immediately
    Connections {
        target: backend
        function onTelemetryChanged(uavId, telemetryData) {
            // Check if home position is in the telemetry data and is valid
            if (telemetryData && telemetryData.home_position) {
                var home = telemetryData.home_position
                if (home.latitude !== 0 || home.longitude !== 0) {
                    // Check if this is a new/changed home position
                    var lastHome = lastHomePositions[uavId]
                    var hasChanged = !lastHome || 
                                   lastHome.latitude !== home.latitude || 
                                   lastHome.longitude !== home.longitude
                    
                    if (hasChanged) {
                        console.log("QML: Home position changed for", uavId, "- emitting launchLocationChanged")
                        mapBridge.launchLocationChanged(uavId, home.latitude, home.longitude)
                        
                        // Update cached home position
                        lastHomePositions[uavId] = {
                            latitude: home.latitude,
                            longitude: home.longitude
                        }
                    }
                }
            }
        }
    }
    
    // Functions to interact with the map
    function updateUAVData() {
        // Get UAV data from backend
        if (typeof backend !== 'undefined') {
            try {
                // Get all UAVs and update their positions
                var allUAVs = backend.getAllUAVs()
                if (allUAVs && allUAVs.length > 0) {
                    for (var i = 0; i < allUAVs.length; i++) {
                        var uavData = allUAVs[i]
                        var uavId = uavData.uav_id
                        
                        // Check if position is valid
                        if (uavData.position && uavData.position.latitude !== 0 && uavData.gps && uavData.gps.fix_type >= 2) {
                            var heading = uavData.attitude ? (uavData.attitude.heading || 0) : 0
                            var mode = uavData.flight_status ? (uavData.flight_status.mode || "UNKNOWN") : "UNKNOWN"
                            var armed = uavData.flight_status ? (uavData.flight_status.armed || false) : false
                            
                            // Send to web map
                            mapBridge.uavPositionChanged(
                                uavId, 
                                uavData.position.latitude, 
                                uavData.position.longitude, 
                                heading, 
                                mode, 
                                armed
                            )
                        }
                        
                        // Update launch location for each UAV (when home position is set)
                        var home = backend.getHomePosition(uavId)
                        if (home && home.isValid) {
                            // Check if this is a new/changed home position (same logic as Connections block)
                            var lastHome = lastHomePositions[uavId]
                            var hasChanged = !lastHome || 
                                           lastHome.latitude !== home.latitude || 
                                           lastHome.longitude !== home.longitude
                            
                            if (hasChanged) {
                                console.log("QML: Emitting launchLocationChanged for", uavId, "at", home.latitude, home.longitude)
                                mapBridge.launchLocationChanged(uavId, home.latitude, home.longitude)
                                
                                // Update cached home position
                                lastHomePositions[uavId] = {
                                    latitude: home.latitude,
                                    longitude: home.longitude
                                }
                            }
                        }
                    }
                }
                
                // Update waypoints for current UAV
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
                
                // Update GCS home position
                var gcsHome = backend.getGCSHomePosition()
                if (gcsHome && gcsHome.isValid) {
                    mapBridge.gcsHomePositionChanged(gcsHome.latitude, gcsHome.longitude)
                }
                
            } catch (e) {
                // Backend methods not available - use test data
                console.log("Backend not available, using test data")
            }
        }
    }
    
    // Functions to control the map
    function centerOnUAV(uavId) {
        if (!uavId) uavId = currentUAV
        webView.runJavaScript("centerOnUAV('" + uavId + "')")
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
            
            // Clear the cache so launch circles will be emitted
            lastHomePositions = {}
            
            // Start the timer now that map is ready
            updateTimer.running = true
            
            // Immediately update UAV data to show launch circles
            updateUAVData()
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