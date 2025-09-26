import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: missionEditor
    width: 800
    height: 600
    color: "#f0f0f0"

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        padding: 20

        Text {
            text: "Mission Editor"
            font.pointSize: 24
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
        }

        RowLayout {
            spacing: 10

            TextField {
                id: latitudeField
                placeholderText: "Latitude"
                width: 200
            }

            TextField {
                id: longitudeField
                placeholderText: "Longitude"
                width: 200
            }

            TextField {
                id: altitudeField
                placeholderText: "Altitude"
                width: 200
            }

            TextField {
                id: holdTimeField
                placeholderText: "Hold Time (s)"
                width: 200
            }
        }

        Button {
            text: "Add Waypoint"
            onClicked: {
                // Logic to add waypoint
            }
        }

        ListView {
            id: waypointList
            width: parent.width
            height: 300
            model: ListModel {
                // Model for waypoints
            }
            delegate: Item {
                width: waypointList.width
                height: 40
                Text {
                    text: "Waypoint: " + model.latitude + ", " + model.longitude
                }
            }
        }

        Button {
            text: "Save Mission"
            onClicked: {
                // Logic to save mission
            }
        }
    }
}