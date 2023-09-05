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
from sdt import (brightness, changepoint, gui, helper, io, loc, multicolor,
                 spatial)
import trackpy


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
        self._datasets.dataRoles = ["locData"]
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

        data = {"file_version": 2,
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
                "fit_options": self.fitOptions,
                "changepoint_options": self.changepointOptions}

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
                    dkey = dset.get(j, "id")
                    ld = dset.get(j, "locData")
                    if isinstance(ld, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}", ld)
            # for t, df in self._survivalFuncs.items():
            #     s.put(f"/survival_funcs/{t}", df)
            # if self._survivalFits is not None:
            #     s.put("/survival_fits", self._survivalFits)
            # if self._finalFit is not None:
            #     s.put("/final_fit", self._finalFit)

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
            ch = data["channels"]
            for v in ch.values():
                if "source" not in v:
                    # sdt-python <= 17.4 YAML file
                    v["source"] = f"source_{v.pop('source_id')}"
            self.imagePipeline.channels = ch
        if "data_dir" in data:
            self.dataDir = data["data_dir"]
        if "excitation_seq" in data:
            self.imagePipeline.excitationSeq = data["excitation_seq"]
        if "loc_algorithm" in data:
            self.locAlgorithm = data["loc_algorithm"]
        if "loc_options" in data:
            self.locOptions = data["loc_options"]
        if "track_options" in data:
            t = data["track_options"]
            t.setdefault("extra_frames", 0)  # sdt-python <= 17.4 YAML file
            self.trackOptions = data["track_options"]
        if "registrator" in data:
            reg = data["registrator"]
            if set(reg.channel_names) != {"acceptor", "donor"}:
                reg.channel_names = ["acceptor", "donor"]
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

        dd = Path(self.dataDir)
        # older YAML files store special dataset files under "special_files"
        all_files = {**data.get("special_files", {}), **data.get("files", {})}
        if all_files:
            for interval, files in all_files.items():
                if isinstance(files, list):
                    # older YAML files store list of file names
                    all_files[interval] = {n: f for n, f in enumerate(files)}
            for files in all_files.values():
                for entry in files.values():
                    for src, f in entry.items():
                        # Replace backslashes by forward slashes
                        # On Windows and sdt-python <= 17.4 paths were saved
                        # with backslashes
                        f = f.replace("\\", "/")
                        entry[src] = (dd / f).as_posix()
            self._datasets.fileLists = all_files
            for i in range(self._datasets.count):
                self._datasets.set(
                    i, "special",
                    self._datasets.get(i, "key") in self._specialKeys)
            self.registrationDatasetChanged.emit()
        h5path = ypath.with_suffix(".h5")
        if h5path.exists():
            with pd.HDFStore(h5path, "r") as s:
                for i in range(self._datasets.rowCount()):
                    ekey = self._datasets.get(i, "key")
                    dset = self._datasets.get(i, "dataset")
                    for j in range(dset.rowCount()):
                        # new files use the file ID as key
                        dkey = [dset.get(j, "id")]
                        try:
                            # old files use the file name as key
                            dpath = Path(dset.get(j, "source_0")).relative_to(dd)
                            # try with forward slashes
                            dpath = dpath.as_posix()
                            dkey.append(dpath)
                            # try with backward slashes (sdt-python <= 17.4)
                            dpath_bs = dpath.replace("/", "\\")
                            dkey.append(dpath_ps)
                        except Exception:
                            pass

                        for k in dkey:
                            try:
                                dset.set(j, "locData", s.get(f"/{ekey}/{k}"))
                            except KeyError:
                                pass
                            else:
                                break

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
                    brightness.from_raw_image(trc, pipe, radius=3,
                                              mask="circle")
                finally:
                    for i in imgs.values():
                        i.close()

            trc["filter_param"] = -1
            trc["filter_manual"] = -1
            return trc

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

        def changepointFunc(trackData):
            if len(trackData) < 1:
                return trackData.copy()
            td = trackData.sort_values(["particle", "frame"])
            cps = []
            for p, (idx, mass) in helper.split_dataframe(
                    td, "particle", ["mass"], type="array_list",
                    keep_index=True, sort=False):
                c = cp_det.find_changepoints(mass, **opts)
                s = self.indices_to_segments(c, len(mass))
                cps.append(pd.Series(s, index=idx))
            td["mass_seg"] = pd.concat(cps)
            return td

        return changepointFunc
