// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SdtGui 0.2 as Sdt
import SmFretBondTime.Templates 1.0 as T


T.Filter {
    id: root

    property int previewFrameNumber: -1
    property list<Item> overlays: [
        Sdt.TrackDisplay {
            trackData: root.manualAccepted
            currentFrame: previewFrameNumber
            color: "Lime"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.manualUndecided
            currentFrame: previewFrameNumber
            color: "yellow"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.manualRejected
            currentFrame: previewFrameNumber
            color: "red"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: root.paramRejected
            currentFrame: previewFrameNumber
            color: "gray"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
            visible: showParamCheck.checked
        },
        Sdt.TrackDisplay {
            trackData: root.currentTrackData
            currentFrame: previewFrameNumber
            color: "#8080ff"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        }
    ]
    property alias massThresh: massThreshSel.value
    property alias bgThresh: bgThreshSel.value
    property alias minLength: minLengthSel.value
    property alias minChangepoints: minChangepointsSel.value
    property alias maxChangepoints: maxChangepointsSel.value
    property alias startEndChangepoints: startEndChangepointsCheck.checked
    property Item timeTraceFig: null
    property alias previewFrameNumber: nav.previewFrameNumber
    property alias frameCount: nav.frameCount
    property alias currentTrackData: nav.currentTrackData
    property alias currentTrackInfo: nav.currentTrackInfo

    showManual: showManualSel.currentIndex  // private property

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    onCurrentTrackDataChanged: updatePlot()

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent
        spacing: 7

        GroupBox {
            title: "display options"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent

                Switch {
                    id: locPreviewCheck
                    text: "show localizations"
                    checked: true
                }
                Switch {
                    id: trackPreviewCheck
                    text: "show tracks"
                    checked: false
                }
                Switch {
                    id: showParamCheck
                    text: "show parametrically rejected"
                    checked: false
                }
                RowLayout {
                    Label { text: "manually filtered" }
                    ComboBox {
                        id: showManualSel
                        model: ["all", "undecided", "accepted", "rejected"]
                    }
                }
            }
        }
        GroupBox {
            title: "parametric filter"
            Layout.fillWidth: true

            GridLayout {
                columns: 2
                anchors.fill: parent

                Label {
                    text: "max. background"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: bgThreshSel
                    from: 0
                    to: Sdt.Sdt.intMax
                    stepSize: 10
                    value: 1000
                }
                Label {
                    text: "min. intensity"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: massThreshSel
                    from: 0
                    to: Sdt.Sdt.intMax
                    // decimals: 0
                    stepSize: 100
                }
                Label {
                    text: "min. length"
                    Layout.fillWidth: true
                }
                Sdt.EditableSpinBox {
                    id: minLengthSel
                    from: 1
                    to: Sdt.Sdt.intMax
                    value: 2
                }
                Label {
                    text: "min. changepoints"
                    enabled: root.hasChangepoints
                }
                SpinBox {
                    id: minChangepointsSel
                    Layout.alignment: Qt.AlignRight
                    value: 1
                    enabled: root.hasChangepoints
                }
                Label {
                    text: "max. changepoints"
                    enabled: root.hasChangepoints
                }
                SpinBox {
                    id: maxChangepointsSel
                    Layout.alignment: Qt.AlignRight
                    value: 2
                    enabled: root.hasChangepoints
                }
                Switch {
                    id: startEndChangepointsCheck
                    text: "start/end count as changepoints"
                    checked: true
                    Layout.columnSpan: 2
                    enabled: root.hasChangepoints
                }
            }
        }
        GroupBox {
            id: manualGroup

            Layout.fillWidth: true
            title: "manual filter"

            TrackNavigator {
                id: nav
                cull: true
                showStatistics: true
                trackData: root.trackData
                trackStats: root.navigatorStats
                onTrackAccepted: root.acceptTrack(trackNo)
                onTrackRejected: root.rejectTrack(trackNo)
            }
        }
        Sdt.StatusDisplay { status: root.status }
        Item { Layout.fillHeight: true }
    }

    Component.onCompleted: { completeInit() }
}
