# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
from pathlib import Path
import sys

from PyQt5 import QtWidgets
import matplotlib as mpl
from sdt import gui

# need to import so that QML types get registered
from . import gui as bond_gui  # noqa: F401


mpl.rcParams["axes.unicode_minus"] = False

app = QtWidgets.QApplication(sys.argv)
app.setOrganizationName("schuetzgroup")
app.setOrganizationDomain("biophysics.iap.tuwien.ac.at")
app.setApplicationName("SmFretBondTime")
app.setApplicationVersion("0.1")

argp = argparse.ArgumentParser(
    description="Analyze bond lifetimes via smFRET data")
argp.add_argument("save", help="Save file", nargs="?", type=Path)
args = argp.parse_args()

if sys.platform != "win32":
    gui.mpl_use_qt_font()

comp = gui.Component(Path(__file__).parent / "gui" / "main.qml")
comp.create()
if comp.status_ == gui.Component.Status.Error:
        sys.exit(1)
if args.save is not None:
    comp.backend.load(args.save.resolve())

sys.exit(app.exec_())
