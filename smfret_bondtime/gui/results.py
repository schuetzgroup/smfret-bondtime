import random

from PyQt5 import QtCore, QtQml, QtQuick
from sdt import gui

from ..analysis import LifetimeAnalyzer


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

        self._worker = gui.ThreadWorker(self._calcWorker)
        self._worker.finished.connect(self._workerFinished)
        self._worker.error.connect(self._workerError)

    @QtCore.pyqtSlot(result=int)
    def genRandomSeed(self):
        # at least on Windows only 32 bit can be used
        return random.randint(0, 1<<32-1)

    @QtCore.pyqtSlot()
    def calculate(self):
        self._worker.enabled = True
        self._worker(
            self.datasets,
            self.resultsFig.figure,
            self.minLength,
            self.minCount,
            self.nBoot,
            self.randomSeed,
        )

    @staticmethod
    def _calcWorker(datasets, fig, minLength, minCount, nBoot, randomSeed):
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
        for a in fig.axes:
            a.cla()
        ana.plot(fig.axes[0])
        ana.plot_censor_stats(fig.axes[1])
        for a in fig.axes:
            a.legend(loc=0)
        fig.canvas.draw_idle()

    def _workerFinished(self):
        self._worker.enabled = False

    def _workerError(self, e):
        print("error", e)
        self._worker.enabled = False


QtQml.qmlRegisterType(Results, "SmFretBondTime.Templates", 1, 0, "Results")
