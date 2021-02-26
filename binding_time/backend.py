import contextlib
import math
from pathlib import Path

from PyQt5 import QtCore, QtQuick
import numpy as np
import pandas as pd
from sdt import brightness, gui, helper, io, loc, multicolor


class Dataset(gui.Dataset):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = {}
        self._frameSel = multicolor.FrameSelector("")
        self._reg = multicolor.Registrator()
        self._background = 200.0
        self._bleedThrough = 0.0

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
        # TODO: this will affect also some roles

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
        # TODO: this will affect also some roles

    registratorChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=registratorChanged)
    def registrator(self):
        return self._reg

    @registrator.setter
    def registrator(self, r):
        if (np.allclose(r.parameters1, self._reg.parameters1) and
                np.allclose(r.parameters2, self._reg.parameters2)):
            return
        self._reg = r
        self.registratorChanged.emit()
        # TODO: this will affect also some roles

    background = gui.SimpleQtProperty(float, comp=math.isclose)
    bleedThrough = gui.SimpleQtProperty(float, comp=math.isclose)

    @QtCore.pyqtSlot(int, str, result=QtCore.QVariant)
    def getProperty(self, index, role):
        if not (0 <= index <= self.rowCount() and role in self.roles):
            return None
        if role == "key":
            return "; ".join(str(self.getProperty(index, r))
                             for r in self.fileRoles)
        if role in ("donor", "acceptor"):
            chan = self.channels[role]
            fname = self.getProperty(index, self.fileRoles[chan["source_id"]])
            fname = Path(self.dataDir, fname)
            seq = io.ImageSequence(fname).open()
            if chan["roi"] is not None:
                seq = chan["roi"](seq)
            if self._frameSel.excitation_seq:
                seq = self._frameSel(seq, "d")
            if role == "donor":
                # FIXME: Is donor garanteed to be channel 2?
                seq = self._reg(seq, channel=2, cval=self._background)
            return seq
        if role == "corrAcceptor":
            d = self.getProperty(index, "donor")
            a = self.getProperty(index, "acceptor")

            @helper.pipeline(ancestor_count="all")
            def corr(donor, acceptor):
                noBg = np.asanyarray(donor, dtype=float) - self.background
                return acceptor - noBg * self.bleedThrough

            return corr(d, a)
        return super().getProperty(index, role)


class DatasetCollection(gui.DatasetCollection):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataRoles = ["key", "donor", "acceptor", "corrAcceptor",
                          "locData"]
        self.DatasetClass = Dataset
        self._channels = {"acceptor": {"source_id": 0, "roi": None},
                          "donor": {"source_id": 0, "roi": None}}
        self._excitationSeq = ""
        self._reg = multicolor.Registrator()
        self._background = 200.0
        self._bleedThrough = 0.0

    def makeDataset(self):
        ret = super().makeDataset()
        ret.channels = self.channels
        ret.excitationSeq = self.excitationSeq
        ret.registrator = self.registrator
        ret.background = self.background
        ret.bleedThrough = self.bleedThrough
        return ret

    channelsChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=channelsChanged)
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, ch):
        if ch == self._channels:
            return
        self._channels = ch
        for i in range(self.rowCount()):
            self.getProperty(i, "dataset").channels = ch
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
        for i in range(self.rowCount()):
            self.getProperty(i, "dataset").excitationSeq = seq
        self.excitationSeqChanged.emit()

    registratorChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=registratorChanged)
    def registrator(self):
        return self._reg

    @registrator.setter
    def registrator(self, r):
        if (np.allclose(r.parameters1, self._reg.parameters1) and
                np.allclose(r.parameters2, self._reg.parameters2)):
            return
        self._reg = r
        for i in range(self.rowCount()):
            self.getProperty(i, "dataset").registrator = r
        self.registratorChanged.emit()

    backgroundChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(float, notify=backgroundChanged)
    def background(self):
        return self._background

    @background.setter
    def background(self, bg):
        if math.isclose(bg, self._background):
            return
        self._background = bg
        for i in range(self.rowCount()):
            self.getProperty(i, "dataset").background = bg
        self.backgroundChanged.emit()

    bleedThroughChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(float, notify=bleedThroughChanged)
    def bleedThrough(self):
        return self._bleedThrough

    @bleedThrough.setter
    def bleedThrough(self, bt):
        if math.isclose(bt, self._bleedThrough):
            return
        self._bleedThrough = bt
        for i in range(self.rowCount()):
            self.getProperty(i, "dataset").bleedThrough = bt
        self.bleedThroughChanged.emit()


class Filter(QtQuick.QQuickItem):
    def __init__(self, parent):
        super().__init__(parent)
        self._options = {}

    options = gui.SimpleQtProperty("QVariantMap")

    @QtCore.pyqtSlot(QtCore.QVariant, QtCore.QVariant, result=QtCore.QVariant)
    def filterTracks(self, trc, imageSeq):
        if imageSeq is None:
            return
        n_frames = len(imageSeq)
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

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def _getFilterFunc(self):
        return self.filterTracks


class Backend(QtCore.QObject):
    _specialKeys = ["registration"]

    def __init__(self, parent=None):
        super().__init__(parent)
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
        data = {"channels": self.datasets.channels,
                "data_dir": self._datasets.dataDir,
                "excitation_seq": self._datasets.excitationSeq,
                "loc_algorithm": self.locAlgorithm,
                "loc_options": self.locOptions,
                "track_options": self.trackOptions,
                "files": self._datasets.fileLists,
                "special_files": self._specialDatasets.fileLists,
                "registration_loc": self.registrationLocSettings,
                "registrator": self._datasets.registrator,
                "background": self._datasets.background,
                "bleed_through": self._datasets.bleedThrough}

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
            self._datasets.channels = data["channels"]
            self._specialDatasets.channels = data["channels"]
        if "data_dir" in data:
            self._datasets.dataDir = data["data_dir"]
            self._specialDatasets.dataDir = data["data_dir"]
        if "excitation_seq" in data:
            self._datasets.excitationSeq = data["excitation_seq"]
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
        if "registrator" in data:
            self._datasets.registrator = data["registrator"]
        if "background" in data:
            self._datasets.background = data["background"]
        if "bleed_through" in data:
            self._datasets.bleedThrough = data["bleed_through"]

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
