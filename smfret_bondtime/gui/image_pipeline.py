# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import contextlib
import math
from typing import Dict

from PyQt5 import QtCore, QtQml
import numpy as np
import scipy.ndimage
from sdt import gui, helper, multicolor


class LifetimeImagePipeline(gui.BasicImagePipeline):
    def __init__(self, parent: QtCore.QObject = None):
        super().__init__(parent)
        self._bleedThrough = {"background": 200.0, "factor": 0.0, "smooth": 1.0}
        self._channels = {
            "donor": {"roi": None, "source": "source_0"},
            "acceptor": {"roi": None, "source": "source_0"},
        }
        self.frameSelector = multicolor.FrameSelector("")
        self._registrator = multicolor.Registrator()
        self._registrator.channel_names = list(self.channels)

        self.bleedThroughChanged.connect(self._doProcessIfCorrAcceptor)
        self.channelsChanged.connect(self.doProcess)
        self.excitationSeqChanged.connect(self.doProcess)
        self.registratorChanged.connect(self._doProcessIfCorrAcceptor)

    channels: Dict = gui.SimpleQtProperty("QVariantMap")
    registrator: multicolor.Registrator = gui.SimpleQtProperty("QVariant")

    excitationSeqChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=excitationSeqChanged)
    def excitationSeq(self) -> str:
        return self.frameSelector.excitation_seq

    @excitationSeq.setter
    def excitationSeq(self, s):
        if s == self.frameSelector.excitation_seq:
            return
        self.frameSelector.excitation_seq = s
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

    def _doProcessIfCorrAcceptor(self):
        if self.currentChannel == "corrAcceptor":
            self.doProcess()

    def processFunc(self, imageSeqs, channel):
        if channel in ("donor", "acceptor"):
            ch = self._channels.get(channel, {})
            r = ch.get("roi")
            s = ch.get("source")
            if s is not None:
                seq = imageSeqs.get(s)
            if r is not None:
                seq = r(seq)
            if channel == "donor":
                seq = self._registrator(
                    seq, channel="donor", cval=self._bleedThrough["background"]
                )

            # Remember frame count. Necessary to adjust frame numbers after
            # localization in slices. See `Backend.getLocateFunc`.
            cnt = len(seq)

            if seq is not None:
                seq = self.frameSelector.select(seq, "d")

            seq.orig_frame_count = cnt
            return seq
        if channel.startswith("corrAcceptor"):
            d = self.processFunc(imageSeqs, "donor")
            a = self.processFunc(imageSeqs, "acceptor")
            bg = self._bleedThrough["background"]
            bt = self._bleedThrough["factor"]
            smt = self._bleedThrough["smooth"]

            def corr(donor, acceptor):
                noBg = np.asanyarray(donor, dtype=float) - bg
                if smt >= 1e-3:
                    noBg = scipy.ndimage.gaussian_filter(noBg, smt)
                return acceptor - noBg * bt

            seq = helper.Pipeline(corr, d, a, propagate_attrs={"orig_frame_count"})
            return seq


QtQml.qmlRegisterType(
    LifetimeImagePipeline, "SmFretBondTime", 1, 0, "LifetimeImagePipeline"
)
