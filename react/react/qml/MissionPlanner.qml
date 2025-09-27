import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

Window {
    id: missionPlannerWindow
    title: "Mission Planner Tools"
    width: 320
    height: 500
    minimumWidth: 320
    minimumHeight: 500
    maximumWidth: 320
    maximumHeight: 500
    flags: Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowSystemMenuHint
    modality: Qt.NonModal

    // Center the window on screen when opened
    Component.onCompleted: {
        x = (Screen.width - width) / 2
        y = (Screen.height - height) / 2
    }

    Rectangle {
        anchors.fill: parent
        color: "#f8f8f8"
        border.color: "#ddd"
        border.width: 1

        ScrollView {
            anchors.fill: parent
            contentWidth: width
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            // Area of Interest Section
            GroupBox {
                title: "Area of Interest"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300

                RowLayout {
                    width: 280
                    spacing: 5

                    Button {
                        text: "Draw Polygon"
                        Layout.preferredWidth: 135
                        background: Rectangle {
                            color: parent.hovered ? "#e3f2fd" : "#f5f5f5"
                            border.color: "#2196F3"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#1976D2"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            console.log("Draw Polygon tool activated")
                            // TODO: Activate polygon drawing mode on map
                        }
                    }

                    Button {
                        text: "Clear Area"
                        Layout.preferredWidth: 135
                        background: Rectangle {
                            color: parent.hovered ? "#ffebee" : "#f5f5f5"
                            border.color: "#f44336"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#d32f2f"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            console.log("Clear area of interest")
                            // TODO: Clear drawn polygon from map
                        }
                    }
                }
            }

            // Flight Planning Section
            GroupBox {
                title: "Flight Planning"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300

                ColumnLayout {
                    width: 280
                    spacing: 5

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Number of Flights:"
                            font.pointSize: 9
                        }
                        SpinBox {
                            id: flightCountSpinBox
                            from: 1
                            to: 10
                            value: 1
                            editable: true
                            Layout.preferredWidth: 80
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Altitude (m):"
                            font.pointSize: 9
                        }
                        SpinBox {
                            id: altitudeSpinBox
                            from: 10
                            to: 200
                            value: 30
                            editable: true
                            Layout.preferredWidth: 80
                        }
                        Text {
                            text: "GSD (cm):"
                            font.pointSize: 9
                            Layout.preferredWidth: 40
                        }
                        Text {
                            text: "N/A "
                            font.pointSize: 9
                            Layout.preferredWidth: 50
                            Layout.leftMargin: 10
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Front Overlap (%):"
                            font.pointSize: 9
                        }
                        SpinBox {
                            id: frontOverlapSpinBox
                            from: 0
                            to: 999
                            value: 75
                            editable: true
                            Layout.preferredWidth: 80
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Lateral Overlap (%):"
                            font.pointSize: 9
                        }
                        SpinBox {
                            id: lateralOverlapSpinBox
                            from: 0
                            to: 999
                            value: 75
                            editable: true
                            Layout.preferredWidth: 80
                        }
                    }

                    // Altitude slider with +/- buttons
                    RowLayout {
                        Layout.fillWidth: true // Re-enable fillWidth for consistent alignment
                        spacing: 5

                        Text {
                            text: "Orientation (°):"
                            font.pointSize: 9
                            Layout.preferredWidth: 80
                        }

                        Slider {
                            id: orientationSlider
                            from: 0
                            to: 360
                            value: 0
                            stepSize: 1
                            Layout.fillWidth: true
                        }

                        Text {
                            text: orientationSlider.value.toFixed(0) + "°"
                            font.pointSize: 9
                            Layout.preferredWidth: 35
                            horizontalAlignment: Text.AlignRight
                        }

                        Button {
                            text: "-"
                            font.bold: true
                            font.pointSize: 12
                            width: 20
                            implicitWidth: 20
                            Layout.maximumWidth: 20
                            Layout.minimumWidth: 20
                            height: 20
                            implicitHeight: 20
                            Layout.maximumHeight: 20
                            Layout.minimumHeight: 20
                            background: Rectangle {
                                color: parent.hovered ? "#ffebee" : "#f5f5f5"
                                border.color: "#f44336"
                                border.width: 1
                                radius: 3
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#d32f2f"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font: parent.font
                            }
                            onClicked: {
                                orientationSlider.value = Math.max(orientationSlider.from, orientationSlider.value - 1)
                            }
                        }

                        Button {
                            text: "+"
                            font.bold: true
                            font.pointSize: 12
                            width: 20
                            implicitWidth: 20
                            Layout.maximumWidth: 20
                            Layout.minimumWidth: 20
                            height: 20
                            implicitHeight: 20
                            Layout.maximumHeight: 20
                            Layout.minimumHeight: 20
                            background: Rectangle {
                                color: parent.hovered ? "#e8f5e8" : "#f5f5f5"
                                border.color: "#4CAF50"
                                border.width: 1
                                radius: 3
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#2E7D32"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font: parent.font
                            }
                            onClicked: {
                                orientationSlider.value = Math.min(orientationSlider.to, orientationSlider.value + 1)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        RadioButton {
                            text: "Lawnmower Pattern"
                            checked: true
                            ButtonGroup.group: patternButtonGroup
                            font.pointSize: 9
                        }

                        RadioButton {
                            text: "Grid Pattern"
                            ButtonGroup.group: patternButtonGroup
                            font.pointSize: 9
                        }
                    }

                    ButtonGroup {
                        id: patternButtonGroup // Define the missing ButtonGroup
                    }
                }
            }

            // Generate Flights Section
            GroupBox {
                title: "Generate Missions"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300

                RowLayout {
                    width: 280
                    spacing: 5

                    Button {
                        text: "Generate Flight Paths"
                        Layout.preferredWidth: 135
                        background: Rectangle {
                            color: parent.hovered ? "#e8f5e8" : "#f5f5f5"
                            border.color: "#4CAF50"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#2E7D32"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            console.log("Generate flight paths")
                            console.log("Flights:", flightCountSpinBox.value)
                            console.log("Altitude:", altitudeSpinBox.value + "m")
                            console.log("Front overlap:", frontOverlapSpinBox.value + "%")
                            console.log("Lateral overlap:", lateralOverlapSpinBox.value + "%")
                            console.log("Pattern:", patternButtonGroup.checkedButton.text)
                            console.log("Orientation:", orientationSlider.value.toFixed(1) + "°")

                            // Update mission information display
                            missionInfoText.text = "MISSION GENERATED\n" +
                                                 "================\n\n" +
                                                 "Flight Parameters:\n" +
                                                 "- Number of Flights: " + flightCountSpinBox.value + "\n" +
                                                 "- Altitude: " + altitudeSpinBox.value + " m\n" +
                                                 "- Speed: " + speedSpinBox.value + " m/s\n" +
                                                 "- Front Overlap: " + frontOverlapSpinBox.value + " %\n" +
                                                 "- Lateral Overlap: " + lateralOverlapSpinBox.value + " %\n" +
                                                 "- Flight Pattern: " + patternButtonGroup.checkedButton.text + "\n" +
                                                 "- Orientation: " + orientationSlider.value.toFixed(1) + " °\n\n" +
                                                 "Estimated Mission Data:\n" +
                                                 "- Total Flight Time: ~15 minutes\n" +
                                                 "- Coverage Area: ~2.5 km²\n" +
                                                 "- Battery Usage: ~75%\n" +
                                                 "- Waypoints Generated: 24\n\n" +
                                                 "Flight Path Details:\n" +
                                                 "Waypoint 1: Start position (0, 0)\n" +
                                                 "Waypoint 2: North boundary (0, 100)\n" +
                                                 "Waypoint 3: East turn (50, 100)\n" +
                                                 "... (additional waypoints)\n" +
                                                 "Waypoint 24: Return to start (0, 0)\n\n" +
                                                 "Safety Notes:\n" +
                                                 "- Maintain minimum 30m altitude over obstacles\n" +
                                                 "- Monitor battery levels throughout flight\n" +
                                                 "- Emergency landing zones identified"

                            // TODO: Generate actual flight paths based on parameters
                        }
                    }

                    Button {
                        text: "Save Missions"
                        Layout.preferredWidth: 135
                        background: Rectangle {
                            color: parent.hovered ? "#fff3e0" : "#f5f5f5"
                            border.color: "#FF9800"
                            border.width: 1
                            radius: 3
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#E65100"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            missionSaveDialog.open()
                        }
                    }
                }
            }

            // Mission Information Section
            GroupBox {
                title: "Mission Information"
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                Layout.minimumWidth: 300
                Layout.preferredHeight: 200

                TextArea {
                    id: missionInfoText
                    width: 280
                    height: parent.height - 10  // Account for GroupBox padding
                    readOnly: true
                    wrapMode: Text.Wrap
                    font.family: "Courier New"
                    font.pointSize: 8
                    background: Rectangle {
                        color: "#ffffff"
                        border.color: "#cccccc"
                        border.width: 1
                    }
                    text: "No mission generated yet.\n\n" +
                          "Mission details will appear here after generating flight paths.\n\n" +
                          "Information will include:\n" +
                          "- Flight path coordinates\n" +
                          "- Altitude and speed settings\n" +
                          "- Coverage area calculations\n" +
                          "- Estimated flight time\n" +
                          "- Battery consumption estimates"
                }
            }


            }
        }
    }

    FileDialog {
        id: missionSaveDialog
        title: "Save Mission Files"
        nameFilters: ["Mission files (*.mission)", "Waypoint files (*.waypoints)", "All files (*)"]
        onAccepted: {
            console.log("Save missions to:", selectedFile)
            // TODO: Save generated mission files
        }
    }

    // Handle window close
    onClosing: {
        console.log("Mission Planner window closed")
    }
}