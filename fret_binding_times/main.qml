import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.3 as QQDialogs
import QtQuick.Layouts 1.15
import Qt.labs.settings 1.0
import SdtGui 0.1 as Sdt
import BindingTime 1.0


ApplicationWindow {
    id: window
    visible: true
    title: ("FRET lifetime analyzer" +
            (backend.saveFile.toString().length ?
             (" – " + Sdt.Sdt.urlToLocalFile(backend.saveFile)) : ""))

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
                    if (!backend.saveFile.toString().length) {
                        saveFileDialog.selectExisting = false
                        saveFileDialog.open()
                    } else {
                        backend.save(backend.saveFile)
                    }
                }
            }
            ToolButton {
                icon.name: "document-save-as"
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
            id: mainStack

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

            RowLayout {
                StackLayout {
                    id: previewStack

                    Layout.fillWidth: false
                    Layout.fillHeight: true
                    // not sure why this is needed, but otherwise implicitWidth
                    // is 0... (Qt 5.15.6)
                    implicitWidth: Math.max(bt.implicitWidth, loc.implicitWidth,
                                            track.implicitWidth, filter.implicitWidth)

                    BleedThrough {
                        id: bt
                        background: backend.datasets.bleedThrough.background
                        onBackgroundChanged: {
                            var bt = backend.datasets.bleedThrough
                            bt.background = background
                            backend.datasets.bleedThrough = bt
                        }
                        factor: backend.datasets.bleedThrough.factor
                        onFactorChanged: {
                            var bt = backend.datasets.bleedThrough
                            bt.factor = factor
                            backend.datasets.bleedThrough = bt
                        }
                        smooth: backend.datasets.bleedThrough.smooth
                        onSmoothChanged: {
                            var bt = backend.datasets.bleedThrough
                            bt.smooth = smooth
                            backend.datasets.bleedThrough = bt
                        }
                    }
                    Locator {
                        id: loc
                        datasets: backend.datasets
                        previewImage: visible ? imSel.image : null
                    }
                    ColumnLayout {
                        RowLayout {
                            Label {
                                text: "extra pre/post frames"
                                Layout.fillWidth: true
                            }
                            SpinBox {
                                id: extraBox
                                from: 0
                                to: 999
                            }
                        }
                        Tracker {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            id: track
                            datasets: backend.datasets
                            previewData: (
                                visible ?
                                imSel.dataset.get(imSel.currentIndex, "locData") :
                                null
                            )
                            previewFrameNumber: imSel.currentFrame
                        }
                    }
                    Filter {
                        id: filter
                        datasets: backend.datasets
                        frameCount: imSel.currentFrameCount
                        timeTraceFig: timeTraceFig
                        onPreviewFrameNumberChanged: {
                            imSel.currentFrame = previewFrameNumber
                        }

                        Connections {
                            target: imSel
                            function onCurrentFrameChanged() {
                                filter.previewFrameNumber = imSel.currentFrame
                            }
                        }
                    }
                }
                Item { width: 2 }
                SplitView {
                    id: split

                    orientation: Qt.Vertical
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        SplitView.fillHeight: true

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
                                imageRole: "corrAcceptor"
                                Layout.fillWidth: true
                            }
                        }
                        Sdt.ImageDisplay {
                            id: imDisp
                            image: imSel.image
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                        }
                    }
                    Sdt.FigureCanvasAgg {
                        id: timeTraceFig
                        SplitView.preferredHeight: split.height / 4.0
                        visible: false
                    }
                }
            }

            Results {
                id: results

                minLength: filter.minLength
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }

        states: [
            State {
                name: "channelSetup"
                when: actionTab.currentIndex == 0
                PropertyChanges {
                    target: mainStack
                    currentIndex: 0
                }
            },
            State {
                name: "datasetSetup"
                when: actionTab.currentIndex == 1
                PropertyChanges {
                    target: mainStack
                    currentIndex: 1
                }
            },
            State {
                name: "registrationSetup"
                when: actionTab.currentIndex == 2
                PropertyChanges {
                    target: mainStack
                    currentIndex: 2
                }
            },
            State {
                name: "bleedthroughSetup"
                when: actionTab.currentIndex == 3
                PropertyChanges {
                    target: mainStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: previewStack
                    currentIndex: 0
                }
                PropertyChanges {
                    target: imSel
                    imageRole: bt.imageRole
                }
            },
            State {
                name: "locate"
                when: actionTab.currentIndex == 4
                PropertyChanges {
                    target: mainStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: previewStack
                    currentIndex: 1
                }
                PropertyChanges {
                    target: imDisp
                    overlays: loc.overlays
                }
            },
            State {
                name: "track"
                when: actionTab.currentIndex == 5
                PropertyChanges {
                    target: mainStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: previewStack
                    currentIndex: 2
                }
                PropertyChanges {
                    target: imDisp
                    overlays: track.overlays
                }
            },
            State {
                name: "filter"
                when: actionTab.currentIndex == 6
                PropertyChanges {
                    target: mainStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: previewStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: imDisp
                    overlays: filter.overlays
                }
                PropertyChanges {
                    target: timeTraceFig
                    visible: true
                }
                PropertyChanges {
                    target: filter
                    trackData: imSel.dataset.get(imSel.currentIndex, "locData")
                    imageSequence: imSel.dataset.get(imSel.currentIndex, "corrAcceptor")
                }
            },
            State {
                name: "results"
                when: actionTab.currentIndex == 7
                PropertyChanges {
                    target: mainStack
                    currentIndex: 4
                }
            }
        ]
    }
    Backend {
        id: backend
        locAlgorithm: loc.algorithm
        onLocAlgorithmChanged: { loc.algorithm = locAlgorithm }
        locOptions: loc.options
        onLocOptionsChanged: { loc.options = locOptions }
        trackOptions: {"search_range": track.searchRange,
                       "memory": track.memory,
                       "extra_frames": extraBox.value}
        onTrackOptionsChanged: {
            // If setting `track`'s properties directly from trackOptions,
            // there is a problem: setting searchRange updates trackOptions,
            // overwriting all other new entries with the old ones. Thus assign
            // to a variable first, which is not updated when setting properties.
            var opts = trackOptions
            track.searchRange = opts.search_range
            track.memory = opts.memory
            extraBox.value = opts.extra_frames
        }
        filterOptions: {"filter_initial": filter.filterInitial,
                        "filter_terminal": filter.filterTerminal,
                        "mass_thresh": filter.massThresh,
                        "bg_thresh": filter.bgThresh,
                        "min_length": filter.minLength}
        onFilterOptionsChanged: {
            var o = filterOptions
            filter.filterInitial = o.filter_initial
            filter.filterTerminal = o.filter_terminal
            filter.massThresh = o.mass_thresh
            filter.bgThresh = o.bg_thresh
            filter.minLength = o.min_length != undefined ? o.min_length : 2
        }
        registrationLocOptions: reg.locateSettings
        onRegistrationLocOptionsChanged: { reg.locateSettings = registrationLocOptions }
        fitOptions: {"fit_variable": results.fitVariable,
                     "min_count": results.minCount}
        onFitOptionsChanged: {
            var o = fitOptions
            results.fitVariable = o.fit_variable
            results.minCount = o.min_count
        }
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
        folder: Sdt.Sdt.parentUrl(backend.saveFile)
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
