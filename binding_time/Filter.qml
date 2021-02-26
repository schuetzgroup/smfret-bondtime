import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt
import BindingTime.Templates 1.0 as T


T.Filter {
    id: root

    property var datasets
    property var previewData: null
    property var previewImageSequence: null
    property int previewFrameNumber: -1
    property var overlays: Sdt.TrackDisplay {
        id: trackDisp
        trackData: options, filterTracks(previewData, previewImageSequence)
        currentFrame: previewFrameNumber
    }

    Binding on options { value: rootLayout.options }
    onOptionsChanged: {
        filterInitialCheck.checked = options.filter_initial
        filterTerminalCheck.checked = options.filter_terminal
        bgThreshSel.value = options.bg_thresh
        massThreshSel.value = options.mass_thresh
    }

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        property var options: {
            "filter_initial": filterInitialCheck.checked,
            "filter_terminal": filterTerminalCheck.checked,
            "bg_thresh": bgThreshSel.value,
            "mass_thresh": massThreshSel.value
        }

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
                to: Sdt.Common.intMax
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
                to: Sdt.Common.intMax
                // decimals: 0
                stepSize: 100
            }
        }
        Item { Layout.fillHeight: true }
        Switch {
            text: "Show tracks"
            checked: true
            onCheckedChanged: { trackDisp.visible = checked }
        }
        Button {
            text: "Filter all…"
            Layout.fillWidth: true
            onClicked: {
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
            func: root._getFilterFunc()
            argRoles: ["locData", "corrAcceptor"]
        }

        onRejected: { batchWorker.abort() }
    }
}
