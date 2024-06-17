import functools
import operator

from PyQt5 import QtCore, QtQml
import numpy as np
from sdt import changepoint, gui


# TODO: No need to derive from OptionChooser since there are no intensive
# tasks that need to be done in a thread
class Filter(gui.OptionChooser):
    _invalidTrackInfo = {"start": -1, "end": -1, "mass": float("NaN"),
                         "bg": float("NaN"), "bg_dev": float("NaN"),
                         "length": 0, "status": "undefined"}

    _statusMap = {-1: "undecided", 0: "accepted", 1: "rejected"}

    def __init__(self, parent):
        super().__init__(
            argProperties=[
                "trackData", "frameCount","bgThresh", "massThresh", "minLength",
                "minChangepoints", "maxChangepoints", "startEndChangepoints"
            ],
            resultProperties=["paramAccepted", "paramRejected"],
            parent=parent)
        self._datasets = None
        self._trackData = None
        self._paramAccepted = None
        self._paramRejected = None
        self._manualAccepted = None
        self._manualRejected = None
        self._manualUndecided = None
        self._navigatorData = None

        self._showManual = 0

        self.paramAcceptedChanged.connect(self._updateManualTracks)
        self.showManualChanged.connect(self._updateManualTracks)

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    trackData = gui.SimpleQtProperty(QtCore.QVariant, comp=operator.is_)
    currentTrackData = gui.QmlDefinedProperty()
    currentTrackInfo = gui.QmlDefinedProperty()
    frameCount = gui.QmlDefinedProperty()
    paramAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    paramRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualUndecided = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    navigatorData = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    massThresh = gui.QmlDefinedProperty()
    bgThresh = gui.QmlDefinedProperty()
    minLength = gui.QmlDefinedProperty()
    timeTraceFig = gui.QmlDefinedProperty()
    minChangepoints = gui.QmlDefinedProperty()
    maxChangepoints = gui.QmlDefinedProperty()
    startEndChangepoints = gui.QmlDefinedProperty()

    showManual = gui.SimpleQtProperty(int)

    trackDataChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=trackDataChanged)
    def trackData(self):
        return self._trackData

    @trackData.setter
    def trackData(self, td):
        if self._trackData is td:
            return
        hadChangepoints = self.hasChangepoints
        self._trackData = td
        self.trackDataChanged.emit()
        if hadChangepoints != self.hasChangepoints:
            self.hasChangepointsChanged.emit()

    hasChangepointsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(bool, notify=hasChangepointsChanged)
    def hasChangepoints(self):
        return self._trackData is not None and "mass_seg" in self._trackData

    @QtCore.pyqtSlot()
    def updatePlot(self):
        if self.timeTraceFig is None or self.currentTrackData is None:
            return

        d = self.currentTrackData["mass"].to_numpy()
        if "mass_seg" in self.currentTrackData:
            cp = np.nonzero(np.diff(self.currentTrackData["mass_seg"]))[0] + 1
        else:
            cp = np.array([])

        fig = self.timeTraceFig.figure
        fig.set_constrained_layout(True)
        try:
            ax = fig.axes[0]
        except IndexError:
            ax = fig.add_subplot()
        ax.cla()
        changepoint.plot_changepoints(
            d, cp, time=self.currentTrackData["frame"], ax=ax)
        ax.set_ylim(d.min(), d.max())
        ax.axvline(self.currentTrackInfo["start"], color="g")
        ax.axvline(self.currentTrackInfo["end"], color="r")
        ax.set_xlabel("frame")
        ax.set_ylabel("intensity")
        fig.canvas.draw_idle()

    @staticmethod
    def workerFunc(
        trackData, frameCount, bgThresh, massThresh, minLength, minChangepoints,
        maxChangepoints, startEndChangepoints
    ):
        if trackData is None or frameCount < 1:
            return None, None
        n_frames = frameCount
        trackData["filter_param"] = 0
        try:
            actual_td = trackData[trackData["extra_frame"] == 0]
        except KeyError:
            actual_td = trackData
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
        if "mass_seg" in trackData:
            cp_count = trackData.groupby("particle")["mass_seg"].apply(
                lambda x: len(x.unique())) - 1

            if startEndChangepoints:
                presentAtStart = actual_td.loc[
                    actual_td["frame"] == 0, "particle"].unique()
                presentAtEnd = actual_td.loc[
                    actual_td["frame"] == n_frames - 1, "particle"].unique()
                cp_count[cp_count.index.isin(presentAtStart)] += 1
                cp_count[cp_count.index.isin(presentAtEnd)] += 1

            bad_p = (cp_count < minChangepoints) | (cp_count > maxChangepoints)
            bad_p = bad_p.index[bad_p.to_numpy()]
            trackData.loc[trackData["particle"].isin(bad_p),
                          "filter_param"] = 1
        fp = trackData["filter_param"] == 0
        return trackData[fp], trackData[~fp]

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
        if self._trackData is None:
            self._navigatorData = None
            self._manualAccepted = None
            self._manualRejected = None
            self._manualUndecided = None
        else:
            fp = self._trackData[self._trackData["filter_param"] == 0]
            if self._showManual == 1:  # show only undecided
                self._navigatorData = self._manualUndecided = \
                    fp[fp["filter_manual"] == -1]
                self._manualAccepted = self._manualRejected = fp.iloc[:0]
            elif self._showManual == 2:  # show only accepted
                self._navigatorData = self._manualAccepted = \
                    fp[fp["filter_manual"] == 0]
                self._manualUndecided = self._manualRejected = fp.iloc[:0]
            elif self._showManual == 3:  # show only rejected
                self._navigatorData = self._manualRejected = \
                    fp[fp["filter_manual"] == 1]
                self._manualUndecided = self._manualAccepted = fp.iloc[:0]
            else:
                self._navigatorData = fp
                self._manualAccepted = fp[fp["filter_manual"] == 0]
                self._manualRejected = fp[fp["filter_manual"] == 1]
                self._manualUndecided = fp[fp["filter_manual"] == -1]
        self.navigatorDataChanged.emit()
        self.manualRejectedChanged.emit()
        self.manualAcceptedChanged.emit()
        self.manualUndecidedChanged.emit()

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getFilterFunc(self):
        return functools.partial(
            self.workerFunc,
            massThresh=self.massThresh, bgThresh=self.bgThresh,
            minLength=self.minLength, minChangepoints=self.minChangepoints,
            maxChangepoints=self.maxChangepoints,
            startEndChangepoints=self.startEndChangepoints)


QtQml.qmlRegisterType(Filter, "BindingTime.Templates", 1, 0, "Filter")
