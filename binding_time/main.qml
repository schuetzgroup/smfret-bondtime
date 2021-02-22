import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Dialogs 1.3 as QQDialogs
import QtQuick.Layouts 1.12
import Qt.labs.settings 1.0
import SdtGui 1.0 as Sdt
import BindingTime 1.0


ApplicationWindow {
    id: root
    visible: true
    title: "FRET lifetime analyzer"

    property alias backend: backend

    ColumnLayout {
        id: rootLayout
        anchors.fill: parent
        anchors.margins: 5

        RowLayout {
            ToolButton {
                icon.name: "document-open"
                onClicked: {
                    saveFileDialog.selectExisting = true
                    saveFileDialog.open()
                }
            }
            ToolButton {
                icon.name: "document-save"
                onClicked: {
                    saveFileDialog.selectExisting = false
                    saveFileDialog.open()
                }
            }
            ToolSeparator {}
            TabBar {
                id: actionTab
                Layout.fillWidth: true
                TabButton { text: "Channels" }
                TabButton { text: "Datasets" }
                TabButton { text: "Registration" }
                TabButton { text: "Bleed-through" }
                TabButton { text: "Locate" }
                TabButton { text: "Track" }
                TabButton { text: "Filter" }
                TabButton { text: "Results" }
            }
        }

        StackLayout {
            currentIndex: actionTab.currentIndex

            ColumnLayout {
                Sdt.FrameSelector {
                    id: frameSel
                    showTypeSelector: false
                    excitationSeq: backend.excitationSeq
                    Layout.fillWidth: true
                }
                Item { height: 5 }
                Sdt.ChannelConfig {
                    id: channelConfig
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    channels: backend.channels
                    onChannelsModified: { backend.channels = channels }
                }
            }
            Sdt.MultiDataCollector {
                id: dataCollector
                datasets: backend.datasets
                specialDatasets: backend.specialDatasets
                sourceNames: channelConfig.sourceCount
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Registrator {
                id: reg
                channels: backend.channels
                dataDir: backend.dataDir
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Item {}
            Locator {
                id: loc
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Tracker {
                id: track
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Filter {
                id: filter
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
    Backend {
        id: backend
        excitationSeq: frameSel.excitationSeq
        locAlgorithm: loc.algorithm
        onLocAlgorithmChanged: { loc.algorithm = locAlgorithm }
        locOptions: loc.options
        onLocOptionsChanged: { loc.options = locOptions }
        trackOptions: track.options
        onTrackOptionsChanged: { track.options = trackOptions }
        filterOptions: filter.options
        onFilterOptionsChanged: { filter.options = filterOptions }
    }
    Settings {
        id: settings
        category: "Window"
        property int width: 640
        property int height: 400
    }
    Dialog {
        id: batchDialog
        title: "Locating…"
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
            dataset: backend
            argRoles: ["fretImage"]
            resultRole: "locData"
        }

        onRejected: { batchWorker.abort() }
    }
    Dialog {
        id: trackBatchDialog
        title: "Tracking…"
        anchors.centerIn: parent
        closePolicy: Popup.NoAutoClose
        modal: true
        footer: DialogButtonBox {
            Button {
                text: (trackBatchWorker.progress == trackBatchWorker.count ?
                       "OK" : "Abort")
                DialogButtonBox.buttonRole: (
                    trackBatchWorker.progress == trackBatchWorker.count ?
                    DialogButtonBox.AcceptRole : DialogButtonBox.RejectRole
                )
            }
        }

        Sdt.BatchWorker {
            id: trackBatchWorker
            anchors.fill: parent
            dataset: backend
            argRoles: ["locData"]
            resultRole: "locData"
        }

        onRejected: { trackBatchWorker.abort() }
    }
    QQDialogs.FileDialog {
        id: saveFileDialog
        selectMultiple: false
        nameFilters: ["YAML savefile (*.yaml)", "All files (*)"]
        onAccepted: {
            if (selectExisting)
                backend.load(fileUrl)
            else
                backend.save(fileUrl)
        }
    }
    Component.onCompleted: {
        width = settings.width
        height = settings.height
    }
    onClosing: {
        loc.previewEnabled = false
        settings.setValue("width", width)
        settings.setValue("height", height)
    }
}
