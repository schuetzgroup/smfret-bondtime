# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

from PyQt5 import QtCore, QtQuick, QtQml
from sdt import changepoint, gui


class Changepoints(QtQuick.QQuickItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._datasets = None

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    penalty = gui.QmlDefinedProperty()
    currentTrackData = gui.QmlDefinedProperty()
    currentTrackInfo = gui.QmlDefinedProperty()
    timeTraceFig = gui.QmlDefinedProperty()

    @QtCore.pyqtSlot()
    def findChangepoints(self):
        if self.timeTraceFig is None or self.currentTrackData is None:
            return

        d = self.currentTrackData["mass"].to_numpy()
        cp = changepoint.Pelt().find_changepoints(d, self.penalty)

        fig = self.timeTraceFig.figure
        fig.set_constrained_layout(True)
        try:
            ax = fig.axes[0]
        except IndexError:
            ax = fig.add_subplot()
        ax.cla()
        changepoint.plot_changepoints(d, cp, time=self.currentTrackData["frame"], ax=ax)
        ax.set_ylim(d.min(), d.max())
        ax.axvline(self.currentTrackInfo["start"], color="g")
        ax.axvline(self.currentTrackInfo["end"], color="r")
        ax.set_xlabel("frame")
        ax.set_ylabel("intensity")
        fig.canvas.draw_idle()


QtQml.qmlRegisterType(Changepoints, "SmFretBondTime.Templates", 1, 0, "Changepoints")
