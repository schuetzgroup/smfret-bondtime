import argparse
from pathlib import Path
import sys

from PyQt5 import QtCore, QtGui, QtQml, QtWidgets
from sdt import gui

from .backend import Backend, Dataset, Filter


app = QtWidgets.QApplication(sys.argv)
app.setOrganizationName("schuetzgroup")
app.setOrganizationDomain("biophysics.iap.tuwien.ac.at")
app.setApplicationName("FRETLifetimeAnalysis")
app.setApplicationVersion("0.1")

argp = argparse.ArgumentParser(
    description="Analyze bond lifetimes via smFRET data")
argp.add_argument("save", help="Save file", nargs="?")
args = argp.parse_args()

QtQml.qmlRegisterType(Backend, "BindingTime", 1, 0, "Backend")
QtQml.qmlRegisterType(Dataset, "BindingTime", 1, 0, "Dataset")
QtQml.qmlRegisterType(Filter, "BindingTime.Templates", 1, 0, "Filter")

gui.mpl_use_qt_font()

comp = gui.Component(Path(__file__).parent / "main.qml")
if comp.status_ == gui.Component.Status.Error:
        sys.exit(1)
if args.save is not None:
    comp.backend.load(args.save)

sys.exit(app.exec_())
