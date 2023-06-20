import argparse
from pathlib import Path
import sys

from PyQt5 import QtCore, QtGui, QtQml, QtWidgets
import matplotlib as mpl
from sdt import gui

from .backend import Backend
from .changepoints import Changepoints
from .filter import Filter
from .image_pipeline import LifetimeImagePipeline
from .track_navigator import TrackNavigator

mpl.rcParams["axes.unicode_minus"] = False

app = QtWidgets.QApplication(sys.argv)
app.setOrganizationName("schuetzgroup")
app.setOrganizationDomain("biophysics.iap.tuwien.ac.at")
app.setApplicationName("FRETLifetimeAnalysis")
app.setApplicationVersion("0.1")

argp = argparse.ArgumentParser(
    description="Analyze bond lifetimes via smFRET data")
argp.add_argument("save", help="Save file", nargs="?", type=Path)
args = argp.parse_args()

QtQml.qmlRegisterType(Backend, "BindingTime", 1, 0, "Backend")
QtQml.qmlRegisterType(LifetimeImagePipeline, "BindingTime", 1, 0,
                      "LifetimeImagePipeline")
QtQml.qmlRegisterType(Filter, "BindingTime.Templates", 1, 0, "Filter")
QtQml.qmlRegisterType(Changepoints, "BindingTime.Templates", 1, 0,
                      "Changepoints")
QtQml.qmlRegisterType(TrackNavigator, "BindingTime.Templates", 1, 0,
                      "TrackNavigator")

gui.mpl_use_qt_font()

comp = gui.Component(Path(__file__).parent / "main.qml")
comp.create()
if comp.status_ == gui.Component.Status.Error:
        sys.exit(1)
if args.save is not None:
    comp.backend.load(args.save.resolve())

sys.exit(app.exec_())
