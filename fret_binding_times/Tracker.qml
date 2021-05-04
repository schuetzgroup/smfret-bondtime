import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.1 as Sdt


Item {
    id: root

    property var datasets
    property alias searchRange: track.searchRange
    property alias memory: track.memory
    property Item overlays: Sdt.TrackDisplay {
        trackData: track.trackData
        currentFrame: previewFrameNumber
    }
    property var previewData: null
    property int previewFrameNumber: -1

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        Sdt.TrackOptions {
            id: track
            locData: root.previewData
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Item { Layout.fillHeight: true }
        Button {
            text: "Track all…"
            Layout.fillWidth: true
            onClicked: {
                trackBatchWorker.func = backend.getTrackFunc()
                trackBatchWorker.start()
                trackBatchDialog.open()
            }
        }
    }
    Dialog {
        id: trackBatchDialog
        title: "Tracking…"
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.NoAutoClose
        modal: true
        footer: DialogButtonBox {
            Button {
                text: (trackBatchWorker.progress == trackBatchWorker.count ?
                       "OK" : "Abort")
                DialogButtonBox.buttonRole: (
                    trackBatchWorker.progress == trackBatchWorker.count ?
                    DialogButtonBox.AcceptRole : DialogButtonBox.RejectRole
                )
            }
        }

        Sdt.BatchWorker {
            id: trackBatchWorker
            anchors.fill: parent
            dataset: root.datasets
            argRoles: ["locData"]
            resultRole: "locData"
        }

        onRejected: { trackBatchWorker.abort() }
    }
}
