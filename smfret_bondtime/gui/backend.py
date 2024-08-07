# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import contextlib
from pathlib import Path

from PyQt5 import QtCore, QtQml
import numpy as np
import pandas as pd
from sdt import brightness, changepoint, gui, helper, io, loc, multicolor, spatial
import trackpy

from ..analysis import calc_track_stats
from ..io import load_data, special_keys


class Backend(QtCore.QObject):
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
        for k in special_keys:
            self._datasets.append(k, special=True)
        self._registrationLocOptions = {}
        self._fitOptions = {}
        self._changepointOptions = {}
        self._saveFile = QtCore.QUrl()
        self._imagePipeline = None

        self._wrk = gui.ThreadWorker(self._workerDispatch)
        self._wrk.finished.connect(self._wrkFinishedOk)
        self._wrk.error.connect(self._wrkFinishedError)
        self._wrkError = ""

    @QtCore.pyqtProperty(QtCore.QVariant, constant=True)
    def datasets(self):
        return self._datasets

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

    dataDirChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=dataDirChanged)
    def dataDir(self):
        return self._dataDir

    @dataDir.setter
    def dataDir(self, d):
        if self._dataDir == d:
            return
        for i in range(self._datasets.rowCount()):
            dset = self._datasets.get(i, "dataset")
            roles = dset.fileRoles
            for j in range(dset.rowCount()):
                for r in roles:
                    old = Path(dset.get(j, r))
                    with contextlib.suppress(ValueError):
                        rel = old.relative_to(self._dataDir)
                        dset.set(j, r, (d / rel).as_posix())
        self._dataDir = d
        self.dataDirChanged.emit()

    @QtCore.pyqtProperty(QtCore.QObject, constant=True)
    def _worker(self):
        return self._wrk

    _workerErrorChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=_workerErrorChanged)
    def _workerError(self):
        return self._wrkError

    @QtCore.pyqtSlot(QtCore.QUrl)
    def save(self, url):
        if self._wrkError:
            self._wrkError = ""
            self._workerErrorChanged.emit()
        self._wrk.enabled = True

        yaml_path = Path(url.toLocalFile()).with_suffix(".yaml")

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

        # write to disk in different thread
        self._wrk("save", yaml_path, data, self._datasets)

        self.saveFile = QtCore.QUrl.fromLocalFile(str(yaml_path))

    @QtCore.pyqtSlot(QtCore.QUrl, result=QtCore.QVariant)
    def load(self, url):
        if self._wrkError:
            self._wrkError = ""
            self._workerErrorChanged.emit()
        self._wrk.enabled = True

        if isinstance(url, QtCore.QUrl):
            yaml_path = Path(url.toLocalFile())
        else:
            yaml_path = Path(url)

        # load in different thread
        self._wrk("load", yaml_path)

        self.saveFile = QtCore.QUrl.fromLocalFile(str(yaml_path))

    @staticmethod
    def _workerDispatch(action, *args, **kwargs):
        if action == "save":
            ret = __class__._saveFunc(*args, **kwargs)
        elif action == "load":
            ret = __class__._loadFunc(*args, **kwargs)
        else:
            raise ValueError(f"unknown action {action}")

        return action, ret

    @staticmethod
    def _saveFunc(yaml_path, yaml_data, datasets):
        tmp_yaml_path = yaml_path.with_suffix(".tmp.yaml")
        h5_path = yaml_path.with_suffix(".h5")
        tmp_h5_path = yaml_path.with_suffix(".tmp.h5")

        try:
            with tmp_yaml_path.open("w") as yf:
                io.yaml.safe_dump(yaml_data, yf)

            import tables
            import warnings

            with pd.HDFStore(tmp_h5_path, "w") as s, warnings.catch_warnings():
                warnings.simplefilter("ignore", tables.NaturalNameWarning)
                for i in range(datasets.rowCount()):
                    ekey = datasets.get(i, "key")
                    dset = datasets.get(i, "dataset")
                    for j in range(dset.rowCount()):
                        dkey = dset.get(j, "id")
                        ld = dset.get(j, "locData")
                        if isinstance(ld, pd.DataFrame):
                            s.put(f"/{ekey}/{dkey}/loc", ld)
                        ts = dset.get(j, "trackStats")
                        if isinstance(ts, pd.DataFrame):
                            s.put(f"/{ekey}/{dkey}/track_stats", ts)

            tmp_yaml_path.replace(yaml_path)
            tmp_h5_path.replace(h5_path)
        finally:
            tmp_yaml_path.unlink(missing_ok=True)
            tmp_h5_path.unlink(missing_ok=True)

    @staticmethod
    def _loadFunc(yaml_path):
        return load_data(yaml_path, convert_interval=None, special=True)

    def _wrkFinishedOk(self, result):
        self._wrk.enabled = False
        if result[0] != "load":
            return

        data, tracks, trackStats = result[1]

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
                    i, "special", self._datasets.get(i, "key") in special_keys
                )
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

    def _wrkFinishedError(self, e):
        self._wrkError = str(e)
        self._workerErrorChanged.emit()
        self._wrk.enabled = False

    @QtCore.pyqtSlot(result=QtCore.QVariant)
    def getLocateFunc(self):
        f = getattr(loc, self.locAlgorithm).batch
        opts = self.locOptions

        def locFunc(*files):
            try:
                imgs = {
                    src: io.ImageSequence(f).open()
                    for src, f in zip(self.datasets.fileRoles, files)
                }
                pipe = self.imagePipeline.processFunc(imgs, "corrAcceptor")
                lc = f(pipe, **opts)
                orig_frame_count = pipe.orig_frame_count
            finally:
                for i in imgs.values():
                    i.close()
            # Since sdt-python 17.1, frame numbers are preserved when using
            # slices of ImageSequence.
            lc["frame"] = self.imagePipeline.frameSelector.renumber_frames(
                lc["frame"].to_numpy(), "d", n_frames=orig_frame_count
            )
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
                {
                    "frame": np.arange(max(0, mini - nExtra), mini),
                    "extra_frame": 1,
                    "particle": p,
                    "interp": 1,
                    "x": t.loc[0, "x"],
                    "y": t.loc[0, "y"],
                }
            )
            i = t.index[-1]
            maxi = t.loc[i, "frame"]
            post = pd.DataFrame(
                {
                    "frame": np.arange(maxi + 1, min(maxi + nExtra + 1, nFrames)),
                    "extra_frame": 2,
                    "particle": p,
                    "interp": 1,
                    "x": t.loc[i, "x"],
                    "y": t.loc[i, "y"],
                }
            )
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
                locData = locData[~locData["x"].isnull() & ~locData["y"].isnull()]
                trc = trackpy.link(locData, **opts)
                trc = spatial.interpolate_coords(trc)

                try:
                    imgs = {
                        src: io.ImageSequence(f).open()
                        for src, f in zip(self.datasets.fileRoles, files)
                    }
                    pipe = self.imagePipeline.processFunc(imgs, "corrAcceptor")
                    trc = self.trackExtraFrames(trc, extra, len(pipe))
                    brightness.from_raw_image(trc, pipe, radius=3, mask="circle")
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
                td, "particle", ["mass"], type="array_list", keep_index=True, sort=False
            ):
                c = cp_det.find_changepoints(mass, **opts)
                s = self.indices_to_segments(c, len(mass))
                cps.append(pd.Series(s, index=idx))
                st.loc[p, "changepoints"] = len(c)
            td["mass_seg"] = pd.concat(cps)
            return td, st

        return changepointFunc


QtQml.qmlRegisterType(Backend, "SmFretBondTime", 1, 0, "Backend")
