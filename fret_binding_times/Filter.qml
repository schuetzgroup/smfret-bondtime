import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.1 as Sdt
import BindingTime.Templates 1.0 as T


T.Filter {
    id: root

    property int previewFrameNumber: -1
    property list<Item> overlays: [
        Sdt.TrackDisplay {
            trackData: root.acceptedTracks
            currentFrame: previewFrameNumber
            color: "Lime"
            visible: !showCurrentCheck.checked && previewCheck.checked
        },
        Sdt.TrackDisplay {
            trackData: root.rejectedTracks
            currentFrame: previewFrameNumber
            color: "red"
            visible: showRejectedCheck.checked && previewCheck.checked
        },
        Sdt.TrackDisplay {
            trackData: root.currentTrack
            currentFrame: previewFrameNumber
            color: "yellow"
            visible: previewCheck.checked
        }
    ]
    property alias filterInitial: filterInitialCheck.checked
    property alias filterTerminal: filterTerminalCheck.checked
    property alias massThresh: massThreshSel.value
    property alias bgThresh: bgThreshSel.value
    property alias minLength: minLengthSel.value

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        GroupBox {
            title: "filter options"
            Layout.fillWidth: true

            GridLayout {
                columns: 3
                anchors.fill: parent

                Switch {
                    id: filterInitialCheck
                    text: "remove initially present tracks"
                    checked: true
                    Layout.columnSpan: 3
                }
                Switch {
                    id: filterTerminalCheck
                    text: "remove terminally present tracks"
                    checked: true
                    Layout.columnSpan: 3
                }
                Label {
                    text: "background"
                    Layout.fillWidth: true
                }
                Label { text: "<" }
                Sdt.EditableSpinBox {
                    id: bgThreshSel
                    from: 0
                    to: Sdt.Sdt.intMax
                    stepSize: 10
                }
                Label {
                    text: "intensity"
                    Layout.fillWidth: true
                }
                Label { text: ">" }
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
                    Layout.columnSpan: 2
                }
                Sdt.EditableSpinBox {
                    id: minLengthSel
                    from: 1
                    to: Sdt.Sdt.intMax
                    value: 2
                }
            }
        }
        Item { height: 5 }
        GroupBox {
            Layout.fillWidth: true
            title: "check results"

            GridLayout {
                anchors.fill: parent
                columns: 2

                Switch {
                    id: previewCheck
                    text: "preview"
                    checked: true
                    Layout.columnSpan: 2
                }
                Switch {
                    id: showRejectedCheck
                    text: "show rejected"
                    checked: true
                    enabled: previewCheck.checked
                    Layout.columnSpan: 2
                }
                Switch {
                    id: showCurrentCheck
                    text: "show current only"
                    checked: false
                    enabled: previewCheck.checked
                    Layout.columnSpan: 2
                }
                Switch {
                    id: firstFrameCheck
                    text: "go to first frame"
                    checked: true
                    Layout.columnSpan: 2
                }
                Switch {
                    id: browseRejectedCheck
                    text: "browse rejected"
                    checked: false
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
                        model: browseRejectedCheck.checked ? root.trackList : root.acceptedTrackList
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
                        width: trackSel.width / 2
                        onClicked: {
                            root.previewFrameNumber = root.currentTrackInfo.start
                        }
                    }
                    ToolButton {
                        icon.name: "go-last"
                        width: trackSel.width / 2
                        onClicked: {
                            root.previewFrameNumber = root.currentTrackInfo.end
                        }
                    }
                }
                Label { text: "intensity" }
                Label { text: root.currentTrackInfo.mass.toFixed(0) }
                Label { text: "background" }
                Label { text: root.currentTrackInfo.bg.toFixed(0) }
                Label { text: "length" }
                Label { text: root.currentTrackInfo.length }
                Label { text: "status" }
                Label { text: root.currentTrackInfo.status }
            }
        }
        Item { Layout.fillHeight: true }
        Button {
            text: "Filter all…"
            Layout.fillWidth: true
            onClicked: {
                batchWorker.func = root.getFilterFunc()
                batchWorker.start()
                batchDialog.open()
            }
        }
    }

    Dialog {
        id: batchDialog
        title: "Filtering…"
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.NoAutoClose
        modal: true
        footer: DialogButtonBox {
            Button {
                text: batchWorker.progress == batchWorker.count ? "OK" : "Abort"
                DialogButtonBox.buttonRole: (batchWorker.progress == batchWorker.count ?
                                             DialogButtonBox.AcceptRole :
                                             DialogButtonBox.RejectRole)
            }
        }

        Sdt.BatchWorker {
            id: batchWorker
            anchors.fill: parent
            dataset: root.datasets
            argRoles: ["locData", "corrAcceptor"]
        }

        onRejected: { batchWorker.abort() }
    }

    Component.onCompleted: { completeInit() }
}
