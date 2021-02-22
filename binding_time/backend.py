import contextlib
from pathlib import Path

from PyQt5 import QtCore, QtQuick
import numpy as np
import pandas as pd
from sdt import brightness, gui, io, loc, multicolor


class Dataset(gui.Dataset):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = {}
        self._frameSel = multicolor.FrameSelector("")

    def _onTrafoChanged(self):
        """Emit :py:meth:`dataChanged` if exc seq or channels change"""
        self.dataChanged.emit(self.index(0), self.index(self.count - 1),
                              [int(self.Roles.fretImage)])

    channelsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=channelsChanged)
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, ch):
        if ch == self._channels:
            return
        self._channels = ch
        self.channelsChanged.emit()

    excitationSeqChanged = QtCore.pyqtSignal()
    """:py:attr:`excitationSeq` changed"""

    @QtCore.pyqtProperty(str, notify=excitationSeqChanged)
    def excitationSeq(self) -> str:
        """Excitation sequence. See :py:class:`multicolor.FrameSelector` for
        details. No error checking es performend here.
        """
        return self._frameSel.excitation_seq

    @excitationSeq.setter
    def excitationSeq(self, seq: str):
        if seq == self.excitationSeq:
            return
        self._frameSel.excitation_seq = seq
        self.excitationSeqChanged.emit()

    def getProperty(self, index, role):
        if role == "key":
            return "; ".join(str(self.getProperty(index, r))
                             for r in self.fileRoles)
        if role == "fretImage":
            chan = self.channels["acceptor"]
            fname = self.getProperty(index, self.fileRoles[chan["source_id"]])
            fname = Path(self.dataDir, fname)
            seq = io.ImageSequence(fname).open()
            if chan["roi"] is not None:
                seq = chan["roi"](seq)
            seq = self._frameSel(seq, "d")
            return seq
        if role in ("donor", "acceptor"):
            chan = self.channels[role]
            fname = self.getProperty(index, self.fileRoles[chan["source_id"]])
            fname = Path(self.dataDir, fname)
            seq = io.ImageSequence(fname).open()
            if chan["roi"] is not None:
                seq = chan["roi"](seq)
            return seq
        return super().getProperty(index, role)


class Filter(QtQuick.QQuickItem):
    def __init__(self, parent):
        super().__init__(parent)
        self._options = {}

    optionsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=optionsChanged)
    def options(self):
        return self._options

    @options.setter
    def options(self, o):
        if o == self._options:
            return
        self._options = o
        self.optionsChanged.emit()

    @QtCore.pyqtSlot(QtCore.QVariant, int, result=QtCore.QVariant)
    def filterTracks(self, trc, n_frames):
        if trc is None:
            return None
        trc["accepted"] = True
        if self.options["filter_initial"]:
            bad_p = trc.loc[trc["frame"] == 0, "particle"].unique()
            trc.loc[trc["particle"].isin(bad_p), "accepted"] = False
        if self.options["filter_terminal"]:
            bad_p = trc.loc[trc["frame"] == n_frames - 1, "particle"].unique()
            trc.loc[trc["particle"].isin(bad_p), "accepted"] = False
        bg_thresh = self.options["bg_thresh"]
        if bg_thresh > 0:
            bad_p = trc.groupby("particle")["bg"].mean() >= bg_thresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trc.loc[trc["particle"].isin(bad_p), "accepted"] = False
        mass_thresh = self.options["mass_thresh"]
        if mass_thresh > 0:
            bad_p = trc.groupby("particle")["mass"].mean() <= mass_thresh
            bad_p = bad_p.index[bad_p.to_numpy()]
            trc.loc[trc["particle"].isin(bad_p), "accepted"] = False
        return trc[trc["accepted"]]


class DatasetCollection(gui.DatasetCollection):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataRoles = ["key", "fretImage", "locData"]
        self.DatasetClass = Dataset

    def makeDataset(self):
        ret = super().makeDataset()
        ret.channels = self.parent().channels  # FIXME
        ret.excitationSeq = self.parent().excitationSeq  # FIXME
        return ret


class Backend(QtCore.QObject):
    _specialKeys = ["registration"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = {"acceptor": {"source_id": 0, "roi": None},
                          "donor": {"source_id": 0, "roi": None}}
        self._excitationSeq = ""
        self._algo = ""
        self._options = {}
        self._trcOptions = {}
        self._filterOptions = {}
        self._datasets = DatasetCollection(self)
        self._specialDatasets = DatasetCollection(self)
        for k in self._specialKeys:
            self._specialDatasets.append(k)
        self._regLocSettings = {}

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def datasets(self):
        return self._datasets

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def specialDatasets(self):
        return self._specialDatasets

    channelsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=channelsChanged)
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, ch):
        if ch == self._channels:
            return
        self._channels = ch
        for ds in self._datasets, self._specialDatasets:
            for i in range(ds.count):
                ds.getProperty(i, "dataset").channels = ch
        self.channelsChanged.emit()

    excitationSeqChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=excitationSeqChanged)
    def excitationSeq(self) -> str:
        return self._excitationSeq

    @excitationSeq.setter
    def excitationSeq(self, seq: str):
        if seq == self.excitationSeq:
            return
        self._excitationSeq = seq
        for i in range(self._datasets.count):
            self._datasets.getProperty(i, "dataset").excitationSeq = seq
        self.excitationSeqChanged.emit()

    locAlgorithmChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=locAlgorithmChanged)
    def locAlgorithm(self):
        return self._algo

    @locAlgorithm.setter
    def locAlgorithm(self, a):
        if a == self._algo:
            return
        self._algo = a
        self.locAlgorithmChanged.emit()

    locOptionsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=locOptionsChanged)
    def locOptions(self):
        return self._options

    @locOptions.setter
    def locOptions(self, o):
        if o == self._options:
            return
        self._options = o
        self.locOptionsChanged.emit()

    trackOptionsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=trackOptionsChanged)
    def trackOptions(self):
        return self._trcOptions

    @trackOptions.setter
    def trackOptions(self, o):
        if o == self._trcOptions:
            return
        self._trcOptions = o
        self.trackOptionsChanged.emit()

    filterOptionsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=filterOptionsChanged)
    def filterOptions(self):
        return self._filterOptions

    @filterOptions.setter
    def filterOptions(self, o):
        if o == self._filterOptions:
            return
        self._filterOptions = o
        self.filterOptionsChanged.emit()

    registrationDatasetChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=registrationDatasetChanged)
    def registrationDataset(self):
        return self._specialDatasets.getProperty(0, "dataset")

    registrationLocSettingsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=registrationLocSettingsChanged)
    def registrationLocSettings(self):
        return self._regLocSettings

    @registrationLocSettings.setter
    def registrationLocSettings(self, s):
        if s == self._regLocSettings:
            return
        self._regLocSettings = s
        self.registrationLocSettingsChanged.emit()

    @QtCore.pyqtSlot(QtCore.QUrl)
    def save(self, url):
        data = {"channels": self.channels, "data_dir": self._datasets.dataDir,
                "excitation_seq": self.excitationSeq,
                "loc_algorithm": self.locAlgorithm,
                "loc_options": self.locOptions,
                "track_options": self.trackOptions,
                "files": self._datasets.fileLists,
                "special_files": self._specialDatasets.fileLists,
                "registration_loc": self.registrationLocSettings}

        ypath = Path(url.toLocalFile())
        with ypath.open("w") as yf:
            io.yaml.safe_dump(data, yf)

        import tables, warnings
        with pd.HDFStore(ypath.with_suffix(".h5"), "w") as s:
            for i in range(self._datasets.rowCount()):
                ekey = self._datasets.getProperty(i, "key")
                dset = self._datasets.getProperty(i, "dataset")
                for j in range(dset.rowCount()):
                    dkey = dset.getProperty(j, "key")
                    ld = dset.getProperty(j, "locData")
                    if isinstance(ld, pd.DataFrame):
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore",
                                                  tables.NaturalNameWarning)
                            s.put(f"/{ekey}/{dkey}", ld)

    @QtCore.pyqtSlot(QtCore.QUrl, result=QtCore.QVariant)
    def load(self, url):
        if isinstance(url, QtCore.QUrl):
            ypath = Path(url.toLocalFile())
        else:
            ypath = Path(url)
        with ypath.open() as yf:
            data = io.yaml.safe_load(yf)
        if "channels" in data:
            self.channels = data["channels"]
        if "data_dir" in data:
            self._datasets.dataDir = data["data_dir"]
            self._specialDatasets.dataDir = data["data_dir"]
        if "excitation_seq" in data:
            self.excitationSeq = data["excitation_seq"]
        if "loc_algorithm" in data:
            self.locAlgorithm = data["loc_algorithm"]
        if "loc_options" in data:
            self.locOptions = data["loc_options"]
        if "track_options" in data:
            self.trackOptions = data["track_options"]
        if "files" in data:
            self._datasets.fileLists = data["files"]
        if "special_files" in data:
            sf = data["special_files"]
            self._specialDatasets.fileLists = {
                k: sf.get(k, []) for k in self._specialKeys}
            self.registrationDatasetChanged.emit()
        if "registration_loc" in data:
            self.registrationLocSettings = data["registration_loc"]

        h5path = ypath.with_suffix(".h5")
        if h5path.exists():
            with pd.HDFStore(h5path, "r") as s:
                for i in range(self._datasets.rowCount()):
                    ekey = self._datasets.getProperty(i, "key")
                    dset = self._datasets.getProperty(i, "dataset")
                    for j in range(dset.rowCount()):
                        dkey = dset.getProperty(j, "key")
                        with contextlib.suppress(KeyError):
                            dset.setProperty(j, "locData",
                                             s.get(f"/{ekey}/{dkey}"))

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getLocateFunc(self):
        f = getattr(loc, self.locAlgorithm).batch
        opts = self.locOptions

        def locFunc(fretImage):
            lc = f(fretImage, **opts)
            brightness.from_raw_image(lc, fretImage, radius=3, mask="circle")
            return lc

        return locFunc
