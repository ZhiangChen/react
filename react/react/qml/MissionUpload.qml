import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: uploadWindow
    title: "Mission Upload"
    width: 450
    height: 250
    minimumWidth: 400
    minimumHeight: 220
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint
    modality: Qt.NonModal
    
    property int totalUAVs: 0
    property int completedUAVs: 0
    property int successCount: 0
    property int failureCount: 0
    property var uploadStatuses: ({})  // {uav_id: {status: string, progress: float, success: bool}}
    property bool isResumeOperation: false  // Track if this is a +Resume operation
    property var successfulUAVs: []  // Track UAVs that uploaded successfully
    
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
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            
            // Header: Overall Progress
            GroupBox {
                title: "Overall Progress"
                Layout.fillWidth: true
                Layout.preferredHeight: 75
                
                background: Rectangle {
                    color: "white"
                    border.color: "#ddd"
                    border.width: 1
                    radius: 4
                }
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 5
                    
                    // Progress label
                    Label {
                        text: uploadWindow.completedUAVs + " / " + uploadWindow.totalUAVs + " UAVs Completed"
                        font.bold: true
                        font.pixelSize: 13
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: -15
                    }
                    
                    // Overall progress bar
                    ProgressBar {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 5
                        from: 0
                        to: uploadWindow.totalUAVs
                        value: uploadWindow.completedUAVs
                        
                        background: Rectangle {
                            implicitWidth: 200
                            implicitHeight: 20
                            color: "#e0e0e0"
                            radius: 4
                            border.color: "#bbb"
                            border.width: 1
                        }
                        
                        contentItem: Item {
                            implicitWidth: 200
                            implicitHeight: 18
                            
                            Rectangle {
                                width: uploadWindow.totalUAVs > 0 ? 
                                       (uploadWindow.completedUAVs / uploadWindow.totalUAVs) * parent.width : 0
                                height: parent.height
                                radius: 3
                                color: "#4CAF50"
                            }
                        }
                    }
                    
                    // Statistics row
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: -4
                        spacing: 20
                        
                        RowLayout {
                            spacing: 5
                            Label {
                                text: "Success:"
                                color: "#000000"
                                font.bold: true
                                font.pixelSize: 11
                            }
                            Label {
                                text: uploadWindow.successCount
                                color: "#000000"
                                font.pixelSize: 14
                                font.bold: true
                            }
                        }
                        
                        RowLayout {
                            spacing: 5
                            Label {
                                text: "Failed:"
                                color: "#000000"
                                font.bold: true
                                font.pixelSize: 11
                            }
                            Label {
                                text: uploadWindow.failureCount
                                color: "#000000"
                                font.pixelSize: 14
                                font.bold: true
                            }
                        }
                        
                        Item { Layout.fillWidth: true }  // Spacer
                    }
                }
            }
            
            // Individual UAV Progress List
            GroupBox {
                title: "UAV Upload Status"
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                background: Rectangle {
                    color: "white"
                    border.color: "#ddd"
                    border.width: 1
                    radius: 4
                }
                
                ScrollView {
                    anchors.fill: parent
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    
                    ListView {
                        id: uavListView
                        model: ListModel {
                            id: uavListModel
                        }
                        spacing: 5
                        
                        delegate: Rectangle {
                            width: uavListView.width - 10
                            height: 55
                            color: index % 2 === 0 ? "#fafafa" : "#ffffff"
                            border.color: "#e0e0e0"
                            border.width: 1
                            radius: 4
                            
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 3
                                
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    
                                    // UAV ID
                                    Label {
                                        text: model.uavId
                                        font.bold: true
                                        font.pixelSize: 12
                                        Layout.minimumWidth: 80
                                    }
                                    
                                    // Status message
                                    Label {
                                        text: model.statusMessage
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        color: "#555"
                                        font.pixelSize: 10
                                    }
                                    
                                    // Progress percentage
                                    Label {
                                        text: Math.round(model.progress) + "%"
                                        font.pixelSize: 11
                                        color: "#666"
                                        Layout.minimumWidth: 40
                                        horizontalAlignment: Text.AlignRight
                                    }
                                }
                                
                                // Progress bar
                                ProgressBar {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 6
                                    from: 0
                                    to: 100
                                    value: model.progress
                                    
                                    background: Rectangle {
                                        implicitWidth: 200
                                        implicitHeight: 6
                                        color: "#e0e0e0"
                                        radius: 3
                                    }
                                    
                                    contentItem: Item {
                                        implicitWidth: 200
                                        implicitHeight: 4
                                        
                                        Rectangle {
                                            width: model.progress * parent.width / 100
                                            height: parent.height
                                            radius: 2
                                            color: "#4CAF50"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Functions to manage upload status
    function reset(total, isResume) {
        totalUAVs = total
        completedUAVs = 0
        successCount = 0
        failureCount = 0
        uploadStatuses = {}
        uavListModel.clear()
        isResumeOperation = isResume || false
        successfulUAVs = []
    }
    
    function addUAV(uavId) {
        if (!uploadStatuses[uavId]) {
            uploadStatuses[uavId] = {
                index: uavListModel.count,
                status: "Initializing...",
                progress: 0,
                success: false
            }
            
            uavListModel.append({
                uavId: uavId,
                statusMessage: "Initializing...",
                progress: 0,
                success: false
            })
        }
    }
    
    function updateProgress(uavId, statusMessage, progressPercent) {
        if (!uploadStatuses[uavId]) {
            addUAV(uavId)
        }
        
        var status = uploadStatuses[uavId]
        var index = status.index
        
        uavListModel.setProperty(index, "statusMessage", statusMessage)
        uavListModel.setProperty(index, "progress", progressPercent)
        
        uploadStatuses[uavId].status = statusMessage
        uploadStatuses[uavId].progress = progressPercent
    }
    
    function setComplete(uavId, success, message) {
        if (!uploadStatuses[uavId]) {
            addUAV(uavId)
        }
        
        var status = uploadStatuses[uavId]
        var index = status.index
        
        uavListModel.setProperty(index, "statusMessage", message)
        uavListModel.setProperty(index, "progress", 100)
        uavListModel.setProperty(index, "success", success)
        
        uploadStatuses[uavId].status = message
        uploadStatuses[uavId].progress = 100
        uploadStatuses[uavId].success = success
        
        completedUAVs++
        if (success) {
            successCount++
            successfulUAVs.push(uavId)
        } else {
            failureCount++
        }
        
        // Check if all uploads are complete
        if (completedUAVs >= totalUAVs) {
            // If this is a +Resume operation and we have successful uploads, auto-start missions
            if (isResumeOperation && successfulUAVs.length > 0) {
                console.log("+Resume: All uploads complete. Auto-starting missions for", successfulUAVs.length, "UAV(s)")
                
                // Delay to let user see the completion status
                autoStartTimer.start()
            }
        }
    }
    
    // Timer for auto-starting missions after +Resume upload completes
    Timer {
        id: autoStartTimer
        interval: 1500  // 1.5 second delay to show completion
        repeat: false
        onTriggered: {
            console.log("+Resume: Auto-starting missions...")
            
            // Start mission for each successfully uploaded UAV
            for (var i = 0; i < successfulUAVs.length; i++) {
                var uavId = successfulUAVs[i]
                console.log("  Starting mission for", uavId)
                
                try {
                    if (backend && backend.uav_controller) {
                        backend.uav_controller.start_mission(uavId)
                    }
                } catch(e) {
                    console.error("Error starting mission for", uavId, ":", e)
                }
            }
            
            // Close the upload window after starting missions
            uploadWindow.close()
        }
    }
}
