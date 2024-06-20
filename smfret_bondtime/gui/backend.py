import contextlib
from pathlib import Path

from PyQt5 import QtCore, QtQml
import numpy as np
import pandas as pd
from sdt import (brightness, changepoint, gui, helper, io, loc, multicolor,
                 spatial)
import trackpy

from ..analysis import calc_track_stats
from ..io import load_data


class Backend(QtCore.QObject):
    _specialKeys = ["registration"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locAlgorithm = ""
        self._locOptions = {}
        self._trackOptions = {}
        self._filterOptions = {}
        self._frameSel = multicolor.FrameSelector("")
        self._dataDir = ""
        self._datasets = gui.DatasetCollection()
        self._datasets.dataRoles = ["locData", "trackStats"]
        for k in self._specialKeys:
            self._datasets.append(k, special=True)
        self._registrationLocOptions = {}
        self._fitOptions = {}
        self._changepointOptions = {}
        self._saveFile = QtCore.QUrl()
        self._imagePipeline = None

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def datasets(self):
        return self._datasets

    dataDir = gui.SimpleQtProperty(str)
    locAlgorithm = gui.SimpleQtProperty(str)
    locOptions = gui.SimpleQtProperty("QVariantMap")
    trackOptions = gui.SimpleQtProperty("QVariantMap")
    filterOptions = gui.SimpleQtProperty("QVariantMap")
    registrationLocOptions = gui.SimpleQtProperty("QVariantMap")
    fitOptions = gui.SimpleQtProperty("QVariantMap")
    changepointOptions = gui.SimpleQtProperty("QVariantMap")
    saveFile = gui.SimpleQtProperty(QtCore.QUrl)
    imagePipeline = gui.SimpleQtProperty("QVariant")

    registrationDatasetChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(QtCore.QVariant, notify=registrationDatasetChanged)
    def registrationDataset(self):
        for i in range(self._datasets.count):
            if self._datasets.get(i, "key") == "registration":
                return self._datasets.get(i, "dataset")

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

    @QtCore.pyqtSlot(QtCore.QUrl)
    def save(self, url):
        dd = self.dataDir
        fl = self._datasets.fileLists
        for dsetFiles in fl.values():
            for entry in dsetFiles.values():
                for srcName, p in entry.items():
                    with contextlib.suppress(ValueError):
                        entry[srcName] = Path(p).relative_to(dd).as_posix()

        data = {
            "file_version": 3,
            "channels": self.imagePipeline.channels,
            "data_dir": self.dataDir,
            "excitation_seq": self.imagePipeline.excitationSeq,
            "loc_algorithm": self.locAlgorithm,
            "loc_options": self.locOptions,
            "track_options": self.trackOptions,
            "files": fl,
            "registration_loc": self.registrationLocOptions,
            "registrator": self.imagePipeline.registrator,
            "bleed_through": self.imagePipeline.bleedThrough,
            "filter_options": self.filterOptions,
            "changepoint_options": self.changepointOptions,
            "fit_options": self.fitOptions,
        }

        ypath = Path(url.toLocalFile()).with_suffix(".yaml")
        with ypath.open("w") as yf:
            io.yaml.safe_dump(data, yf)

        import tables
        import warnings
        with pd.HDFStore(ypath.with_suffix(".h5"), "w") as s, \
                warnings.catch_warnings():
            warnings.simplefilter("ignore", tables.NaturalNameWarning)
            for i in range(self._datasets.rowCount()):
                ekey = self._datasets.get(i, "key")
                dset = self._datasets.get(i, "dataset")
                for j in range(dset.rowCount()):
                    dkey = dset.get(j, "id")
                    ld = dset.get(j, "locData")
                    if isinstance(ld, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}/loc", ld)
                    ts = dset.get(j, "trackStats")
                    if isinstance(ts, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}/track_stats", ts)

        self.saveFile = QtCore.QUrl.fromLocalFile(str(ypath))

    @QtCore.pyqtSlot(QtCore.QUrl, result=QtCore.QVariant)
    def load(self, url):
        if isinstance(url, QtCore.QUrl):
            ypath = Path(url.toLocalFile())
        else:
            ypath = Path(url)
        try:
            data, tracks, trackStats = load_data(
                ypath, convert_interval=None, special=True
            )
        except (FileNotFoundError, RuntimeError):
            return

        if "channels" in data:
            self.imagePipeline.channels = data["channels"]
        if "data_dir" in data:
            self.dataDir = data["data_dir"]
        if "excitation_seq" in data:
            self.imagePipeline.excitationSeq = data["excitation_seq"]
        if "loc_algorithm" in data:
            self.locAlgorithm = data["loc_algorithm"]
        if "loc_options" in data:
            self.locOptions = data["loc_options"]
        if "track_options" in data:
            self.trackOptions = data["track_options"]
        if "registrator" in data:
            self.imagePipeline.registrator = data["registrator"]
        if "registration_loc" in data:
            self.registrationLocOptions = data["registration_loc"]
        if "bleed_through" in data:
            self.imagePipeline.bleedThrough = data["bleed_through"]
        if "filter_options" in data:
            self.filterOptions = data["filter_options"]
        if "fit_options" in data:
            self.fitOptions = data["fit_options"]
        if "changepoint_options" in data:
            self.changepointOptions = data["changepoint_options"]

        fl = data.get("files", {})
        if fl:
            self._datasets.fileLists = fl
            for i in range(self._datasets.count):
                self._datasets.set(
                    i, "special",
                    self._datasets.get(i, "key") in self._specialKeys)
            self.registrationDatasetChanged.emit()

        for i in range(self._datasets.rowCount()):
            intv = self._datasets.get(i, "key")
            dset = self._datasets.get(i, "dataset")
            for j in range(dset.rowCount()):
                fid = dset.get(j, "id")
                with contextlib.suppress(KeyError):
                    dset.set(j, "locData", tracks[intv][fid])
                with contextlib.suppress(KeyError):
                    dset.set(j, "trackStats", trackStats[intv][fid])

        self.saveFile = QtCore.QUrl.fromLocalFile(str(ypath))

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getLocateFunc(self):
        f = getattr(loc, self.locAlgorithm).batch
        opts = self.locOptions

        def locFunc(*files):
            try:
                imgs = {src: io.ImageSequence(f).open()
                        for src, f in zip(self.datasets.fileRoles, files)}
                pipe = self.imagePipeline.processFunc(imgs, "corrAcceptor")
                lc = f(pipe, **opts)
                orig_frame_count = pipe.orig_frame_count
            finally:
                for i in imgs.values():
                    i.close()
            # Since sdt-python 17.1, frame numbers are preserved when using
            # slices of ImageSequence.
            lc["frame"] = self.imagePipeline.frameSelector.renumber_frames(
                lc["frame"].to_numpy(), "d", n_frames=orig_frame_count)
            return lc

        return locFunc

    def trackExtraFrames(self, trc, nExtra, nFrames):
        if nExtra <= 0:
            trc["extra_frame"] = 0
            return trc
        trc_s = []
        for p, t in helper.split_dataframe(trc, "particle", type="DataFrame"):
            t.sort_values("frame", ignore_index=True, inplace=True)
            t["extra_frame"] = 0
            mini = t.loc[0, "frame"]
            pre = pd.DataFrame(
                {"frame": np.arange(max(0, mini - nExtra), mini),
                 "extra_frame": 1, "particle": p, "interp": 1,
                 "x": t.loc[0, "x"], "y": t.loc[0, "y"]})
            i = t.index[-1]
            maxi = t.loc[i, "frame"]
            post = pd.DataFrame(
                {"frame": np.arange(maxi + 1,
                                    min(maxi + nExtra + 1, nFrames)),
                 "extra_frame": 2, "particle": p, "interp": 1,
                 "x": t.loc[i, "x"], "y": t.loc[i, "y"]})
            a = pd.concat([pre, t, post], ignore_index=True)
            trc_s.append(a)
        return pd.concat(trc_s, ignore_index=True)


    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getTrackFunc(self):
        opts = self.trackOptions.copy()
        extra = opts.pop("extra_frames", 0)

        def trackFunc(locData, *files):
            trackpy.quiet()
            if locData.empty:
                trc = locData.copy()
                # This adds the "particle" column
                trc["particle"] = 0
                trc_stats = pd.DataFrame(
                    columns=["start", "end", "track_len", "censored", "bg", "mass"]
                )
            else:
                if "extra_frame" in locData:
                    locData = locData[locData["extra_frame"] == 0]
                trc = trackpy.link(locData, **opts)
                trc = spatial.interpolate_coords(trc)

                try:
                    imgs = {src: io.ImageSequence(f).open()
                            for src, f in zip(self.datasets.fileRoles, files)}
                    pipe = self.imagePipeline.processFunc(imgs, "corrAcceptor")
                    trc = self.trackExtraFrames(trc, extra, len(pipe))
                    brightness.from_raw_image(
                        trc, pipe, radius=3, mask="circle"
                    )
                    trc_stats = calc_track_stats(trc, len(pipe))
                except Exception:
                    trc_stats = pd.DataFrame(
                        columns=["start", "end", "track_len", "censored", "bg", "mass"]
                    )
                    raise
                finally:
                    for i in imgs.values():
                        i.close()
            trc_stats["filter_param"] = -1
            trc_stats["filter_manual"] = -1
            return trc, trc_stats

        return trackFunc

    # TODO: this should be in sdt.changepoint.utils
    @staticmethod
    def indices_to_segments(indices, length):
        seg = np.arange(len(indices) + 1)
        reps = np.diff(indices, prepend=0, append=length)
        return np.repeat(seg, reps)

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getChangepointFunc(self):
        opts = self.changepointOptions
        cp_det = changepoint.Pelt()

        def changepointFunc(tracks, stats):
            if len(tracks) < 1:
                return tracks.copy(), stats.copy()
            td = tracks.sort_values(["particle", "frame"])
            st = stats.copy()
            cps = []
            st["changepoints"] = -1
            for p, (idx, mass) in helper.split_dataframe(
                    td, "particle", ["mass"], type="array_list",
                    keep_index=True, sort=False):
                c = cp_det.find_changepoints(mass, **opts)
                s = self.indices_to_segments(c, len(mass))
                cps.append(pd.Series(s, index=idx))
                st.loc[p, "changepoints"] = len(c)
            td["mass_seg"] = pd.concat(cps)
            return td, st

        return changepointFunc


QtQml.qmlRegisterType(Backend, "SmFretBondTime", 1, 0, "Backend")
