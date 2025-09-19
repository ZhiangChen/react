import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1024
    height: 768
    title: "REACT - Ground Control Station"

    MenuBar {
        Menu {
            title: "File"
            Action {
                text: "Exit"
                onTriggered: Qt.quit()
            }
        }
        Menu {
            title: "Edit"
            Action {
                text: "Settings"
                // Placeholder for settings dialog action
            }
        }
    }

    RowLayout {
        anchors.fill: parent

        MapView {
            id: mapView
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        UAVList {
            id: uavList
            Layout.preferredWidth: 300
            Layout.fillHeight: true
        }
    }

    StatusBar {
        id: statusBar
        Text {
            text: "Ready"
        }
    }
}