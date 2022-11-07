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
import trackpy


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
            # Remember frame count. Necessary to adjust frame numbers after
            # localization in slices. See `Backend.getLocateFunc`.
            cnt = len(seq)
            if chan["roi"] is not None:
                seq = chan["roi"](seq)
            if self._frameSel.excitation_seq:
                seq = self._frameSel.select(seq, "d")
            if role == "donor":
                # FIXME: Is donor garanteed to be channel 2?
                seq = self._registrator(seq, channel=2,
                                        cval=self._bleedThrough["background"])
            seq.orig_frame_count = cnt
            return seq
        if role == "corrAcceptor":
            d = self.get(index, "donor")
            a = self.get(index, "acceptor")
            bg = self._bleedThrough["background"]
            bt = self._bleedThrough["factor"]
            smt = self._bleedThrough["smooth"]

            def corr(donor, acceptor):
                noBg = np.asanyarray(donor, dtype=float) - bg
                if smt >= 1e-3:
                    noBg = scipy.ndimage.gaussian_filter(noBg, smt)
                return acceptor - noBg * bt

            return helper.Pipeline(corr, d, a,
                                   propagate_attrs={"orig_frame_count"})
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
        self._fitOptions = {}
        self._saveFile = QtCore.QUrl()
        self._survivalFuncs = {}
        self._survivalFits = None
        self._finalFit = None

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
    fitOptions = gui.SimpleQtProperty("QVariantMap")
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
                "filter_options": self.filterOptions,
                "fit_options": self.fitOptions}

        ypath = Path(url.toLocalFile()).with_suffix(".yaml")
        with ypath.open("w") as yf:
            io.yaml.safe_dump(data, yf)

        import tables, warnings
        with pd.HDFStore(ypath.with_suffix(".h5"), "w") as s, \
                warnings.catch_warnings():
            warnings.simplefilter("ignore", tables.NaturalNameWarning)
            for i in range(self._datasets.rowCount()):
                ekey = self._datasets.get(i, "key")
                dset = self._datasets.get(i, "dataset")
                for j in range(dset.rowCount()):
                    dkey = dset.get(j, "key")
                    ld = dset.get(j, "locData")
                    if isinstance(ld, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}", ld)
            for t, df in self._survivalFuncs.items():
                s.put(f"/survival_funcs/{t}", df)
            if self._survivalFits is not None:
                s.put("/survival_fits", self._survivalFits)
            if self._finalFit is not None:
                s.put("/final_fit", self._finalFit)

        self.saveFile = QtCore.QUrl.fromLocalFile(str(ypath))

    @QtCore.pyqtSlot(QtCore.QUrl, result=QtCore.QVariant)
    def load(self, url):
        if isinstance(url, QtCore.QUrl):
            ypath = Path(url.toLocalFile())
        else:
            ypath = Path(url)
        try:
            with ypath.open() as yf:
                data = io.yaml.safe_load(yf)
        except FileNotFoundError:
            return

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
        if "fit_options" in data:
            self.fitOptions = data["fit_options"]

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
        fsel = multicolor.FrameSelector(self.datasets.excitationSeq)

        def locFunc(fretImage):
            lc = f(fretImage, **opts)
            # Since sdt-python 17.1, frame numbers are preserved when using
            # slices of ImageSequence.
            lc["frame"] = fsel.renumber_frames(
                lc["frame"].to_numpy(), "d",
                n_frames=fretImage.orig_frame_count)
            brightness.from_raw_image(lc, fretImage, radius=3, mask="circle")
            return lc

        return locFunc

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getTrackFunc(self):
        opts = self.trackOptions

        def trackFunc(locData):
            trackpy.quiet()
            if locData.empty:
                trc = locData.copy()
                # This adds the "particle" column
                trc["particle"] = 0
            else:
                trc = trackpy.link(locData, **opts)
            trc["filter_param"] = -1
            trc["filter_manual"] = -1
            return trc

        return trackFunc

    @staticmethod
    def survivalModelRates(x, a, k):
        return a * np.exp(-k * x)

    @staticmethod
    def survivalModelTimes(x, a, t):
        return a * np.exp(-x / t)

    @staticmethod
    def lifetimeModel(t_frame, t_off, t_bleach):
        return 1 / (1 / t_off + 1 / (t_bleach * t_frame))

    @QtCore.pyqtSlot(QtCore.QVariant, int, int, bool, result="QVariantMap")
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
                df = df[(df["filter_param"] == 0) & (df["filter_manual"] == 0)]
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

            r = {"time": time,
                 "surv": pd.DataFrame({"t": x, "count": y, "use": use})}
            try:
                fit_x = x[use]
                fit_y = y[use]
                # estimate amplitude as number of events
                a = fit_y[0]
                # estimate 1 / rate as mean of survival times
                m = np.sum(fit_x * fit_y) / np.sum(fit_y)

                if fitRates:
                    fit, cov = scipy.optimize.curve_fit(
                        self.survivalModelRates, fit_x, fit_y, p0=[a, 1 / m])
                    err = np.sqrt(np.diag(cov))
                    r["rate_fit"] = fit
                    r["rate_err"] = err
                    r["tau_fit"] = [fit[0], 1 / fit[1]]
                    # error propagation for x -> 1 / x
                    r["tau_err"] = [err[0], 1 / (fit[1] * fit[1]) * err[1]]
                else:
                    fit, cov = scipy.optimize.curve_fit(
                        self.survivalModelTimes, fit_x, fit_y, p0=[a, m])
                    err = np.sqrt(np.diag(cov))
                    r["tau_fit"] = fit
                    r["tau_err"] = err
                    r["rate_fit"] = [fit[0], 1 / fit[1]]
                    # error propagation for x -> 1 / x
                    r["rate_err"] = [err[0], 1 / (fit[1] * fit[1]) * err[1]]
            except (IndexError, TypeError):
                # IndexError: a = fit_y[0] fails because there isn't a single
                # data point
                # TypeError: Not enough data for curve_fit
                r["tau_fit"] = r["tau_err"] = r["rate_fit"] = r["rate_err"] = \
                    [np.NaN] * 2
            res.append(r)

        res = sorted(res, key=lambda x: x["time"])
        self._survivalFuncs = {x["time"]: x["surv"] for x in res}
        sf= {"t": [x["time"] for x in res],
             "count": [x["rate_fit"][0] for x in res],
             "count_err": [x["rate_err"][0] for x in res],
             "rate": [x["rate_fit"][-1] for x in res],
             "rate_err": [x["rate_err"][-1] for x in res],
             "tau": [x["tau_fit"][-1] for x in res],
             "tau_err": [x["tau_err"][-1] for x in res]}
        self._survivalFits = pd.DataFrame(sf)
        validFits = self._survivalFits[np.all(np.isfinite(self._survivalFits),
                                              axis=1)]

        fig = figureCanvas.figure
        fig.clf()
        fig.set_constrained_layout(True)
        grid = fig.add_gridspec(2, 1)

        survAx = fig.add_subplot(grid[0])
        for i, r in enumerate(res):
            t = r["time"]
            d = r["surv"]
            fit = r["rate_fit"]
            color = f"C{i%10}"
            d1 = d[d["use"]]
            survAx.scatter(d1["t"], d1["count"], marker="o", edgecolor="none",
                           facecolor=color, alpha=0.5)
            d2 = d[~d["use"]]
            survAx.scatter(d2["t"], d2["count"], marker="o", edgecolor=color,
                           facecolor="none", alpha=0.5)
            x_fit = np.linspace(d["t"].min(), d["t"].max(), 100)
            survAx.plot(x_fit, self.survivalModelRates(x_fit, *fit),
                        color=color,
                        label=f"{t*1000:.0f} ms ({1 / t:.1f} fps)")
        survAx.legend(loc=0)
        survAx.set_title("survival functions")
        survAx.set_xlabel("survival time [s]")
        survAx.set_ylabel("cumulated count")

        k_bleach, k_off = np.polyfit(1 / validFits["t"], validFits["rate"], 1)

        if fitRates:
            rates, rates_cov = scipy.optimize.curve_fit(
                lambda x, ko, kb: ko + x * kb, 1 / validFits["t"],
                validFits["rate"], p0=[k_off, k_bleach],
                sigma=validFits["rate_err"], absolute_sigma=True)
            k_off, k_bleach = rates
            k_off_err, k_bleach_err = np.sqrt(np.diag(rates_cov))
            t_off = 1 / k_off
            t_off_err = 1 / (k_off * k_off) * k_off_err
            t_bleach = 1 / k_bleach
            t_bleach_err = 1 / (k_bleach * k_bleach) * k_bleach_err
            rateAx = fig.add_subplot(grid[1])
            rateAx.errorbar(1 / validFits["t"], validFits["rate"],
                            validFits["rate_err"], fmt=".")
            rateAx.set_title("measured off-rates")
            rateAx.set_xlabel("frame rate [fps]")
            rateAx.set_ylabel("apparent off-rate [s$^{-1}$]")
            x_r = np.array([1 / validFits["t"].iloc[-1],
                            1 / validFits["t"].iloc[0]])
            y_r = k_off + k_bleach * x_r
            rateAx.plot(x_r, y_r, "C0")
        else:
            times, times_cov = scipy.optimize.curve_fit(
                self.lifetimeModel, validFits["t"], validFits["tau"],
                p0=[1 / k_off, 1 / k_bleach], sigma=validFits["tau_err"],
                absolute_sigma=True)
            t_off, t_bleach = times
            t_off_err, t_bleach_err = np.sqrt(np.diag(times_cov))
            k_off = 1 / t_off
            k_off_err = 1 / (t_off * t_off) * t_off_err
            k_bleach = 1 / t_bleach
            k_bleach_err = 1 / (t_bleach * t_bleach) * t_bleach_err
            timeAx = fig.add_subplot(grid[1])
            timeAx.errorbar(validFits["t"] * 1000, validFits["tau"],
                            validFits["tau_err"], fmt=".")
            timeAx.set_title("measured lifetimes")
            timeAx.set_xlabel("time per frame [ms]")
            timeAx.set_ylabel("apparent lifetime [s]")
            x_t = np.linspace(validFits["t"].iloc[0], validFits["t"].iloc[-1],
                              100)
            y_t = self.lifetimeModel(x_t, t_off, t_bleach)
            timeAx.plot(x_t * 1000, y_t, "C0")

        figureCanvas.draw_idle()

        ret = {"k_bleach": float(k_bleach),
               "k_bleach_err": float(k_bleach_err),
               "k_off": float(k_off), "k_off_err": float(k_off_err),
               "t_bleach": float(t_bleach),
               "t_bleach_err": float(t_bleach_err),
               "t_off": float(t_off), "t_off_err": float(t_off_err)}
        self._finalFit = pd.Series(ret)
        return ret
