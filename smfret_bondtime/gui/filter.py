# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import functools
import warnings

from PyQt5 import QtCore, QtQml
import numpy as np
from sdt import changepoint, gui


# TODO: No need to derive from OptionChooser since there are no intensive
# tasks that need to be done in a thread
class Filter(gui.OptionChooser):
    def __init__(self, parent):
        super().__init__(
            argProperties=[
                "trackData",
                "trackStats",
                "bgThresh",
                "massThresh",
                "minLength",
                "minChangepoints",
                "maxChangepoints",
                "startEndChangepoints",
            ],
            resultProperties=["paramAccepted", "paramRejected"],
            parent=parent,
        )
        self._datasets = None
        self._trackData = None
        self._trackStats = None
        self._paramAccepted = None
        self._paramRejected = None
        self._manualAccepted = None
        self._manualRejected = None
        self._manualUndecided = None
        self._navigatorStats = None

        self._showManual = 0

        self.paramAcceptedChanged.connect(self._updateManualTracks)
        self.showManualChanged.connect(self._updateManualTracks)

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    currentTrackData = gui.QmlDefinedProperty()
    currentTrackInfo = gui.QmlDefinedProperty()
    frameCount = gui.QmlDefinedProperty()
    paramAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    paramRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualAccepted = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualRejected = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    manualUndecided = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    navigatorStats = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
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
        self._trackData = td
        self.trackDataChanged.emit()

    trackStatsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=trackStatsChanged)
    def trackStats(self):
        return self._trackStats

    @trackStats.setter
    def trackStats(self, ts):
        if self._trackStats is ts:
            return
        hadChangepoints = self.hasChangepoints
        self._trackStats = ts
        self.trackStatsChanged.emit()
        if hadChangepoints != self.hasChangepoints:
            self.hasChangepointsChanged.emit()

    hasChangepointsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(bool, notify=hasChangepointsChanged)
    def hasChangepoints(self):
        return self._trackStats is not None and "changepoints" in self._trackStats

    @QtCore.pyqtSlot()
    def updatePlot(self):
        if (
            self.timeTraceFig is None
            or self.currentTrackData is None
            or len(self.currentTrackData) < 1
        ):
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
        changepoint.plot_changepoints(d, cp, time=self.currentTrackData["frame"], ax=ax)

        ymin = np.nanmin(d)
        ymax = np.nanmax(d)
        ax.set_ylim(
            ymin if np.isfinite(ymin) else None, ymax if np.isfinite(ymax) else None
        )
        ax.axvline(self.currentTrackInfo["start"], color="g")
        ax.axvline(self.currentTrackInfo["end"], color="r")
        ax.set_xlabel("frame")
        ax.set_ylabel("intensity")
        fig.canvas.draw_idle()

    @staticmethod
    def workerFunc(
        trackData,
        trackStats,
        bgThresh,
        massThresh,
        minLength,
        minChangepoints,
        maxChangepoints,
        startEndChangepoints,
    ):
        if trackStats is None or trackData is None:
            return None, None
        flt = np.zeros(len(trackStats), dtype=bool)
        if bgThresh > 0:
            flt |= trackStats["bg"] >= bgThresh
        if massThresh > 0:
            flt |= trackStats["mass"] <= massThresh
        if minLength > 1:
            flt |= trackStats["track_len"] < minLength
        if "changepoints" in trackStats:
            cp = trackStats["changepoints"].to_numpy(copy=True)
            if startEndChangepoints:
                cp += trackStats["censored"] & 1
                cp += trackStats["censored"] & 2
            flt |= cp < minChangepoints
            flt |= cp > maxChangepoints
        trackStats["filter_param"] = flt.astype(int)

        fp = trackStats["filter_param"] == 0
        msk = trackData["particle"].isin(fp.index[fp])
        return trackData[msk], trackData[~msk]

    @QtCore.pyqtSlot(int)
    def acceptTrack(self, index):
        if index not in self._trackStats.index:
            warnings.warn(f"tried to accept track {index} which does not exist")
            return
        self._trackStats.loc[index, "filter_manual"] = 0
        self._updateManualTracks()

    @QtCore.pyqtSlot(int)
    def rejectTrack(self, index):
        if index not in self._trackStats.index:
            warnings.warn(f"tried to reject track {index} which does not exist")
            return
        self._trackStats.loc[index, "filter_manual"] = 1
        self._updateManualTracks()

    def _updateManualTracks(self):
        if self._trackData is None or self._trackStats is None:
            self._navigatorStats = None
            self._manualAccepted = None
            self._manualRejected = None
            self._manualUndecided = None
        else:
            fp = self._trackStats[self._trackStats["filter_param"] == 0]

            if self._showManual == 1:  # show only undecided
                self._navigatorStats = fp[fp["filter_manual"] == -1]
                self._manualUndecided = self._trackData[
                    self._trackData["particle"].isin(self._navigatorStats.index)
                ]
                self._manualAccepted = self._manualRejected = self._trackData.iloc[:0]
            elif self._showManual == 2:  # show only accepted
                self._navigatorStats = fp[fp["filter_manual"] == 0]
                self._manualAccepted = self._trackData[
                    self._trackData["particle"].isin(self._navigatorStats.index)
                ]
                self._manualUndecided = self._manualRejected = self._trackData.iloc[:0]
            elif self._showManual == 3:  # show only rejected
                self._navigatorStats = fp[fp["filter_manual"] == 1]
                self._manualRejected = self._trackData[
                    self._trackData["particle"].isin(self._navigatorStats.index)
                ]
                self._manualAccepted = self._manualUndecided = self._trackData.iloc[:0]
            else:
                self._navigatorStats = fp
                self._manualAccepted = self._trackData[
                    self._trackData["particle"].isin(fp.index[fp["filter_manual"] == 0])
                ]
                self._manualRejected = self._trackData[
                    self._trackData["particle"].isin(fp.index[fp["filter_manual"] == 1])
                ]
                self._manualUndecided = self._trackData[
                    self._trackData["particle"].isin(
                        fp.index[fp["filter_manual"] == -1]
                    )
                ]
        self.navigatorStatsChanged.emit()
        self.manualRejectedChanged.emit()
        self.manualAcceptedChanged.emit()
        self.manualUndecidedChanged.emit()

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getFilterFunc(self):
        return functools.partial(
            self.workerFunc,
            massThresh=self.massThresh,
            bgThresh=self.bgThresh,
            minLength=self.minLength,
            minChangepoints=self.minChangepoints,
            maxChangepoints=self.maxChangepoints,
            startEndChangepoints=self.startEndChangepoints,
        )


QtQml.qmlRegisterType(Filter, "SmFretBondTime.Templates", 1, 0, "Filter")
