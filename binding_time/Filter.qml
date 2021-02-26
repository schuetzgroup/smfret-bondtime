import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt
import BindingTime.Templates 1.0 as T


T.Filter {
    id: root

    property alias datasets: datasetSel.datasets

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
        RowLayout {
            Label { text: "dataset" }
            Sdt.DatasetSelector {
                id: datasetSel
                Layout.fillWidth: true
            }
            Item { width: 5 }
            Sdt.ImageSelector {
                id: imSel
                editable: false
                dataset: datasetSel.currentDataset
                textRole: "key"
                imageRole: "corrAcceptor"
                Layout.fillWidth: true
            }
        }
        RowLayout {
            ColumnLayout {
                Switch {
                    id: filterInitialCheck
                    text: "Remove initially present tracks"
                    checked: true
                }
                Switch {
                    id: filterTerminalCheck
                    text: "Remove terminally present tracks"
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
                        // decimals: 0
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
            Sdt.ImageDisplay {
                id: imDisp
                input: imSel.output
                overlays: Sdt.TrackDisplay {
                    id: trackDisp
                    trackData: root.options, root.filterTracks(
                        imSel.dataset.getProperty(imSel.currentIndex, "locData"),
                        imSel.dataset.getProperty(imSel.currentIndex, "corrAcceptor")
                    )
                    currentFrame: imSel.currentFrame
                }
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    Dialog {
        id: batchDialog
        title: "Filtering…"
        anchors.centerIn: parent
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
