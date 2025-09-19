import QtQuick 2.15
import QtQuick.Controls 2.15

Dialog {
    id: settingsDialog
    title: "Settings"
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    ColumnLayout {
        spacing: 10
        padding: 20

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

        Button {
            text: "Save"
            onClicked: {
                // Logic to save settings goes here
                settingsDialog.accept();
            }
        }
    }
}