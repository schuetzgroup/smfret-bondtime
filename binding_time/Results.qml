import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt


Item {
    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    RowLayout {
        id: rootLayout

        anchors.fill: parent

        Item {
            implicitWidth: textLayout.implicitWidth
            implicitHeight: textLayout.implicitHeight
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            ColumnLayout {
                id: textLayout
                anchors.fill: parent
                GroupBox {
                    title: "Fitting options"
                    Layout.fillWidth: true
                    GridLayout {
                        columns: 2
                        anchors.fill: parent
                        RadioButton {
                            id: fitRatesButton
                            text: "fit rates"
                            checked: true
                            Layout.columnSpan: 2
                        }
                        RadioButton {
                            text: "fit times"
                            Layout.columnSpan: 2
                        }
                        Label { text: "ignore first" }
                        Sdt.EditableSpinBox {
                            id: ignoreFirstSel
                            value: 1
                        }
                        Label { text: "min. count" }
                        Sdt.EditableSpinBox {
                            id: minCountSel
                            value: 10
                        }
                    }
                }
                GroupBox {
                    id: resultValueGroup
                    property real kOff

                    Binding on kOff {
                        when: root.visible
                        value: root.visible, backend.getResults(
                            resultCanvas, ignoreFirstSel.value, minCountSel.value,
                            fitRatesButton.checked
                        )
                    }

                    title: "Results"
                    Layout.fillWidth: true
                    GridLayout {
                        columns: 3
                        anchors.fill: parent
                        Label {
                            textFormat: Text.RichText
                            text: "<b>k<sub>off</sub>:</b> "
                        }
                        Label {
                            text: Number(resultValueGroup.kOff).toLocaleString(Qt.locale(), "f", 2)
                        }
                        Label {
                            textFormat: Text.RichText
                            text: "s<sup>-1</sup>"
                        }
                        Label {
                            textFormat: Text.RichText
                            text: "<b>t<sub>off</sub>:</b> "
                        }
                        Label {
                            text: Number(1 / resultValueGroup.kOff).toLocaleString(Qt.locale(), "f", 1)
                        }
                        Label {
                            text: "s"
                        }
                        Label {
                            textFormat: Text.RichText
                            text: "<b>t<sub>1/2</sub>:</b> "
                        }
                        Label {
                            text: Number(Math.log(2) / resultValueGroup.kOff).toLocaleString(Qt.locale(), "f", 1)
                        }
                        Label {
                            text: "s"
                        }
                    }
                }
            }
        }
        Sdt.FigureCanvasAgg {
            id: resultCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
