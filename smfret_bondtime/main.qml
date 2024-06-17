import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.3 as QQDialogs
import QtQuick.Layouts 1.15
import Qt.labs.settings 1.0
import SdtGui 0.2 as Sdt
import BindingTime 1.0


ApplicationWindow {
    id: window
    visible: true
    title: ("Bond lifetime analyzer" +
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
                TabButton { text: "Changepoints" }
                TabButton { text: "Filter" }
            }
        }

        StackLayout {
            id: mainStack

            ColumnLayout {
                Sdt.FrameSelector {
                    id: frameSel
                    showTypeSelector: false
                    excitationSeq: imagePipe.excitationSeq
                    onExcitationSeqChanged: {
                        imagePipe.excitationSeq = excitationSeq
                    }
                    Layout.fillWidth: true
                }
                Item { height: 5 }
                Sdt.ChannelConfig {
                    id: channelConfig
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    channels: imagePipe.channels
                    onChannelsChanged: {
                        imagePipe.channels = channels
                    }
                }
            }
            ColumnLayout {
                Sdt.DirSelector {
                    id: dataDirSel
                    label: "Data folder:"
                    dataDir: backend.dataDir
                    onDataDirChanged: { backend.dataDir = dataDir }
                    Layout.fillWidth: true
                }
                Sdt.MultiDataCollector {
                    id: dataCollector
                    datasets: backend.datasets
                    sourceNames: channelConfig.sourceNames
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    dataDir: backend.dataDir
                }
            }
            Sdt.Registrator {
                id: reg
                dataset: backend.registrationDataset
                channels: imagePipe.channels
                registrator: imagePipe.registrator
                onRegistratorChanged: { imagePipe.registrator = registrator }
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
                        background: imagePipe.bleedThrough.background
                        onBackgroundChanged: {
                            var bt = imagePipe.bleedThrough
                            bt.background = background
                            imagePipe.bleedThrough = bt
                        }
                        factor: imagePipe.bleedThrough.factor
                        onFactorChanged: {
                            var bt = imagePipe.bleedThrough
                            bt.factor = factor
                            imagePipe.bleedThrough = bt
                        }
                        smooth: imagePipe.bleedThrough.smooth
                        onSmoothChanged: {
                            var bt = imagePipe.bleedThrough
                            bt.smooth = smooth
                            imagePipe.bleedThrough = bt
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
                        /*Button {
                            Layout.fillWidth: true
                            text: "Add extra frames…"
                        }*/
                    }
                    Changepoints {
                        id: changepoints

                        timeTraceFig: timeTraceFig
                        datasets: backend.datasets

                        onPreviewFrameNumberChanged: {
                            imSel.currentFrame = previewFrameNumber
                        }

                        Connections {
                            target: imSel
                            function onCurrentFrameChanged() {
                                changepoints.previewFrameNumber = imSel.currentFrame
                            }
                            function onCurrentFrameCountChanged() {
                                changepoints.frameCount = imSel.currentFrameCount
                            }
                        }
                    }
                    ScrollView {
                        Filter {
                            id: filter
                            datasets: backend.datasets
                            timeTraceFig: timeTraceFig
                            onPreviewFrameNumberChanged: {
                                imSel.currentFrame = previewFrameNumber
                            }

                            Connections {
                                target: imSel
                                function onCurrentFrameChanged() {
                                    filter.previewFrameNumber = imSel.currentFrame
                                }
                                function onCurrentFrameCountChanged() {
                                    filter.frameCount = imSel.currentFrameCount
                                }
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
                                // textRole: "key"
                                currentChannel: "corrAcceptor"
                                Layout.fillWidth: true
                                imagePipeline: imagePipe
                            }
                        }
                        Sdt.ImageDisplay {
                            id: imDisp
                            image: imSel.image
                            error: imSel.error
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
                    currentChannel: bt.imageRole
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
                name: "changepoints"
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
                    overlays: changepoints.overlays
                }
                PropertyChanges {
                    target: timeTraceFig
                    visible: true
                }
                PropertyChanges {
                    target: changepoints
                    trackData: imSel.dataset.get(imSel.currentIndex, "locData")
                }
                PropertyChanges {
                    target: imSel
                    currentChannel: "corrAcceptor"
                }
            },
            State {
                name: "filter"
                when: actionTab.currentIndex == 7
                PropertyChanges {
                    target: mainStack
                    currentIndex: 3
                }
                PropertyChanges {
                    target: previewStack
                    currentIndex: 4
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
                    currentFrameCount: imSel.currentFrameCount
                }
                PropertyChanges {
                    target: imSel
                    currentChannel: "corrAcceptor"
                }
            }
        ]
    }
    Backend {
        id: backend
        imagePipeline: imagePipe
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
        filterOptions: {
            "mass_thresh": filter.massThresh,
            "bg_thresh": filter.bgThresh,
            "min_length": filter.minLength,
            "min_changepoints": filter.minChangepoints,
            "max_changepoints": filter.maxChangepoints,
            "start_end_changepoints": filter.startEndChangepoints
        }
        onFilterOptionsChanged: {
            var o = filterOptions
            filter.massThresh = o.mass_thresh
            filter.bgThresh = o.bg_thresh
            filter.minLength = o.min_length != undefined ? o.min_length : 2
            filter.minChangepoints = (o.min_changepoints != undefined ?
                                      o.min_changepoints : 1)
            filter.maxChangepoints = (o.max_changepoints != undefined ?
                                      o.max_changepoints : 2)
            filter.startEndChangepoints = (o.start_end_changepoints != undefined ?
                                           o.start_end_changepoints : true)
        }
        changepointOptions: {"penalty": changepoints.penalty}
        onChangepointOptionsChanged: {
            var o = changepointOptions
            changepoints.penalty = o.penalty
        }
        registrationLocOptions: reg.locateSettings
        onRegistrationLocOptionsChanged: { reg.locateSettings = registrationLocOptions }
    }
    LifetimeImagePipeline {
        id: imagePipe
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
