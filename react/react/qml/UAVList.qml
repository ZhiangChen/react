import QtQuick 2.15
import QtQuick.Controls 2.15

ListView {
    id: uavListView
    width: parent.width
    height: parent.height

    model: ListModel {
        // Example UAV data
        ListElement { name: "UAV 1"; battery: "80%"; gps: "Lat: 34.0522, Lon: -118.2437"; mode: "Auto" }
        ListElement { name: "UAV 2"; battery: "65%"; gps: "Lat: 34.0522, Lon: -118.2437"; mode: "Manual" }
    }

    delegate: Item {
        width: uavListView.width
        height: 50

        Row {
            spacing: 10
            anchors.verticalCenter: parent.verticalCenter

            Text { text: model.name; font.bold: true }
            Text { text: model.battery }
            Text { text: model.gps }
            Text { text: model.mode }
        }
    }
}