from PyQt5 import QtCore, QtQml, QtQuick
import numpy as np
from sdt import gui


class TrackNavigator(QtQuick.QQuickItem):
    _invalidTrackInfo = {"start": -1, "end": -1, "mass": float("NaN"),
                         "bg": float("NaN"), "bg_dev": float("NaN"),
                         "length": 0, "status": "undefined"}
    _statusMap = {-1: "undecided", 0: "accepted", 1: "rejected"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trcList = []
        self._trackData = None
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
            self._trackList = []
        else:
            self._trcList = np.sort(self._trackData["particle"].unique()
                                    ).tolist()
        self.trackDataChanged.emit()
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
        if self._trackData is None or t < 0:
            ftd = None
            self._currentTrackData = None
            self._currentTrackInfo = self._invalidTrackInfo
        else:
            ftd = self._trackData[self._trackData["particle"] == t
                                  ].sort_values("frame")
            if not (len(ftd)):
                self._currentTrackData = None
                self._currentTrackInfo = self._invalidTrackInfo
            else:
                self._currentTrackData = ftd
                try:
                    td = ftd[ftd["extra_frame"] == 0]
                except KeyError:
                    td = ftd
                f = td["frame"].to_numpy()
                start = int(f[0])
                end = int(f[-1])
                status = (self._statusMap[td["filter_manual"].iloc[0]]
                          if "filter_manual" in td
                          else None)
                self._currentTrackInfo = {
                    "start": start, "end": end,
                    "mass": float(td["mass"].mean()),
                    "bg": float(td["bg"].mean()),
                    "bg_dev": float(td["bg_dev"].mean()), "length": len(td),
                    "status": status}
        self.currentTrackNoChanged.emit()
        self.currentTrackDataChanged.emit()
        self.currentTrackInfoChanged.emit()


QtQml.qmlRegisterType(
    TrackNavigator, "SmFretBondTime.Templates", 1, 0, "TrackNavigator"
)
