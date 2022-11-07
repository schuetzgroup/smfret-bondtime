import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.1 as Sdt
import BindingTime.Templates 1.0 as T


T.Filter {
    id: root

    property int previewFrameNumber: -1
    property int frameCount: 0
    property list<Item> overlays: [
        Sdt.TrackDisplay {
            trackData: root.manualAccepted
            currentFrame: previewFrameNumber
            color: "Lime"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.manualUndecided
            currentFrame: previewFrameNumber
            color: "yellow"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.manualRejected
            currentFrame: previewFrameNumber
            color: "red"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.paramRejected
            currentFrame: previewFrameNumber
            color: "gray"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
            visible: showParamCheck.checked
        },
        Sdt.TrackDisplay {
            trackData: root.currentTrack
            currentFrame: previewFrameNumber
            color: "#8080ff"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        }
    ]
    property alias filterInitial: filterInitialCheck.checked
    property alias filterTerminal: filterTerminalCheck.checked
    property alias massThresh: massThreshSel.value
    property alias bgThresh: bgThreshSel.value
    property alias minLength: minLengthSel.value
    property Item timeTraceFig: null

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent
        spacing: 7

        GroupBox {
            title: "display options"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent

                Switch {
                    id: locPreviewCheck
                    text: "show localizations"
                    checked: true
                }
                Switch {
                    id: trackPreviewCheck
                    text: "show tracks"
                    checked: true
                }
                Switch {
                    id: showParamCheck
                    text: "show parametrically rejected"
                    checked: false
                }
            }
        }
        GroupBox {
            title: "parametric filter"
            Layout.fillWidth: true

            GridLayout {
                columns: 2
                anchors.fill: parent

                Switch {
                    id: filterInitialCheck
                    text: "remove initially present tracks"
                    checked: true
                    Layout.columnSpan: 2
                }
                Switch {
                    id: filterTerminalCheck
                    text: "remove terminally present tracks"
                    checked: true
                    Layout.columnSpan: 2
                }
                Label {
                    text: "max. background"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: bgThreshSel
                    from: 0
                    to: Sdt.Sdt.intMax
                    stepSize: 10
                }
                Label {
                    text: "min. intensity"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: massThreshSel
                    from: 0
                    to: Sdt.Sdt.intMax
                    // decimals: 0
                    stepSize: 100
                }
                Label {
                    text: "min. length"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: minLengthSel
                    from: 1
                    to: Sdt.Sdt.intMax
                    value: 2
                }
            }
        }
        GroupBox {
            Layout.fillWidth: true
            title: "manual filter"

            GridLayout {
                anchors.fill: parent
                columns: 2

                Switch {
                    id: firstFrameCheck
                    text: "go to first frame"
                    checked: true
                    Layout.columnSpan: 2
                }
                Label {
                    text: "track"
                    Layout.fillWidth: true
                }
                SpinBox {
                    id: trackSel
                    contentItem: ComboBox {
                        editable: true
                        model: root.trackList
                        implicitWidth: 100
                        onCurrentTextChanged: { updateCurrentTrack() }
                        onModelChanged: { updateCurrentTrack() }

                        function updateCurrentTrack() {
                            var n = model[currentIndex]
                            root.currentTrackNo = n == undefined ? -1 : n
                            parent.value = currentIndex
                            if (firstFrameCheck.checked)
                                root.previewFrameNumber = root.currentTrackInfo.start
                        }
                    }
                    padding: 0
                    to: contentItem.model.length - 1
                    onValueChanged: { contentItem.currentIndex = value }
                }
                Label { text: "frame"}
                Row {
                    ToolButton {
                        icon.name: "go-first"
                        width: (trackSel.width - frameNavSep.width) / 4
                        onClicked: {
                            root.previewFrameNumber = root.currentTrackInfo.start
                        }
                    }
                    ToolButton {
                        icon.name: "go-last"
                        width: (trackSel.width - frameNavSep.width) / 4
                        onClicked: {
                            root.previewFrameNumber = root.currentTrackInfo.end
                        }
                    }
                    ToolSeparator {
                        id: frameNavSep
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    ToolButton {
                        icon.name: "go-previous"
                        autoRepeat: true
                        width: (trackSel.width - frameNavSep.width) / 4
                        enabled: root.previewFrameNumber > 0
                        onClicked: {
                            root.previewFrameNumber -= 1
                        }
                    }
                    ToolButton {
                        icon.name: "go-next"
                        autoRepeat: true
                        width: (trackSel.width - frameNavSep.width) / 4
                        enabled: root.previewFrameNumber < root.frameCount - 1
                        onClicked: {
                            root.previewFrameNumber += 1
                        }
                    }
                }
                Label { text: "action" }
                Row {
                    ToolButton {
                        icon.name: "dialog-ok-apply"
                        icon.color: "green"
                        width: (trackSel.width - actionSep.width) / 2
                        onClicked: {
                            root.acceptTrack(root.currentTrackNo)
                            trackSel.increase()
                        }
                    }
                    ToolSeparator {
                        id: actionSep
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    ToolButton {
                        icon.name: "dialog-cancel"
                        icon.color: "red"
                        width: (trackSel.width - actionSep.width) / 2
                        onClicked: {
                            root.rejectTrack(root.currentTrackNo)
                            trackSel.increase()
                        }
                    }
                }
                Label { text: "intensity" }
                Label { text: root.currentTrackInfo.mass.toFixed(0) }
                Label { text: "background" }
                Label { text: root.currentTrackInfo.bg.toFixed(0) }
                Label { text: "noise" }
                Label { text: root.currentTrackInfo.bg_dev.toFixed(0) }
                Label { text: "length" }
                Label { text: root.currentTrackInfo.length }
                Label { text: "status" }
                Label { text: root.currentTrackInfo.status }
            }
        }
        Item { Layout.fillHeight: true }
    }

    Component.onCompleted: { completeInit() }
}
