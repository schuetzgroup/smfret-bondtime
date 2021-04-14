import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Dialogs 1.3 as QQDialogs
import QtQuick.Layouts 1.12
import Qt.labs.settings 1.0
import SdtGui 0.1 as Sdt
import BindingTime 1.0


ApplicationWindow {
    id: window
    visible: true
    title: "FRET lifetime analyzer"

    property alias backend: backend

    ColumnLayout {
        id: windowLayout
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
            currentIndex: {
                var idx = actionTab.currentIndex
                if (idx <= 2)
                    idx
                else if ((3 <= idx) && (idx <= 6))
                    3
                else if (idx >= 7)
                    idx - 3
            }

            ColumnLayout {
                Sdt.FrameSelector {
                    id: frameSel
                    showTypeSelector: false
                    excitationSeq: backend.datasets.excitationSeq
                    onExcitationSeqChanged: {
                        backend.datasets.excitationSeq = excitationSeq
                    }
                    Layout.fillWidth: true
                }
                Item { height: 5 }
                Sdt.ChannelConfig {
                    id: channelConfig
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    channels: backend.datasets.channels
                    onChannelsModified: {
                        backend.datasets.channels = channels
                        backend.specialDatasets.channels = channels
                    }
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
            Sdt.Registrator {
                id: reg
                dataset: backend.registrationDataset
                channelRoles: Object.keys(dataset.channels)
                registrator: backend.datasets.registrator
                onRegistratorChanged: { backend.datasets.registrator = registrator }
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                RowLayout {
                    anchors.fill: parent

                    Item {
                        Layout.fillHeight: true
                        implicitWidth: previewStack.implicitWidth
                        implicitHeight: previewStack.implicitHeight

                        StackLayout {
                            id: previewStack

                            anchors.fill: parent

                            property var indexMap: {
                                3: 0,  // bleed-through
                                4: 1,  // locate
                                5: 2,  // track
                                6: 3,  // filter
                            }
                            property Item currentItem: itemAt(currentIndex)

                            currentIndex: indexMap[actionTab.currentIndex] || 0

                            BleedThrough {
                                id: bt
                                background: backend.datasets.background
                                onBackgroundChanged: { backend.datasets.background = background }
                                bleedThrough: backend.datasets.bleedThrough
                                onBleedThroughChanged: { backend.datasets.bleedThrough = bleedThrough }
                            }
                            Locator {
                                id: loc
                                datasets: backend.datasets
                                previewImage: visible ? imSel.image : null
                            }
                            Tracker {
                                id: track
                                datasets: backend.datasets
                                previewData: (
                                    visible ?
                                    imSel.dataset.get(imSel.currentIndex, "locData") :
                                    null
                                )
                                previewFrameNumber: imSel.currentFrame
                            }
                            Filter {
                                id: filter
                                datasets: backend.datasets
                                trackData: (
                                    visible ?
                                    imSel.dataset.get(imSel.currentIndex, "locData") :
                                    null
                                )
                                previewFrameNumber: imSel.currentFrame
                                imageSequence: (
                                    visible ?
                                    imSel.dataset.get(imSel.currentIndex, "corrAcceptor") :
                                    null
                                )
                            }
                        }
                    }
                    Item { width: 2 }
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ColumnLayout {
                            anchors.fill: parent
                            RowLayout {
                                Label { text: "dataset" }
                                Sdt.DatasetSelector {
                                    id: datasetSel
                                    datasets: backend.datasets
                                }
                                Item { width: 5 }
                                Sdt.ImageSelector {
                                    id: imSel
                                    editable: false
                                    dataset: datasetSel.currentDataset
                                    textRole: "key"
                                    imageRole: previewStack.currentItem.imageRole || "corrAcceptor"
                                    Layout.fillWidth: true
                                }
                            }
                            Sdt.ImageDisplay {
                                id: imDisp
                                image: imSel.image
                                overlays: previewStack.currentItem.overlays || []
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                            }
                        }
                    }
                }
            }
            Results {
                id: results
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
    Backend {
        id: backend
        locAlgorithm: loc.algorithm
        onLocAlgorithmChanged: { loc.algorithm = locAlgorithm }
        locOptions: loc.options
        onLocOptionsChanged: { loc.options = locOptions }
        trackOptions: {"search_range": track.searchRange, "memory": track.memory}
        onTrackOptionsChanged: {
            // If setting `track`'s properties directly from trackOptions,
            // there is a problem: setting searchRange updates trackOptions,
            // overwriting all other new entries with the old ones. Thus assign
            // to a variable first, which is not updated when setting properties.
            var opts = trackOptions
            track.searchRange = opts.search_range
            track.memory = opts.memory
        }
        filterOptions: {"filter_initial": filter.filterInitial,
                        "filter_terminal": filter.filterTerminal,
                        "mass_thresh": filter.massThresh,
                        "bg_thresh": filter.bgThresh}
        onFilterOptionsChanged: {
            var o = filterOptions
            filter.filterInitial = o.filter_initial
            filter.filterTerminal = o.filter_terminal
            filter.massThresh = o.mass_thresh
            filter.bgThresh = o.bg_thresh
        }
        registrationLocOptions: reg.locateSettings
        onRegistrationLocOptionsChanged: { reg.locateSettings = registrationLocOptions }
    }
    Settings {
        id: settings
        category: "Window"
        property int width: 640
        property int height: 400
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
