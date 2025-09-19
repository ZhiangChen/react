import QtQuick 2.15
import QtLocation 5.15
import QtPositioning 5.15

Map {
    id: mapView
    anchors.fill: parent
    plugin: Plugin {
        name: "osm" // OpenStreetMap plugin
    }

    // Center the map on a specific location
    center: QtPositioning.coordinate(37.7749, -122.4194) // Example coordinates (San Francisco)
    zoomLevel: 12

    // Example of adding a marker for a UAV
    MapQuickItem {
        coordinate: QtPositioning.coordinate(37.7749, -122.4194) // UAV position
        sourceItem: Image {
            source: "qrc:/images/uav_icon.png" // Path to UAV icon
            width: 32
            height: 32
        }
    }

    // Example of adding a polyline for UAV path
    MapPolyline {
        path: [
            QtPositioning.coordinate(37.7749, -122.4194),
            QtPositioning.coordinate(37.7750, -122.4180),
            QtPositioning.coordinate(37.7760, -122.4170)
        ]
        strokeColor: "blue"
        strokeWidth: 2
    }

    // Example of adding a waypoint
    MapQuickItem {
        coordinate: QtPositioning.coordinate(37.7755, -122.4165) // Waypoint position
        sourceItem: Image {
            source: "qrc:/images/waypoint_icon.png" // Path to waypoint icon
            width: 24
            height: 24
        }
    }
}