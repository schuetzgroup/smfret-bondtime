import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    id: root

    property alias options: track.options

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent
        RowLayout {
            Label { text: "dataset" }
            Sdt.DatasetSelector {
                id: trackDatasetSel
                datasets: backend.datasets
                editable: false
                Layout.fillWidth: true
            }
            Item { width: 20 }
            Sdt.ImageSelector {
                id: trackImSel
                editable: false
                dataset: trackDatasetSel.currentDataset
                textRole: "key"
                imageRole: "fretImage"
                Layout.fillWidth: true
            }
        }
        RowLayout {
            ColumnLayout {
                Sdt.TrackOptions {
                    id: track
                    locData: trackImSel.dataset.getProperty(trackImSel.currentIndex, "locData")
                    Layout.alignment: Qt.AlignTop
                }
                Item { Layout.fillHeight: true }
                Button {
                    text: "Track all…"
                    Layout.fillWidth: true
                    onClicked: {
                        trackBatchWorker.func = track.getTrackFunc()
                        trackBatchWorker.start()
                        trackBatchDialog.open()
                    }
                }
            }
            Sdt.ImageDisplay {
                id: trackImDisp
                input: trackImSel.output
                overlays: Sdt.TrackDisplay {
                    trackData: track.trackData
                    currentFrame: trackImSel.currentFrame
                }
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
