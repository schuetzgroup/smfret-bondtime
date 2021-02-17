import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    id: root

    property alias algorithm: loc.algorithm
    property alias options: loc.options
    property alias previewEnabled: loc.previewEnabled

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent
        RowLayout {
            Label { text: "dataset" }
            Sdt.DatasetSelector {
                id: locDatasetSel
                model: backend
                editable: false
                Layout.fillWidth: true
            }
            Item { width: 20 }
            Sdt.ImageSelector {
                id: imSel
                editable: false
                dataset: locDatasetSel.currentDataset
                textRole: "key"
                imageRole: "fretImage"
                Layout.fillWidth: true
            }
        }
        RowLayout {
            ColumnLayout {
                Sdt.LocateOptions {
                    id: loc
                    input: imSel.output
                    Layout.alignment: Qt.AlignTop
                    Layout.fillHeight: true
                }
                Button {
                    text: "Locate all…"
                    Layout.fillWidth: true
                    onClicked: {
                        batchWorker.func = backend.getLocateFunc()
                        batchWorker.start()
                        batchDialog.open()
                    }
                }
            }
            Sdt.ImageDisplay {
                id: imDisp
                input: imSel.output
                overlays: Sdt.LocDisplay {
                    locData: loc.locData
                }
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
