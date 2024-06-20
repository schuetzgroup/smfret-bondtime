// SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
//
// SPDX-License-Identifier: BSD-3-Clause

import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.12
import SdtGui 0.2 as Sdt


Item {
    id: root

    property var datasets
    property alias algorithm: loc.algorithm
    property alias options: loc.options
    property alias previewEnabled: loc.previewEnabled
    property Item overlays: Sdt.LocDisplay { locData: loc.locData }
    property var previewImage: null

    implicitWidth: rootLayout.implicitWidth
    implicitHeight: rootLayout.implicitHeight

    ColumnLayout {
        id: rootLayout

        anchors.fill: parent

        Sdt.LocOptions {
            id: loc
            image: previewImage
            Layout.alignment: Qt.AlignTop
            Layout.fillHeight: true
        }
        Button {
            text: "Locate all…"
            Layout.fillWidth: true
            onClicked: {
                batchWorker.func = backend.getLocateFunc()
                batchWorker.start()
                batchDialog.open()
            }
        }
    }
    Dialog {
        id: batchDialog
        title: "Locating…"
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
            argRoles: root.datasets.fileRoles
            resultRoles: ["locData"]
            displayRole: root.datasets.fileRoles[0]
            errorPolicy: Sdt.BatchWorker.ErrorPolicy.Abort
        }

        onRejected: { batchWorker.abort() }
    }
}
