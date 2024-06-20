// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.2 as Sdt


Item {
    id: root

    property alias background: bgSel.value
    property alias factor: btSel.value
    property alias smooth: smoothSel.value
    readonly property string imageRole: {
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
            text: "factor"
            Layout.fillWidth: true
        }
        Sdt.RealSpinBox {
            id: btSel
            from: 0
            to: 1
            decimals: 3
            stepSize: 0.01
        }
        Label {
            text: "smoothing"
            Layout.fillWidth: true
        }
        Sdt.RealSpinBox {
            id: smoothSel
            from: 0
            to: Infinity
            decimals: 1
            stepSize: 0.1
            value: 1.0
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
                    text: "donor"
                }
                RadioButton {
                    id: showAcceptorButton
                    text: "acceptor"
                }
                RadioButton {
                    id: showAcceptorCorrButton
                    checked: true
                    text: "corrected acceptor"
                }
            }
        }
    }
}
