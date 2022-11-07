import functools
import operator

from PyQt5 import QtCore
import numpy as np
from sdt import gui


# TODO: No need to derive from OptionChooser since there are no intensive
# tasks that need to be done in a thread
class Filter(gui.OptionChooser):
    _invalidTrackInfo = {"start": -1, "end": -1, "mass": float("NaN"),
                         "bg": float("NaN"), "bg_dev": float("NaN"),
                         "length": 0, "status": "undefined"}

    _statusMap = {-1: "undecided", 0: "accepted", 1: "rejected"}

    def __init__(self, parent):
        super().__init__(
            argProperties=["trackData", "imageSequence", "filterInitial",
                           "filterTerminal", "bgThresh", "massThresh",
                           "minLength"],
            resultProperties=["paramAccepted", "paramRejected"],
            parent=parent)
        self._datasets = None
        self._trackData = None
        self._imageSequence = None
        self._paramAccepted = None
        self._paramRejected = None
        self._manualAccepted = None
        self._manualRejected = None
        self._manualUndecided = None
        self._currentTrack = None
        self._currentTrackInfo = self._invalidTrackInfo
        self._currentTrackNo = -1
        self._trackList = []

        self.paramAcceptedChanged.connect(self._updateTrackList)

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    trackData = gui.SimpleQtProperty(QtCore.QVariant, comp=operator.is_)
    imageSequence = gui.SimpleQtProperty(QtCore.QVariant)
    paramAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    paramRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualUndecided = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    currentTrack = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    currentTrackInfo = gui.SimpleQtProperty("QVariantMap", readOnly=True)
    trackList = gui.SimpleQtProperty(list, readOnly=True)
    filterInitial = gui.QmlDefinedProperty()
    filterTerminal = gui.QmlDefinedProperty()
    massThresh = gui.QmlDefinedProperty()
    bgThresh = gui.QmlDefinedProperty()
    minLength = gui.QmlDefinedProperty()
    timeTraceFig = gui.QmlDefinedProperty()

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
            self._currentTrack = None
            self._currentTrackInfo = self._invalidTrackInfo
        else:
            ftd = self._trackData[self._trackData["particle"] == t
                                  ].sort_values("frame")
            if not (len(ftd)):
                self._currentTrack = None
                self._currentTrackInfo = self._invalidTrackInfo
            else:
                self._currentTrack = ftd
                try:
                    td = ftd[ftd["extra_frame"] == 0]
                except KeyError:
                    td = ftd
                f = td["frame"].to_numpy()
                start = int(f[0])
                end = int(f[-1])
                self._currentTrackInfo = {
                    "start": start, "end": end,
                    "mass": float(td["mass"].mean()),
                    "bg": float(td["bg"].mean()),
                    "bg_dev": float(td["bg_dev"].mean()), "length": len(td),
                    "status": self._statusMap[td["filter_manual"].iloc[0]]}
        if ftd is not None and len(ftd) and self.timeTraceFig is not None:
            fig = self.timeTraceFig.figure
            fig.set_constrained_layout(True)
            try:
                ax = fig.axes[0]
            except IndexError:
                ax = fig.add_subplot()
            ax.cla()
            ax.plot(ftd["frame"], ftd["mass"])
            ax.axvline(start, color="g")
            ax.axvline(end, color="r")
            ax.set_xlabel("frame")
            ax.set_ylabel("intensity")
            fig.canvas.draw_idle()
        self.currentTrackNoChanged.emit()
        self.currentTrackChanged.emit()
        self.currentTrackInfoChanged.emit()

    @staticmethod
    def workerFunc(trackData, imageSequence, filterInitial, filterTerminal,
                   bgThresh, massThresh, minLength):
        if trackData is None or imageSequence is None:
            return None, None
        n_frames = len(imageSequence)
        trackData["filter_param"] = 0
        try:
            actual_td = trackData[trackData["extra_frame"] == 0]
        except KeyError:
            actual_td = trackData
        if filterInitial:
            bad_p = actual_td.loc[actual_td["frame"] == 0, "particle"].unique()
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        if filterTerminal:
            bad_p = actual_td.loc[actual_td["frame"] == n_frames - 1,
                                  "particle"].unique()
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        if bgThresh > 0:
            # TODO: only use non-interpolated?
            bad_p = actual_td.groupby("particle")["bg"].mean() >= bgThresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        if massThresh > 0:
            # TODO: only use non-interpolated?
            bad_p = actual_td.groupby("particle")["mass"].mean() <= massThresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        if minLength > 1:
            bad_p = (actual_td.groupby("particle")["frame"].apply(len) <
                     minLength)
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        fp = trackData["filter_param"] == 0
        return trackData[fp], trackData[~fp]

    def _updateTrackList(self):
        if self._trackData is None and self._trackList:
            self._trackList = []
            self.trackListChanged.emit()
            return
        self._updateManualTracks()
        p = np.sort(self._paramAccepted["particle"].unique()).tolist()
        if self._trackList != p:
            self._trackList = p
            self.trackListChanged.emit()

    @QtCore.pyqtSlot(int)
    def acceptTrack(self, index):
        self._trackData.loc[self._trackData["particle"] == index,
                            "filter_manual"] = 0
        self._updateManualTracks()

    @QtCore.pyqtSlot(int)
    def rejectTrack(self, index):
        self._trackData.loc[self._trackData["particle"] == index,
                            "filter_manual"] = 1
        self._updateManualTracks()

    def _updateManualTracks(self):
        fp = self._trackData["filter_param"] == 0
        self._manualAccepted = self._trackData[
            fp & (self._trackData["filter_manual"] == 0)]
        self.manualAcceptedChanged.emit()
        self._manualRejected = self._trackData[
            fp & (self._trackData["filter_manual"] == 1)]
        self.manualRejectedChanged.emit()
        self._manualUndecided = self._trackData[
            fp & (self._trackData["filter_manual"] == -1)]
        self.manualUndecidedChanged.emit()

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getFilterFunc(self):
        return functools.partial(
            self.workerFunc,
            filterInitial=self.filterInitial,
            filterTerminal=self.filterTerminal,
            massThresh=self.massThresh, bgThresh=self.bgThresh,
            minLength=self.minLength)

