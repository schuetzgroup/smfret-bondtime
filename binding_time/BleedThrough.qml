import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    id: root

    property alias background: bgSel.value
    property alias bleedThrough: btSel.value
    property string imageRole: {
        if (showDonorButton.checked)
            "donor"
        else if (showAcceptorButton.checked)
            "acceptor"
        else
            "corrAcceptor"
    }


    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    GridLayout {
        id: rootLayout

        anchors.fill: parent
        columns: 2

        Label {
            text: "background"
            Layout.fillWidth: true
        }
        Sdt.RealSpinBox {
            id: bgSel
            to: Infinity
            decimals: 0
            value: 200
            stepSize: 10
        }
        Label {
            text: "bleed-through"
            Layout.fillWidth: true
        }
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
}
