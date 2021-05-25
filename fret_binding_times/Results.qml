import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.1 as Sdt


Item {
    id: root

    property int minLength
    property alias minCount: minCountSel.value
    property string fitVariable

    Binding on fitVariable {
        value: fitRatesButton.checked ? "rates" : "times"
    }

    onFitVariableChanged: {
        if (fitVariable == "rates")
            fitRatesButton.checked = true
        else
            fitTimesButton.checked = true
    }

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
                            id: fitTimesButton
                            text: "fit times"
                            Layout.columnSpan: 2
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
                    property var results: {
                        if (root.visible) {
                            backend.getResults(
                                resultCanvas, root.minLength, minCountSel.value,
                                fitRatesButton.checked
                            )
                        } else {
                            []
                        }
                    }

                    title: "Results"
                    Layout.fillWidth: true
                    GridLayout {
                        columns: 3
                        anchors.fill: parent
                        Label {
                            textFormat: Text.RichText
                            text: "<b>k<sub>bleach</sub>:</b> "
                        }
                        Label {
                            text: (Number(resultValueGroup.results.k_bleach).toLocaleString(Qt.locale(), "f", 2) +
                                   " ± " +
                                   Number(resultValueGroup.results.k_bleach_err).toLocaleString(Qt.locale(), "f", 3))
                        }
                        Label {}
                        Label {
                            textFormat: Text.RichText
                            text: "<b>k<sub>off</sub>:</b> "
                        }
                        Label {
                            text: (Number(resultValueGroup.results.k_off).toLocaleString(Qt.locale(), "f", 2) +
                                   " ± " +
                                   Number(resultValueGroup.results.k_off_err).toLocaleString(Qt.locale(), "f", 3))
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
                            text: (Number(resultValueGroup.results.t_off).toLocaleString(Qt.locale(), "f", 1) +
                                   " ± " +
                                   Number(resultValueGroup.results.t_off_err).toLocaleString(Qt.locale(), "f", 2))
                        }
                        Label {
                            text: "s"
                        }
                        Label {
                            textFormat: Text.RichText
                            text: "<b>t<sub>1/2</sub>:</b> "
                        }
                        Label {
                            text: (Number(resultValueGroup.results.t_off * Math.log(2)).toLocaleString(Qt.locale(), "f", 1) +
                                   " ± " +
                                   Number(resultValueGroup.results.t_off_err * Math.log(2)).toLocaleString(Qt.locale(), "f", 2))
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
