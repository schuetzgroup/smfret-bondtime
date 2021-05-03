import functools
import operator

from PyQt5 import QtCore
import numpy as np
from sdt import gui


class Filter(gui.OptionChooser):
    _invalidTrackInfo = {"start": -1, "end": -1, "mass": float("NaN"),
                         "bg": float("NaN"), "length": 0,
                         "status": "undefined"}

    def __init__(self, parent):
        super().__init__(
            argProperties=["trackData", "imageSequence", "filterInitial",
                           "filterTerminal", "bgThresh", "massThresh",
                           "minLength"],
            resultProperties=["acceptedTracks", "rejectedTracks"],
            parent=parent)
        self._datasets = None
        self._trackData = None
        self._imageSequence = None
        self._acceptedTracks = None
        self._rejectedTracks = None
        self._currentTrack = None
        self._currentTrackInfo = self._invalidTrackInfo
        self._currentTrackNo = -1
        self._trackList = []
        self._acceptedTrackList = []

        self.trackDataChanged.connect(self._updateTrackList)
        self.acceptedTracksChanged.connect(self._updateAcceptedTrackList)

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    trackData = gui.SimpleQtProperty(QtCore.QVariant, comp=operator.is_)
    imageSequence = gui.SimpleQtProperty(QtCore.QVariant)
    acceptedTracks = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    rejectedTracks = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    currentTrack = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    currentTrackInfo = gui.SimpleQtProperty("QVariantMap", readOnly=True)
    trackList = gui.SimpleQtProperty(list, readOnly=True)
    acceptedTrackList = gui.SimpleQtProperty(list, readOnly=True)
    filterInitial = gui.QmlDefinedProperty()
    filterTerminal = gui.QmlDefinedProperty()
    massThresh = gui.QmlDefinedProperty()
    bgThresh = gui.QmlDefinedProperty()
    minLength = gui.QmlDefinedProperty()

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
            self._currentTrack = None
            self._currentTrackInfo = self._invalidTrackInfo
        else:
            td = self._trackData[self._trackData["particle"] == t]
            if not (len(td)):
                self._currentTrack = None
                self._currentTrackInfo = self._invalidTrackInfo
            else:
                self._currentTrack = td
                f = self._currentTrack["frame"]
                self._currentTrackInfo = {
                    "start": int(f.min()), "end": int(f.max()),
                    "mass": float(td["mass"].mean()),
                    "bg": float(td["bg"].mean()), "length": len(td),
                    "status": ("accepted" if td["accepted"].iloc[0]
                               else "rejected")}
        self.currentTrackNoChanged.emit()
        self.currentTrackChanged.emit()
        self.currentTrackInfoChanged.emit()

    @staticmethod
    def workerFunc(trackData, imageSequence, filterInitial, filterTerminal,
                   bgThresh, massThresh, minLength):
        if trackData is None or imageSequence is None:
            return None, None
        n_frames = len(imageSequence)
        trackData["accepted"] = True
        if filterInitial:
            bad_p = trackData.loc[trackData["frame"] == 0, "particle"].unique()
            trackData.loc[trackData["particle"].isin(bad_p),
                          "accepted"] = False
        if filterTerminal:
            bad_p = trackData.loc[trackData["frame"] == n_frames - 1,
                                  "particle"].unique()
            trackData.loc[trackData["particle"].isin(bad_p),
                          "accepted"] = False
        if bgThresh > 0:
            bad_p = trackData.groupby("particle")["bg"].mean() >= bgThresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "accepted"] = False
        if massThresh > 0:
            bad_p = trackData.groupby("particle")["mass"].mean() <= massThresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "accepted"] = False
        if minLength > 1:
            bad_p = (trackData.groupby("particle")["frame"].apply(len) <
                     minLength)
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "accepted"] = False
        return (trackData[trackData["accepted"]],
                trackData[~trackData["accepted"]])

    def _updateTrackList(self):
        if self._trackData is None and self._trackList:
            self._trackList = []
            self.trackListChanged.emit()
            return
        p = np.sort(self._trackData["particle"].unique()).tolist()
        if self._trackList != p:
            self._trackList = p
            self.trackListChanged.emit()

    def _updateAcceptedTrackList(self):
        if self._acceptedTracks is None and self._acceptedTrackList:
            self._acceptedTrackList = []
            self.acceptedTrackListChanged.emit()
            return
        p = np.sort(self._acceptedTracks["particle"].unique()).tolist()
        if self._acceptedTrackList != p:
            self._acceptedTrackList = p
            self.acceptedTrackListChanged.emit()

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getFilterFunc(self):
        return functools.partial(
            self.workerFunc,
            filterInitial=self.filterInitial,
            filterTerminal=self.filterTerminal,
            massThresh=self.massThresh, bgThresh=self.bgThresh,
            minLength=self.minLength)

