import QtQuick 2.15
import QtQuick.Controls 2.15
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
                onPressed: root.calculate()
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
        id: calcDialog
        title: root.calcError === "" ? "Calculating lifetime…" : "Error"
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.NoAutoClose
        modal: true
        standardButtons: root.calcError === "" ? Dialog.Cancel : Dialog.Ok
        visible: root._calcWorker.busy || root.calcError !== ""
        contentHeight: Math.max(progBar.implicitHeight, errText.implicitHeight)

        ProgressBar {
            id: progBar
            anchors.fill: parent
            indeterminate: true
            visible: root._calcWorker.busy
        }
        Text {
            id: errText
            anchors.fill: parent
            visible: !root._calcWorker.busy
            text: root.calcError
            wrapMode: Text.Wrap
        }

        onRejected: { root._calcWorker.enabled = false }
    }
}
