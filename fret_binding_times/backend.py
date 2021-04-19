import contextlib
import functools
import math
import operator
from pathlib import Path

from PyQt5 import QtCore, QtQuick
import numpy as np
import pandas as pd
import scipy.optimize
import scipy.ndimage
from sdt import brightness, gui, helper, io, loc, multicolor


class Dataset(gui.Dataset):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = {}
        self._frameSel = multicolor.FrameSelector("")
        self._registrator = multicolor.Registrator()
        self._bleedThrough = {"background": 200.0, "factor": 0.0, "smooth": 1.0}

        self.channelsChanged.connect(self._imageDataChanged)
        self.registratorChanged.connect(self._imageDataChanged)
        self.excitationSeqChanged.connect(self._imageDataChanged)
        self.bleedThroughChanged.connect(self._corrAcceptorChanged)

    channels = gui.SimpleQtProperty("QVariantMap")
    registrator = gui.SimpleQtProperty(QtCore.QVariant)
    background = gui.SimpleQtProperty(float, comp=math.isclose)

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

    bleedThroughChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty("QVariantMap", notify=bleedThroughChanged)
    def bleedThrough(self):
        return self._bleedThrough.copy()

    @bleedThrough.setter
    def bleedThrough(self, bt):
        modified = False
        for k in self._bleedThrough:
            with contextlib.suppress(KeyError):
                v = bt[k]
                if not math.isclose(v, self._bleedThrough[k]):
                    self._bleedThrough[k] = v
                    modified = True
        if modified:
            self.bleedThroughChanged.emit()

    @QtCore.pyqtSlot(int, str, result=QtCore.QVariant)
    def get(self, index, role):
        if not (0 <= index <= self.rowCount() and role in self.roles):
            return None
        if role == "key":
            return "; ".join(str(self.get(index, r)) for r in self.fileRoles)
        if role in ("donor", "acceptor"):
            chan = self.channels[role]
            fname = self.get(index, self.fileRoles[chan["source_id"]])
            fname = Path(self.dataDir, fname)
            seq = io.ImageSequence(fname).open()
            if chan["roi"] is not None:
                seq = chan["roi"](seq)
            if self._frameSel.excitation_seq:
                seq = self._frameSel.select(seq, "d")
            if role == "donor":
                # FIXME: Is donor garanteed to be channel 2?
                seq = self._registrator(seq, channel=2,
                                        cval=self._bleedThrough["background"])
            return seq
        if role == "corrAcceptor":
            d = self.get(index, "donor")
            a = self.get(index, "acceptor")
            bg = self._bleedThrough["background"]
            bt = self._bleedThrough["factor"]
            smt = self._bleedThrough["smooth"]

            @helper.pipeline(ancestor_count="all")
            def corr(donor, acceptor):
                noBg = np.asanyarray(donor, dtype=float) - bg
                if smt >= 1e-3:
                    noBg = scipy.ndimage.gaussian_filter(noBg, smt)
                return acceptor - noBg * bt

            return corr(d, a)
        return super().get(index, role)

    def _imageDataChanged(self):
        self.itemsChanged.emit(0, self.count, ["donor", "acceptor",
                                               "corrAcceptor"])

    def _corrAcceptorChanged(self):
        self.itemsChanged.emit(0, self.count, ["corrAcceptor"])


class DatasetCollection(gui.DatasetCollection):
    DatasetClass = Dataset

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataRoles = ["key", "donor", "acceptor", "corrAcceptor",
                          "locData"]
        self.DatasetClass = Dataset
        self._channels = {"acceptor": {"source_id": 0, "roi": None},
                          "donor": {"source_id": 0, "roi": None}}
        self._excitationSeq = ""
        self._registrator = multicolor.Registrator()
        self._bleedThrough = {"background": 200.0, "factor": 0.0, "smooth": 1.0}

        self.propagateProperty("channels")
        self.propagateProperty("excitationSeq")
        self.propagateProperty("registrator")
        self.propagateProperty("bleedThrough")

    channels = gui.SimpleQtProperty("QVariantMap")
    excitationSeq = gui.SimpleQtProperty(str)
    registrator = gui.SimpleQtProperty(QtCore.QVariant)
    background = gui.SimpleQtProperty(float)
    bleedThrough = gui.SimpleQtProperty("QVariantMap")


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


class Backend(QtCore.QObject):
    _specialKeys = ["registration"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locAlgorithm = ""
        self._locOptions = {}
        self._trackOptions = {}
        self._filterOptions = {}
        self._datasets = DatasetCollection(self)
        self._specialDatasets = DatasetCollection(self)
        for k in self._specialKeys:
            self._specialDatasets.append(k)
        self._registrationLocOptions = {}
        self._saveFile = QtCore.QUrl()

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def datasets(self):
        return self._datasets

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def specialDatasets(self):
        return self._specialDatasets

    locAlgorithm = gui.SimpleQtProperty(str)
    locOptions = gui.SimpleQtProperty("QVariantMap")
    trackOptions = gui.SimpleQtProperty("QVariantMap")
    filterOptions = gui.SimpleQtProperty("QVariantMap")
    registrationLocOptions = gui.SimpleQtProperty("QVariantMap")
    saveFile = gui.SimpleQtProperty(QtCore.QUrl)

    registrationDatasetChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=registrationDatasetChanged)
    def registrationDataset(self):
        return self._specialDatasets.get(0, "dataset")

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
                "registration_loc": self.registrationLocOptions,
                "registrator": self._datasets.registrator,
                "bleed_through": self._datasets.bleedThrough,
                "filter_options": self.filterOptions}

        ypath = Path(url.toLocalFile())
        with ypath.open("w") as yf:
            io.yaml.safe_dump(data, yf)

        import tables, warnings
        with pd.HDFStore(ypath.with_suffix(".h5"), "w") as s:
            for i in range(self._datasets.rowCount()):
                ekey = self._datasets.get(i, "key")
                dset = self._datasets.get(i, "dataset")
                for j in range(dset.rowCount()):
                    dkey = dset.get(j, "key")
                    ld = dset.get(j, "locData")
                    if isinstance(ld, pd.DataFrame):
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore",
                                                  tables.NaturalNameWarning)
                            s.put(f"/{ekey}/{dkey}", ld)

        self.saveFile = QtCore.QUrl.fromLocalFile(str(ypath))

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
            self.registrationLocOptions = data["registration_loc"]
        if "registrator" in data:
            self._datasets.registrator = data["registrator"]
        if "bleed_through" in data:
            self._datasets.bleedThrough = data["bleed_through"]
        if "filter_options" in data:
            self.filterOptions = data["filter_options"]

        h5path = ypath.with_suffix(".h5")
        if h5path.exists():
            with pd.HDFStore(h5path, "r") as s:
                for i in range(self._datasets.rowCount()):
                    ekey = self._datasets.get(i, "key")
                    dset = self._datasets.get(i, "dataset")
                    for j in range(dset.rowCount()):
                        dkey = dset.get(j, "key")
                        with contextlib.suppress(KeyError):
                            dset.set(j, "locData", s.get(f"/{ekey}/{dkey}"))

        self.saveFile = QtCore.QUrl.fromLocalFile(str(ypath))

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

    @QtCore.pyqtSlot(QtCore.QVariant, int, int, bool, result=list)
    def getResults(self, figureCanvas, minLength, minCount, fitRates):
        if not self._datasets.rowCount():
            return [np.NaN, np.NaN]

        res = []
        for i in range(self._datasets.rowCount()):
            time = int(self._datasets.get(i, "key")) / 1000
            ds = self._datasets.get(i, "dataset")

            frameCounts = []
            for j in range(ds.rowCount()):
                df = ds.get(j, "locData")
                df = df[df["accepted"]]
                fc = df.groupby("particle")["frame"].apply(np.ptp)
                if not fc.empty:
                    # Exclude empty as they have float dtype, which does not
                    # work with np.bincount
                    frameCounts.append(fc)
            frameCounts = np.concatenate(frameCounts)
            # Need to ignore the first minLength - 1 values since all tracks
            # with lengths < minLength have been removed
            y = np.bincount(frameCounts)[minLength-1:]
            y = np.cumsum(y[::-1])[::-1]  # survival function
            x = np.arange(minLength-0.5, len(y)+minLength-1) * time
            use = np.ones(len(x), dtype=bool)
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

        res = sorted(res, key=lambda x: x[0], reverse=True)

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

        return [float(k_bleach), float(k_off)]
