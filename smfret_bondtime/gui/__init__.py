# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
from pathlib import Path
import sys

from PyQt5 import QtWidgets
import matplotlib as mpl
from sdt import gui

from .backend import Backend
from .changepoints import Changepoints
from .filter import Filter
from .image_pipeline import LifetimeImagePipeline
from .results import Results
from .track_navigator import TrackNavigator
from .._version import __version__


def run():
    mpl.rcParams["axes.unicode_minus"] = False

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("schuetzgroup")
    app.setOrganizationDomain("biophysics.iap.tuwien.ac.at")
    app.setApplicationName("SmFretBondTime")
    app.setApplicationVersion(__version__)

    argp = argparse.ArgumentParser(description="Analyze bond lifetimes via smFRET data")
    argp.add_argument("save", help="Save file", nargs="?", type=Path)
    args = argp.parse_args()

    if sys.platform != "win32":
        gui.mpl_use_qt_font()

    comp = gui.Component(Path(__file__).parent / "main.qml")
    comp.create()
    if comp.status_ == gui.Component.Status.Error:
        return 1
    if args.save is not None:
        comp.backend.load(args.save.resolve())

    return app.exec_()
