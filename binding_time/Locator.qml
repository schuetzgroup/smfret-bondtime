import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    id: root

    property var datasets
    property alias algorithm: loc.algorithm
    property alias options: loc.options
    property alias previewEnabled: loc.previewEnabled
    property Item overlays: Sdt.LocDisplay { locData: loc.locData }
    property var previewImage: null

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        Sdt.LocateOptions {
            id: loc
            input: previewImage
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
    Dialog {
        id: batchDialog
        title: "Locating…"
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
            argRoles: ["corrAcceptor"]
            resultRole: "locData"
        }

        onRejected: { batchWorker.abort() }
    }
}
