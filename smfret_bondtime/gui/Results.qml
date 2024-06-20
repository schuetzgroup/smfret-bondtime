// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.3 as QQDialogs
import QtQuick.Layouts 1.15
import SdtGui 0.2 as Sdt

import SmFretBondTime.Templates 1.0 as T

T.Results {
    id: root

    readonly property Item resultsFig: resultsFig
    property alias minCount: minCountBox.value
    property alias nBoot: nBootBox.value
    property int randomSeed: genRandomSeed()

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    RowLayout {
        id: rootLayout
        anchors.fill: parent

        GridLayout {
            columns: 3

            Label {
                text: "minimum track count"
            }
            Sdt.EditableSpinBox {
                id: minCountBox
                from: 1
                to: 999
                value: 10
                Layout.columnSpan: 2
                Layout.alignment: Qt.AlignRight
            }
            Label {
                text: "bootstrap runs"
            }
            Sdt.EditableSpinBox {
                id: nBootBox
                from: 1
                to: 9999
                value: 1
                Layout.columnSpan: 2
                Layout.alignment: Qt.AlignRight
            }
            Label {
                text: "random seed"
                enabled: root.nBoot > 1
            }
            TextField {
                id: randomSeedBox
                text: root.randomSeed
                validator: IntValidator {}
                onTextChanged: { root.randomSeed = text }
                enabled: root.nBoot > 1
                selectByMouse: true
            }
            ToolButton {
                icon.name: "roll"
                onPressed: { root.randomSeed = root.genRandomSeed() }
                enabled: root.nBoot > 1
            }
            Button {
                text: "Calculate lifetime…"
                Layout.columnSpan: 3
                Layout.fillWidth: true
                onPressed: {
                    workerDialog.title = "Calculating lifetime…"
                    root.calculate()
                }
            }
            Item {
                height: 5
                Layout.columnSpan: 3
            }
            Button {
                text: "Export results…"
                Layout.columnSpan: 3
                enabled: root.resultAvailable
                Layout.fillWidth: true
                onPressed: {
                    workerDialog.title = "Exporting results…"
                    exportFileDialog.open()
                }
            }
            Button {
                text: "Save plot…"
                Layout.columnSpan: 3
                enabled: root.resultAvailable
                Layout.fillWidth: true
                onPressed: {
                    workerDialog.title = "Exporting plot…"
                    exportFigDialog.open()
                }
            }
            Item {
                Layout.columnSpan: 3
                Layout.fillHeight: true
            }
        }
        Sdt.FigureCanvasAgg {
            id: resultsFig
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Dialog {
        id: workerDialog
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.NoAutoClose
        modal: true
        visible: root._worker.busy
        contentHeight: Math.max(progBar.implicitHeight, errText.implicitHeight)

        ProgressBar {
            id: progBar
            anchors.fill: parent
            indeterminate: true
            visible: root._worker.busy

            states: [
                State {
                    name: "error"
                    when: root._workerError !== ""
                    PropertyChanges {
                        target: workerDialog
                        title: "Error"
                        visible: true
                    }
                    PropertyChanges {
                        target: workerDialogButton
                        text: "Close"
                        DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                    }
                }
            ]
        }
        Text {
            id: errText
            anchors.fill: parent
            text: root._workerError
            wrapMode: Text.Wrap
        }

        footer: DialogButtonBox {
            // If we used `standardButtons`, we'd get a binding loop on implicitHeight
            Button {
                id:workerDialogButton
                text: "Abort"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onRejected: { root._worker.enabled = false }
    }

    QQDialogs.FileDialog {
        id: exportFileDialog
        selectMultiple: false
        selectExisting: false
        nameFilters: ["Excel (*.xlsx)", "Open Document (*.ods)"]
        folder: Sdt.Sdt.parentUrl(backend.saveFile)
        onAccepted: { root.exportResults(fileUrl) }
    }

    QQDialogs.FileDialog {
        id: exportFigDialog
        selectMultiple: false
        selectExisting: false
        nameFilters: ["SVG (*.svg)", "PDF (*.pdf)", "PNG (*.png)"]
        folder: Sdt.Sdt.parentUrl(backend.saveFile)
        onAccepted: { root.exportFigure(fileUrl) }
    }
}
