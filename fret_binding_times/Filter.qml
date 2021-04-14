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
        },
        Sdt.TrackDisplay {
            trackData: root.rejectedTracks
            currentFrame: previewFrameNumber
            color: "red"
        }
    ]
    property alias filterInitial: filterInitialCheck.checked
    property alias filterTerminal: filterTerminalCheck.checked
    property alias massThresh: massThreshSel.value
    property alias bgThresh: bgThreshSel.value

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        Switch {
            id: filterInitialCheck
            text: "remove initially present tracks"
            checked: true
        }
        Switch {
            id: filterTerminalCheck
            text: "remove terminally present tracks"
            checked: true
        }
        RowLayout {
            Label {
                text: "mean bg"
                Layout.fillWidth: true
            }
            Label { text: "<" }
            Sdt.EditableSpinBox {
                id: bgThreshSel
                from: 0
                to: Sdt.Sdt.intMax
                stepSize: 10
            }
        }
        RowLayout {
            Label {
                text: "mean mass"
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
        }
        Item { Layout.fillHeight: true }
        Switch {
            text: "preview"
            checked: root.previewEnabled
            onCheckedChanged: { root.previewEnabled = checked }
        }
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
