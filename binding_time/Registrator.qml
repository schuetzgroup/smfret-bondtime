import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 1.0 as Sdt
import BindingTime 1.0


Item {
    id: root

    property alias dataset: coll.dataset
    property alias locAlgorithm: loc.algorithm
    property alias locOptions: loc.options
    property alias channels: dset.channels
    property alias dataDir: dset.dataDir

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        TabBar {
            id: actionTab
            Layout.fillWidth: true
            TabButton { text: "Select files" }
            TabButton { text: "Find transform" }
        }

        StackLayout {
            currentIndex: actionTab.currentIndex

            Sdt.DataCollector {
                id: coll
                sourceNames: channelConfig.sourceCount
                Layout.fillWidth: true
                Layout.fillHeight: true
                showDataDirSelector: false
                dataset: Dataset {
                    id: dset
                    dataRoles: ["key"].concat(channelSel.model)
                }
            }
            ColumnLayout {
                RowLayout {
                    Label { text: "channel" }
                    ComboBox {
                        id: channelSel
                        Layout.fillWidth: true
                        model: Object.keys(coll.dataset.channels)
                    }
                    Item { width: 5 }
                    Sdt.ImageSelector {
                        id: imSel
                        dataset: coll.dataset
                        textRole: "key"
                        imageRole: channelSel.currentText
                        editable: false
                        Layout.fillWidth: true
                    }
                }
                RowLayout {
                    ColumnLayout {
                        Sdt.LocateOptions {
                            id: loc
                            input: imSel.output
                            Layout.alignment: Qt.AlignTop
                            Layout.fillHeight: true
                        }
                        Button {
                            text: "Locate and find transform…"
                            onClicked: {
                                batchWorker.func = root.getLocateFunc()
                                batchWorker.start()
                                batchDialog.open()
                            }
                            Layout.preferredWidth: loc.width
                        }
                    }
                    Sdt.ImageDisplay {
                        id: imDisp
                        input: imSel.output
                        overlays: Sdt.LocDisplay {
                            locData: loc.locData
                            visible: loc.previewEnabled
                        }
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }
            }
        }
    }
    Dialog {
        id: batchDialog
        title: "Locating…"
        anchors.centerIn: parent
        closePolicy: Popup.NoAutoClose
        modal: true
        standardButtons: (batchWorker.progress == batchWorker.count ?
                        Dialog.SaveAll | Dialog.Close :
                        Dialog.Abort)

        onAccepted: { root.saveAll() }
        onRejected: {
            if (batchWorker.progress < batchWorker.count)
                batchWorker.abort()
        }

        ColumnLayout {
            anchors.fill: parent
            Sdt.BatchWorker {
                id: batchWorker
                dataset: imSel.dataset
                argRoles: ["image"]
                resultRole: "locData"
                Layout.fillWidth: true
            }
        }
    }
}
