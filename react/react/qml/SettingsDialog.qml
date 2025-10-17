import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: settingsDialog
    title: "Settings"
    modal: true

    background: Rectangle {
        color: "white"
        border.color: "#cccccc"
        border.width: 1
        radius: 0  // Rectangular corners
    }

    contentItem: ColumnLayout {
        spacing: 10

        TextField {
            id: apiKeyField
            placeholderText: "Enter API Key"
            Layout.fillWidth: true
        }

        TextField {
            id: telemetryPortField
            placeholderText: "Enter Telemetry Port"
            Layout.fillWidth: true
        }

        TextField {
            id: tileServerField
            placeholderText: "Enter Tile Server URL"
            Layout.fillWidth: true
        }

        // Additional settings fields can be added here

        RowLayout {
            spacing: 10
            Layout.alignment: Qt.AlignRight
            Layout.topMargin: 10
            
            Button {
                text: "Cancel"
                Layout.preferredWidth: 80
                onClicked: settingsDialog.reject()
                
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
                text: "Save"
                Layout.preferredWidth: 80
                onClicked: {
                    // Logic to save settings goes here
                    settingsDialog.accept()
                }
                
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