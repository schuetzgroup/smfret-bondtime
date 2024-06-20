# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import random

from PyQt5 import QtCore, QtQml, QtQuick
import pandas as pd
from sdt import gui

from ..analysis import LifetimeAnalyzer, concat_stats


class Results(QtQuick.QQuickItem):
    resultsFig = gui.QmlDefinedProperty()
    datasets = gui.SimpleQtProperty("QVariant")
    minLength = gui.SimpleQtProperty(int)
    minCount = gui.QmlDefinedProperty()
    nBoot = gui.QmlDefinedProperty()
    randomSeed = gui.QmlDefinedProperty()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._datasets = None
        self._minLength = 1
        self._calcError = ""
        self._analyzer = None

        self._wrk = gui.ThreadWorker(self._workerDispatch)
        self._wrk.finished.connect(self._wrkFinishedOk)
        self._wrk.error.connect(self._wrkFinishedError)

        self._wrkError = ""

    @QtCore.pyqtProperty(QtCore.QObject, constant=True)
    def _worker(self):
        return self._wrk

    resultAvailableChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(bool, notify=resultAvailableChanged)
    def resultAvailable(self):
        return self._analyzer is not None

    _workerErrorChanged = QtCore.pyqtSignal()

    @QtCore.pyqtProperty(str, notify=_workerErrorChanged)
    def _workerError(self):
        return self._wrkError

    @QtCore.pyqtSlot(result=int)
    def genRandomSeed(self):
        # at least on Windows only 32 bit can be used
        return random.randint(0, 1 << 32 - 1)

    @QtCore.pyqtSlot()
    def calculate(self):
        if self._wrkError:
            self._wrkError = ""
            self._workerErrorChanged.emit()
        self._wrk.enabled = True
        self._wrk(
            "calculate",
            self.datasets,
            self.resultsFig.figure,
            self.minLength,
            self.minCount,
            self.nBoot,
            self.randomSeed,
        )

    @QtCore.pyqtSlot(QtCore.QUrl)
    def exportResults(self, url):
        if self._wrkError:
            self._wrkError = ""
            self._workerErrorChanged.emit()
        self._wrk.enabled = True
        self._wrk("export_results", url, self._analyzer)

    @QtCore.pyqtSlot(QtCore.QUrl)
    def exportFigure(self, url):
        if self._wrkError:
            self._wrkError = ""
            self._workerErrorChanged.emit()
        self._wrk.enabled = True
        self._wrk("export_figure", url, self.resultsFig.figure)

    @staticmethod
    def _workerDispatch(action, *args, **kwargs):
        if action == "calculate":
            ret = __class__._calcFunc(*args, **kwargs)
        elif action == "export_results":
            ret = __class__._exportResultsFunc(*args, **kwargs)
        elif action == "export_figure":
            ret = __class__._exporFigureFunc(*args, **kwargs)
        else:
            raise ValueError(f"unknown action {action}")

        return action, ret

    @staticmethod
    def _calcFunc(datasets, fig, minLength, minCount, nBoot, randomSeed):
        if datasets is None:
            return

        tstats = {}
        for i in range(datasets.rowCount()):
            if datasets.get(i, "special"):
                continue
            intv = float(datasets.get(i, "key"))
            dset = datasets.get(i, "dataset")
            for j in range(dset.rowCount()):
                fid = dset.get(j, "id")
                ts = dset.get(j, "trackStats")
                tstats.setdefault(intv, {})[fid] = ts

        ana = LifetimeAnalyzer(
            tstats, min_track_length=minLength, min_track_count=minCount
        )
        if nBoot < 2:
            ana.calc_lifetime()
        else:
            ana.calc_lifetime_bootstrap(nBoot, randomSeed)

        if not fig.axes:
            fig.add_subplot(1, 2, 1)
            fig.add_subplot(1, 2, 2)
            fig.set_constrained_layout(True)
        for a in fig.axes:
            a.cla()
        ana.plot(fig.axes[0])
        ana.plot_censor_stats(fig.axes[1])
        for a in fig.axes:
            a.legend(loc=0)
        fig.canvas.draw_idle()

        return ana

    @staticmethod
    def _exportResultsFunc(url, analyzer):
        with pd.ExcelWriter(url.toLocalFile()) as ew:
            lt = analyzer.lifetime
            res = pd.DataFrame(
                [[lt.lifetime, lt.lifetime_err], [lt.bleach, lt.bleach_err]],
                index=["lifetime", "bleach"],
                columns=["value", "standard error"],
            )
            res.to_excel(ew, sheet_name="lifetime")
            analyzer.apparent_lifetimes.to_excel(ew, sheet_name="apparent lifetimes")

            tstats = concat_stats(analyzer.track_stats, filter=False)
            for intv, ts in tstats.items():
                ts.to_excel(ew, sheet_name=f"interval {intv}")

    @staticmethod
    def _exporFigureFunc(url, figure):
        figure.savefig(url.toLocalFile())

    def _wrkFinishedOk(self, result):
        self._wrk.enabled = False
        if result[0] == "calculate":
            a = self.resultAvailable
            self._analyzer = result[1]
            if not a:
                self.resultAvailableChanged.emit()

    def _wrkFinishedError(self, e):
        self._wrkError = str(e)
        self._workerErrorChanged.emit()
        self._wrk.enabled = False


QtQml.qmlRegisterType(Results, "SmFretBondTime.Templates", 1, 0, "Results")
