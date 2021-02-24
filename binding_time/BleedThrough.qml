import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    id: root

    property alias background: bgSel.value
    property alias bleedThrough: btSel.value

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent
        RowLayout {
            Label { text: "dataset" }
            Sdt.DatasetSelector {
                id: datasetSel
                datasets: backend.datasets
                editable: false
                Layout.fillWidth: true
            }
            Item { width: 5 }
            Sdt.ImageSelector {
                id: imSel
                editable: false
                dataset: datasetSel.currentDataset
                textRole: "key"
                imageRole: {
                    if (showDonorButton.checked)
                        "donor"
                    else if (showAcceptorButton.checked)
                        "acceptor"
                    else
                        "corrAcceptor"
                }
                Layout.fillWidth: true
            }
        }
        RowLayout {
            GridLayout {
                columns: 2
                Label { text: "background" }
                Sdt.RealSpinBox {
                    id: bgSel
                    to: Infinity
                    decimals: 0
                    value: 200
                    stepSize: 10
                }
                Label { text: "bleed-through" }
                Sdt.RealSpinBox {
                    id: btSel
                    from: 0
                    to: 1
                    decimals: 3
                    stepSize: 0.01
                }
                Item {
                    Layout.fillHeight: true
                    Layout.columnSpan: 2
                }
                GroupBox {
                    title: "show"
                    Layout.columnSpan: 2
                    Layout.fillWidth: true

                    ButtonGroup {
                        id: showGroup
                        buttons: showLayout.children
                    }
                    ColumnLayout {
                        id: showLayout

                        RadioButton {
                            id: showDonorButton
                            checked: true
                            text: "donor"
                        }
                        RadioButton {
                            id: showAcceptorButton
                            text: "acceptor"
                        }
                        RadioButton {
                            id: showAcceptorCorrButton
                            text: "corrected acceptor"
                        }
                    }
                }
            }
            Sdt.ImageDisplay {
                id: imDisp
                input: imSel.output
                // TODO: overlays:
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
