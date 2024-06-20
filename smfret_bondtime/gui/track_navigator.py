# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

from PyQt5 import QtCore, QtQml, QtQuick
import numpy as np
from sdt import gui


class TrackNavigator(QtQuick.QQuickItem):
    _invalidTrackInfo = {
        "start": -1,
        "end": -1,
        "mass": float("NaN"),
        "bg": float("NaN"),
        "length": 0,
        "status": "undefined",
    }
    _statusMap = {-1: "undecided", 0: "accepted", 1: "rejected"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trcList = []
        self._trackData = None
        self._trackStats = None
        self._currentTrackNo = -1
        self._currentTrackData = None
        self._currentTrackInfo = self._invalidTrackInfo

    currentTrackData = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    currentTrackInfo = gui.SimpleQtProperty("QVariantMap", readOnly=True)

    trackAccepted = QtCore.pyqtSignal(int, arguments=["trackNo"])
    trackRejected = QtCore.pyqtSignal(int, arguments=["trackNo"])

    trackDataChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=trackDataChanged)
    def trackData(self):
        return self._trackData

    @trackData.setter
    def trackData(self, t):
        if t is self._trackData:
            return
        self._trackData = t
        if t is None:
            self._currentTrackData = None
        else:
            self._currentTrackData = self._trackData[
                self._trackData["particle"] == self.currentTrackNo
            ].sort_values("frame")
        self.trackDataChanged.emit()
        self.currentTrackDataChanged.emit()

    trackStatsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariant", notify=trackStatsChanged)
    def trackStats(self):
        return self._trackStats

    @trackStats.setter
    def trackStats(self, s):
        if s is self._trackStats:
            return
        self._trackStats = s
        if s is None:
            self._trcList = []
        else:
            self._trcList = np.sort(self._trackStats.index).tolist()
        self.trackStatsChanged.emit()
        self._trackNoListChanged.emit()

    _trackNoListChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(list, notify=_trackNoListChanged)
    def _trackNoList(self):
        return self._trcList

    currentTrackNoChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(int, notify=currentTrackNoChanged)
    def currentTrackNo(self):
        return self._currentTrackNo

    @currentTrackNo.setter
    def currentTrackNo(self, t):
        if self._currentTrackNo == t:
            return
        self._currentTrackNo = t
        try:
            s = self._trackStats.loc[t]
            self._currentTrackInfo = {
                "start": int(s.get("start", -1)),
                "end": int(s.get("end", -1)),
                "mass": float(s.get("mass", "NaN")),
                "bg": float(s.get("bg", "NaN")),
                "length": int(s.get("track_len", 0)),
                "status": self._statusMap.get(s.get("filter_manual", ""), "undefined"),
            }
            if self._trackData is not None:
                self._currentTrackData = self._trackData[
                    self._trackData["particle"] == t
                ].sort_values("frame")
        except (KeyError, AttributeError):
            # t is not in self._trackStats or self._trackStats is None
            self._currentTrackInfo = self._invalidTrackInfo
            self._currentTrackData = None
        self.currentTrackNoChanged.emit()
        self.currentTrackDataChanged.emit()
        self.currentTrackInfoChanged.emit()


QtQml.qmlRegisterType(
    TrackNavigator, "SmFretBondTime.Templates", 1, 0, "TrackNavigator"
)
