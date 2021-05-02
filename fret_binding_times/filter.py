import operator

from PyQt5 import QtCore
from sdt import gui


class Filter(gui.OptionChooser):
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

    datasets = gui.SimpleQtProperty(QtCore.QVariant)
    trackData = gui.SimpleQtProperty(QtCore.QVariant, comp=operator.is_)
    imageSequence = gui.SimpleQtProperty(QtCore.QVariant)
    acceptedTracks = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    rejectedTracks = gui.SimpleQtProperty(QtCore.QVariant, readOnly=True)
    filterInitial = gui.QmlDefinedProperty()
    filterTerminal = gui.QmlDefinedProperty()
    massThresh = gui.QmlDefinedProperty()
    bgThresh = gui.QmlDefinedProperty()
    minLength = gui.QmlDefinedProperty()

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

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getFilterFunc(self):
        return functools.partial(
            self.workerFunc,
            filterInitial=self.filterInitial,
            filterTerminal=self.filterTerminal,
            massThresh=self.massThresh, bgThresh=self.bgThresh,
            minLength=self.minLength)

