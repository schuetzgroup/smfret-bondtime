# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

from collections import namedtuple
from contextlib import suppress
import copy
import math
from typing import Any, Iterable, Mapping, Optional, Tuple
import warnings

import lifelines
import matplotlib as mpl
import matplotlib.axes  # noqa F401
import numpy as np
import pandas as pd
import scipy.optimize

from .sciform_lite import format_val, format_val_unc


def calc_track_stats(tracks: pd.DataFrame, n_frames: int) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(
            columns=[
                "start",
                "end",
                "track_len",
                "censored",
                "bg",
                "mass",
            ],
            index=pd.Index([], name="particle"),
        )
    if "extra_frame" in tracks:
        tracks = tracks[tracks["extra_frame"] == 0]

    frame_counts = tracks.groupby("particle")["frame"].aggregate(["min", "max"])
    frame_counts.columns = ["start", "end"]
    frame_counts["track_len"] = frame_counts["end"] - frame_counts["start"] + 1

    censored_start = (frame_counts["start"].to_numpy() <= 0).astype(int)
    censored_end = (frame_counts["end"].to_numpy() >= n_frames - 1).astype(int)
    frame_counts["censored"] = censored_start | (censored_end << 1)

    for key in ("mass", "bg"):
        if key in tracks:
            frame_counts[key] = tracks.groupby("particle")[key].mean()
        else:
            frame_counts[key] = np.nan
    return frame_counts


def apply_filters(
    track_stats: pd.DataFrame,
    columns: Iterable[Any] = ["filter_param", "filter_manual"],
) -> pd.DataFrame:
    mask = np.ones(len(track_stats), dtype=bool)
    for c in columns:
        if c not in track_stats:
            continue
        mask &= (track_stats[c] == 0).to_numpy()
    return track_stats[mask]


def concat_stats(track_stats, filter=True):
    ret = {}
    for intv, ts in track_stats.items():
        if isinstance(ts, pd.DataFrame):
            ret[intv] = ts
        else:
            cc = {}
            for k, t in ts.items():
                if isinstance(t, pd.DataFrame) and not t.empty:
                    cc[k] = t
            ret[intv] = pd.concat(cc, names=["file"])
    if filter:
        return {k: apply_filters(ts) for k, ts in ret.items()}
    return ret


def rec_interval_label(time_unit=None):
    if time_unit is None:
        return r"recording interval $\Delta t$"
    return rf"recording interval $\Delta t$ [{time_unit}]"


def app_lifetime_label(time_unit=None):
    if time_unit is None:
        return r"apparent lifetime $\tau_\text{app}$"
    return rf"apparent lifetime $\tau_\text{{app}}$ [{time_unit}]"


LifetimeResult = namedtuple(
    "LifetimeResult", ["lifetime", "bleach", "lifetime_err", "bleach_err"]
)


class LifetimeAnalyzer:
    track_stats: (
        Mapping[Any, pd.DataFrame] | Mapping[Any, Mapping[Any, pd.DataFrame]] | None
    )
    """Maps recording interval -> track stats or recording interval -> file id -> track
    stats.
    Track stats are dataFrames with information about one track per line. Index is the
    track id. Other columns are "track_len": number of frames (first to last, including
    possible missing frames); "censored": 0 if not censored, 1 if left-censored, 2 if
    right-censored, 3 if both.
    """
    apparent_lifetimes: Optional[pd.DataFrame]
    """Information about apparent lifetimes, one line for each recording interval.
    Columns: "interval", "lifetime_app", "lifetime_app_err", "track_count".
    """
    lifetime: Optional[LifetimeResult]
    """Result of fitting :py:meth:`lifetime_model` to :py:attr:`apparent_lifetimes`"""

    def __init__(
        self,
        track_stats: (
            Mapping[Any, pd.DataFrame] | Mapping[Any, Mapping[Any, pd.DataFrame]] | None
        ),
        min_track_length=2,
        min_track_count=10,
        max_init_bleach=1e3,
        max_init_lifetime=1e7,
    ):
        """Parameters
        ----------
        track_stats
            Maps measurement interval -> track stats or interval -> file id -> track
            stats
        """
        self.min_track_length = min_track_length
        self.min_track_count = min_track_count
        self.max_init_bleach = max_init_bleach
        self.max_init_lifetime = max_init_lifetime
        self.track_stats = track_stats
        self.apparent_lifetimes = None
        self.lifetime = None
        self.bootstrap_n_outliers = 0

    def get_apparent_lifetime(
        self, track_lengths: pd.DataFrame, interval: float
    ) -> Tuple[float, float]:
        track_lengths = apply_filters(track_lengths)
        count = track_lengths["track_len"].to_numpy()
        cens = track_lengths["censored"].to_numpy()

        min_mask = count >= self.min_track_length
        count_min = count[min_mask]
        cens_min = cens[min_mask]

        with warnings.catch_warnings(record=True) as cw:
            warnings.filterwarnings(
                "always",
                "has negative values or NaNs",
                lifelines.exceptions.StatisticalWarning,
            )
            try:
                fit_res = lifelines.ExponentialFitter().fit_interval_censoring(
                    count_min - 1,
                    np.where(cens_min & 2, np.inf, count_min),
                    entry=(
                        self.min_track_length - 1 if self.min_track_length > 1 else None
                    ),
                    # use naive result as initial guess
                    initial_point=np.array(
                        [count_min.mean() - self.min_track_length + 0.5]
                    ),
                )
            except Exception:
                return np.NaN, np.NaN, len(count_min)
        err = (
            np.sqrt(fit_res.variance_matrix_.to_numpy().item()) * interval
            if not cw
            else np.NaN
        )
        return fit_res.lambda_ * interval, err, len(count_min)

    def get_apparent_lifetime_basic(
        self, track_lengths: pd.DataFrame, interval: float
    ) -> Tuple[float, float]:
        track_lengths = apply_filters(track_lengths)
        count = track_lengths["track_len"].to_numpy()
        min_mask = count >= self.min_track_length
        count_min = count[min_mask]

        return (
            (count_min.mean() - self.min_track_length + 0.5) * interval,
            count_min.std(ddof=1) / np.sqrt(len(count_min)) * interval,
            len(count_min),
        )

    def calc_apparent_lifetimes(self, method="survival"):
        if method == "survival":
            method = self.get_apparent_lifetime
        elif method == "basic":
            method = self.get_apparent_lifetime_basic
        else:
            raise ValueError('method needs to be "survival" or "basic"')

        app_lt = []
        # filtering is done in `get_apparent_lifetime*` methods
        track_stats = concat_stats(self.track_stats, filter=False)
        for intv, ts in track_stats.items():
            intv = float(intv)
            app_lt.append((intv, *method(ts, intv)))
        self.apparent_lifetimes = pd.DataFrame(
            app_lt,
            columns=["interval", "lifetime_app", "lifetime_app_err", "track_count"],
        ).sort_values("interval", ignore_index=True)

    @staticmethod
    def lifetime_model(interval, t_on, c_bleach):
        return 1 / (1 / t_on + 1 / (c_bleach * interval))

    def calc_lifetime(self):
        if self.apparent_lifetimes is None:
            self.calc_apparent_lifetimes()
        apparent = self.prepare_apparent_lifetimes()
        intervals = apparent["interval"].to_numpy()
        app_lt = apparent["lifetime_app"].to_numpy()
        errors = (
            apparent["lifetime_app_err"] if "lifetime_app_err" in apparent else None
        )

        # initial guesses
        k_bleach_init, k_off_init = np.polyfit(1 / intervals, 1 / app_lt, 1)
        # polyfit can yield negative values
        k_off_init = max(k_off_init, 1 / self.max_init_lifetime)
        k_bleach_init = max(k_bleach_init, 1 / self.max_init_bleach)

        try:
            with warnings.catch_warnings():
                # filter this warning, check for finite (and positive) values instead
                warnings.filterwarnings(
                    "ignore",
                    "Covariance.+could not be estimated",
                    scipy.optimize.OptimizeWarning,
                )
                fit, cov = scipy.optimize.curve_fit(
                    self.lifetime_model,
                    intervals,
                    app_lt,
                    sigma=errors,
                    absolute_sigma=errors is not None,
                    p0=[1 / k_off_init, 1 / k_bleach_init],
                    # do not set bounds as this can make it harder to spot invalid fits
                    # bounds=(0, np.inf),
                )
            self.lifetime = LifetimeResult(*fit, *np.sqrt(np.diag(cov)))
        except (RuntimeError, TypeError):
            # RuntimeError: fit did not converge
            # TypeError: fewer datapoints than fit parameters
            self.lifetime = LifetimeResult(np.NaN, np.NaN, np.NaN, np.NaN)

    def calc_lifetime_bootstrap(self, n_boot, rng=None):
        if rng is None or isinstance(rng, int):
            rng = np.random.default_rng(rng)

        # filter before resampling
        track_stats = {
            intv: t[t["track_len"] >= self.min_track_length]
            for intv, t in concat_stats(self.track_stats).items()
        }
        blt = []
        for _ in range(n_boot):
            ana = copy.copy(self)
            tstats_samp = {
                intv: ts.sample(
                    frac=1.0, replace=True, ignore_index=True, random_state=rng
                )
                for intv, ts in track_stats.items()
            }
            ana.track_stats = tstats_samp
            ana.calc_apparent_lifetimes()
            ana.calc_lifetime()
            blt.append(ana)

        alt = np.array([b.apparent_lifetimes["lifetime_app"].to_numpy() for b in blt])
        self.apparent_lifetimes = pd.DataFrame(
            {
                "interval": blt[0].apparent_lifetimes["interval"].to_numpy(),
                "lifetime_app": alt.mean(axis=0),
                "lifetime_app_err": alt.std(axis=0, ddof=1),
                "track_count": blt[0].apparent_lifetimes["track_count"].to_numpy(),
            }
        )
        lt = np.array([(b.lifetime.lifetime, b.lifetime.bleach) for b in blt])

        # remove outliers
        low_pct, high_pct = np.nanquantile(lt, [0.25, 0.75])
        iqr = high_pct - low_pct
        is_not_outlier = (lt[:, 0] > 0) & (lt[:, 0] < high_pct + 20 * iqr)
        lt = lt[is_not_outlier, :]

        self.lifetime = LifetimeResult(
            lt[:, 0].mean(),
            lt[:, 1].mean(),
            lt[:, 0].std(ddof=1),
            lt[:, 1].std(ddof=1),
        )
        self.bootstrap_n_outliers = len(is_not_outlier) - is_not_outlier.sum()

    def prepare_apparent_lifetimes(self) -> pd.DataFrame:
        apparent = self.apparent_lifetimes
        valid = np.isfinite(apparent["lifetime_app"])
        if "lifetime_app_err" in apparent:
            valid &= np.isfinite(apparent["lifetime_app_err"])
        if "track_count" in apparent:
            valid &= apparent["track_count"] >= self.min_track_count

        return apparent[valid].copy()

    def get_censor_stats(self) -> pd.DataFrame:
        tstats = {
            intv: t[t["track_len"] >= self.min_track_length]
            for intv, t in concat_stats(self.track_stats).items()
        }
        return pd.DataFrame(
            [np.bincount(t["censored"], minlength=4) for t in tstats.values()],
            index=[float(intv) for intv in tstats.keys()],
        ).sort_index()

    def plot(
        self,
        ax: mpl.axes.Axes,
        label: bool | str = True,
        time_unit: str | None = None,
        halflife: bool = False,
        point_kwargs: Mapping = {},
        line_kwargs: Mapping = {},
    ):
        apparent = self.prepare_apparent_lifetimes()
        fit = self.lifetime
        intervals = apparent["interval"].to_numpy()
        err = apparent["lifetime_app_err"] if "lifetime_app_err" in apparent else None

        eb = ax.errorbar(
            intervals,
            apparent["lifetime_app"],
            yerr=err,
            **{"linestyle": "none", "marker": ".", **point_kwargs},
        )
        curve_x = np.linspace(intervals[0], intervals[-1], 100)
        curve_y = self.lifetime_model(curve_x, fit.lifetime, fit.bleach)
        color = eb.lines[0].get_color()

        mul = math.log(2) if halflife else 1
        subscr = r"\frac{1}{2}" if halflife else r"\mathrm{lt}"
        if label:
            if fit.lifetime_err is None:
                val = format_val(fit.lifetime * mul, 2)
                if time_unit is None:
                    lab_res = f"$\\tau_{subscr} = {val}$"
                else:
                    lab_res = f"$\\tau_{subscr} = {val} \\mathrm{{{time_unit}}}$"
            else:
                val = format_val_unc(
                    fit.lifetime * mul, fit.lifetime_err * mul, 2, True
                )
                if time_unit is None:
                    lab_res = f"$\\tau_{subscr} = {val}$"
                else:
                    lab_res = f"$\\tau_{subscr} = ({val}) \\mathrm{{{time_unit}}}$"
            if isinstance(label, bool):
                lab = lab_res
            else:
                lab = f"{label}\n{lab_res}"
        else:
            lab = None

        ax.plot(
            curve_x,
            curve_y,
            color=color,
            label=lab,
            **line_kwargs,
        )

        if fit.lifetime_err is not None or fit.bleach_err is not None:
            lt_err = fit.lifetime_err or 0
            bl_err = fit.bleach_err or 0
            if lt_err >= fit.lifetime or bl_err >= fit.bleach:
                lower_y = np.zeros_like(curve_x)
            else:
                lower_y = self.lifetime_model(
                    curve_x,
                    fit.lifetime - lt_err,
                    fit.bleach - bl_err,
                )
            upper_y = self.lifetime_model(
                curve_x,
                fit.lifetime + lt_err,
                fit.bleach + bl_err,
            )
            ax.fill_between(curve_x, lower_y, upper_y, color=color, alpha=0.3)

        ax.set_xlabel(rec_interval_label(time_unit))
        ax.set_ylabel(app_lifetime_label(time_unit))

    def plot_censor_stats(self, ax: mpl.axes.Axes, time_unit: str | None = None):
        data = self.get_censor_stats()
        intervals = [str(i) for i in data.index]
        cens_names = {
            0: "fully within",
            1: "at start",
            2: "at end",
            3: "at start and end",
        }

        bottom = np.zeros(data.shape[0])
        for ct, d in enumerate(data.to_numpy().T):  # iterate over cens type
            ax.bar(intervals, d, bottom=bottom, label=cens_names[ct])
            bottom += d

        ax.set_xlabel(rec_interval_label(time_unit))
        ax.set_ylabel("average track count")

    @classmethod
    def load(cls, yaml_path, convert_interval=float, n_frames={}):
        from .io import load_data

        md, _, track_stats = load_data(yaml_path, convert_interval, n_frames=n_frames)
        kwargs = {}
        with suppress(KeyError):
            kwargs["min_track_length"] = md["filter_options"]["min_length"]
        with suppress(KeyError):
            kwargs["min_track_count"] = md["fit_options"]["min_count"]
        return cls(track_stats, **kwargs)
