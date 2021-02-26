import contextlib
import math
from pathlib import Path

from PyQt5 import QtCore, QtQuick
import numpy as np
import pandas as pd
import scipy.optimize
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

    @staticmethod
    def survivalModel(x, a, k):
        return a * np.exp(-k * x)

    @staticmethod
    def lifetimeModel(t_frame, t_off, t_bleach):
        return 1 / (1 / t_off + 1 / (t_bleach * t_frame))

    @QtCore.pyqtSlot(QtCore.QVariant, int, int, bool, result=float)
    def getResults(self, figureCanvas, ignoreFirst, minCount, fitRates):
        if not self._datasets.rowCount():
            return np.NaN

        res = []
        for i in range(self._datasets.rowCount()):
            time = int(self._datasets.getProperty(i, "key")) / 1000
            ds = self._datasets.getProperty(i, "dataset")

            frameCounts = []
            for j in range(ds.rowCount()):
                df = ds.getProperty(j, "locData")
                df = df[df["accepted"]]
                fc = df.groupby("particle")["frame"].apply(np.ptp)
                if not fc.empty:
                    # Exclude empty as they have float dtype, which does not
                    # work with np.bincount
                    frameCounts.append(fc)
            frameCounts = np.concatenate(frameCounts)
            y = np.bincount(frameCounts)
            y = np.cumsum(y[::-1])[::-1]  # survival function
            x = np.arange(1, len(y) + 1) * time
            use = np.ones(len(x), dtype=bool)
            use[:ignoreFirst] = False
            use[y < minCount] = False

            fit_x = x[use]
            fit_y = y[use]
            # estimate amplitude as number of events
            a = fit_y[0]
            # estimate 1 / rate as mean of survival times
            m = np.sum(fit_x * fit_y) / np.sum(fit_y)
            fit = scipy.optimize.curve_fit(
                self.survivalModel, fit_x, fit_y, p0=[a, 1 / m])[0]
            res.append((time, x, y, use, fit))

        res = sorted(res, key=lambda x: x[0])

        fig = figureCanvas.figure
        fig.clf()
        fig.set_constrained_layout(True)
        grid = fig.add_gridspec(2, 1)

        survAx = fig.add_subplot(grid[0])
        for i, (t, x, y, use, fit) in enumerate(res):
            color = f"C{i%10}"
            survAx.scatter(x[use], y[use], marker="o", edgecolor="none",
                           facecolor=color, alpha=0.5)
            survAx.scatter(x[~use], y[~use], marker="o", edgecolor=color,
                           facecolor="none", alpha=0.5)
            x_fit = np.linspace(x[0], x[-1], 100)
            survAx.plot(x_fit, self.survivalModel(x_fit, *fit), color=color,
                        label=f"{t*1000:.0f} ms ({1 / t:.1f} fps)")
        survAx.legend(loc=0)
        survAx.set_title("survival functions")
        survAx.set_xlabel("survival time [s]")
        survAx.set_ylabel("cumulated count")

        times = np.array([x[0] for x in res])
        rates = np.array([x[-1][1] for x in res])

        k_bleach, k_off = np.polyfit(1 / times, rates, 1)

        if fitRates:
            rateAx = fig.add_subplot(grid[1])
            rateAx.scatter(1 / times, rates)
            rateAx.set_title("measured off-rates")
            rateAx.set_xlabel("frame rate [fps]")
            rateAx.set_ylabel("apparent off-rate [s$^{-1}$]")
            x_r = np.array([1 / times[-1], 1 / times[0]])
            y_r = k_off + k_bleach * x_r
            rateAx.plot(x_r, y_r, "C0")
        else:
            t_off, t_bleach = scipy.optimize.curve_fit(
                self.lifetimeModel, times, 1 / rates,
                p0=[1 / k_off, 1 / k_bleach])[0]
            timeAx = fig.add_subplot(grid[1])
            timeAx.scatter(times * 1000, 1 / rates)
            timeAx.set_title("measured lifetimes")
            timeAx.set_xlabel("time per frame [ms]")
            timeAx.set_ylabel("apparent lifetime [s]")
            x_t = np.linspace(times[0], times[-1], 100)
            y_t = self.lifetimeModel(x_t, t_off, t_bleach)
            timeAx.plot(x_t * 1000, y_t, "C0")
            k_off = 1 / t_off

        figureCanvas.draw_idle()

        return k_off
