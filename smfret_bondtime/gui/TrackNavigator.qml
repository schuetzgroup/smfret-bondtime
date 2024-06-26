// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SdtGui 0.2 as Sdt
import SmFretBondTime.Templates 1.0 as T


T.TrackNavigator {
    id: root

    property int previewFrameNumber: -1
    property int frameCount: 0
    property bool showStatistics: false
    property bool cull: false

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    Keys.onPressed: (event) => {
        switch (event.key) {
            case Qt.Key_Left:
                prevFrameAction.trigger()
                event.accepted = true
                break
            case Qt.Key_Right:
                nextFrameAction.trigger()
                event.accepted = true
                break
            case Qt.Key_Up:
                firstFrameAction.trigger()
                event.accepted = true
                break
            case Qt.Key_Down:
                lastFrameAction.trigger()
                event.accepted = true
                break
            case Qt.Key_PageUp:
                trackSel.increase()
                event.accepted = true
                break
            case Qt.Key_PageDown:
                trackSel.decrease()
                event.accepted = true
                break
            case Qt.Key_Return:
            case Qt.Key_Enter:
                acceptAction.trigger()
                event.accepted = true
                break
            case Qt.Key_Backspace:
            case Qt.Key_Delete:
                rejectAction.trigger()
                event.accepted = true
                break
        }
    }

    GridLayout {
        id: rootLayout
        anchors.fill: parent
        columns: 2

        Switch {
            id: firstFrameCheck
            text: "go to first frame"
            checked: true
            Layout.columnSpan: 2
        }
        Label {
            text: "track"
            Layout.fillWidth: true
        }
        SpinBox {
            id: trackSel
            contentItem: ComboBox {
                editable: true
                model: root._trackNoList
                onCurrentTextChanged: { updateCurrentTrack() }
                onModelChanged: { updateCurrentTrack() }

                function updateCurrentTrack() {
                    var n = model[currentIndex]
                    root.currentTrackNo = n == undefined ? -1 : n
                    parent.value = currentIndex
                    if (firstFrameCheck.checked)
                        root.previewFrameNumber = root.currentTrackInfo.start
                }
            }
            padding: 0
            to: contentItem.model.length - 1
            onValueChanged: { contentItem.currentIndex = value }
        }
        Label { text: "frame"}
        Row {
            ToolButton {
                action: firstFrameAction
                width: (trackSel.width - frameNavSep.width) / 4
            }
            ToolButton {
                action: lastFrameAction
                width: (trackSel.width - frameNavSep.width) / 4
            }
            ToolSeparator {
                id: frameNavSep
                anchors.verticalCenter: parent.verticalCenter
            }
            ToolButton {
                action: prevFrameAction
                width: (trackSel.width - frameNavSep.width) / 4
            }
            ToolButton {
                action: nextFrameAction
                width: (trackSel.width - frameNavSep.width) / 4
            }
        }
        Label {
            text: "action"
            visible: root.cull
        }
        Row {
            visible: root.cull
            ToolButton {
                action: acceptAction
                width: (trackSel.width - actionSep.width) / 2
            }
            ToolSeparator {
                id: actionSep
                anchors.verticalCenter: parent.verticalCenter
            }
            ToolButton {
                action: rejectAction
                width: (trackSel.width - actionSep.width) / 2
            }
        }
        Label {
            text: "intensity"
            visible: root.showStatistics
        }
        Label {
            text: root.currentTrackInfo.mass.toFixed(0)
            visible: root.showStatistics
        }
        Label {
            text: "background"
            visible: root.showStatistics
        }
        Label {
            text: root.currentTrackInfo.bg.toFixed(0)
            visible: root.showStatistics
        }
        Label {
            text: "length"
            visible: root.showStatistics
        }
        Label {
            text: root.currentTrackInfo.length
            visible: root.showStatistics
        }
        Label {
            text: "status"
            visible: root.showStatistics && root.currentTrackInfo.status
        }
        Label {
            text: root.currentTrackInfo.status
            visible: root.showStatistics && root.currentTrackInfo.status
        }
        Switch {
            id: kbdSwitch
            Layout.columnSpan: 2
            text: "keyboard control"
            checked: root.activeFocus
            onCheckedChanged: { root.focus = checked }
        }
    }

    Action {
        id: prevFrameAction
        icon.name: "go-previous"
        enabled: root.previewFrameNumber > 0
        onTriggered: { root.previewFrameNumber -= 1 }
    }
    Action {
        id: nextFrameAction
        icon.name: "go-next"
        enabled: root.previewFrameNumber < root.frameCount - 1
        onTriggered: { root.previewFrameNumber += 1 }
    }
    Action {
        id: firstFrameAction
        icon.name: "go-first"
        onTriggered: { root.previewFrameNumber = root.currentTrackInfo.start }
    }
    Action {
        id: lastFrameAction
        icon.name: "go-last"
        onTriggered: { root.previewFrameNumber = root.currentTrackInfo.end }
    }
    Action {
        id: acceptAction
        icon.name: "dialog-ok-apply"
        icon.color: "green"
        onTriggered: {
            if (root.currentTrackNo >= 0) {
                root.trackAccepted(root.currentTrackNo)
                trackSel.increase()
            }
        }
        enabled: root.currentTrackNo >= 0
    }
    Action {
        id: rejectAction
        icon.name: "dialog-cancel"
        icon.color: "red"
        onTriggered: {
            if (root.currentTrackNo >= 0) {
                root.trackRejected(root.currentTrackNo)
                trackSel.increase()
            }
        }
        enabled: root.currentTrackNo >= 0
    }
}

