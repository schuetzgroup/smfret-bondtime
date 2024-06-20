// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SdtGui 0.2 as Sdt
import SmFretBondTime.Templates 1.0 as T


T.Changepoints {
    id: root

    property list<Item> overlays: [
        Sdt.TrackDisplay {
            trackData: nav.trackData
            currentFrame: previewFrameNumber
            color: "yellow"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        },
        Sdt.TrackDisplay {
            trackData: nav.currentTrackData
            currentFrame: previewFrameNumber
            color: "#8080ff"
            showLoc: locPreviewCheck.checked
            showTracks: trackPreviewCheck.checked
            markerSize: 3.0
        }
    ]
    property alias penalty: penaltyBox.value
    property alias previewFrameNumber: nav.previewFrameNumber
    property alias frameCount: nav.frameCount
    property alias trackData: nav.trackData
    property alias trackStats: nav.trackStats
    property alias currentTrackData: nav.currentTrackData
    property alias currentTrackInfo: nav.currentTrackInfo
    property Item timeTraceFig: null

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    onCurrentTrackDataChanged: findChangepoints()
    onPenaltyChanged: findChangepoints()

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
            }
        }
        GroupBox {
            id: changepointGroup

            Layout.fillWidth: true
            title: "changepoint detection"

            GridLayout {
                anchors.fill: parent
                columns: 2

                Label { text: "penalty" }
                Sdt.EditableSpinBox {
                    id: penaltyBox
                    Layout.fillWidth: true
                    from: 0
                    to: 1000000000
                    stepSize: 100000
                    value: 1000000
                    down.indicator.visible: false
                    down.indicator.width: 0
                    up.indicator.visible: false
                    up.indicator.width: 0
                }
            }
        }
        GroupBox {
            id: navigationGroup

            Layout.fillWidth: true
            title: "navigation"

            focusPolicy: Qt.StrongFocus

            TrackNavigator {
                id: nav
                anchors.fill: parent
            }
        }
        Button {
            text: "Process all…"
            Layout.fillWidth: true
            onClicked: {
                batchWorker.func = backend.getChangepointFunc()
                batchWorker.start()
                batchDialog.open()
            }
        }
        Item { Layout.fillHeight: true }
    }

    Dialog {
        id: batchDialog
        title: "Finding changepoints…"
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.NoAutoClose
        modal: true
        footer: DialogButtonBox {
            Button {
                text: batchWorker.isRunning ? "Abort" : "OK"
                DialogButtonBox.buttonRole: (batchWorker.isRunning ?
                                             DialogButtonBox.RejectRole :
                                             DialogButtonBox.AcceptRole)
            }
        }

        Sdt.BatchWorker {
            id: batchWorker
            anchors.fill: parent
            dataset: root.datasets
            argRoles: ["locData", "trackStats"]
            resultRoles: ["locData", "trackStats"]
            displayRole: "source_0"
            errorPolicy: Sdt.BatchWorker.ErrorPolicy.Abort
        }

        onRejected: { batchWorker.abort() }
    }
}

