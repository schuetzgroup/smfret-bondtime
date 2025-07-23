# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
#
# SPDX-License-Identifier: BSD-3-Clause

import collections
import contextlib
import copy
import math
import re
import warnings
from pathlib import Path
from typing import Any, Dict, Mapping

import pandas as pd
from sdt import io, multicolor

from .analysis import calc_track_stats

special_keys = ["registration"]


def save_data(
    yaml_path: str | Path,
    metadata: Dict[str, Any],
    loc_data: Mapping[Any, Mapping[Any, pd.DataFrame | None]],
    track_stats: Mapping[Any, Mapping[Any, pd.DataFrame | None]],
):
    """Save metadata, single-molecule localizations and track statistics

    Metadata is written to `yaml_path`, localizations and track stats are written
    to a HDF5 file of the same name, but with suffix ".h5". Within the HDF5 file, the
    `loc` and `track_stats` underneatch /<dataset id>/<file id>/ contain localization
    data and track stats, respectively.

    Parameters
    ----------
    yaml_path
        Path to file to save metadata in YAML format. Tracking data is saved in a
        HDF5 file of the same name, but with suffix ".h5".
    metadata
        Data to save into the YAML file. The key "file_version" is added to identify
        the save file version for loading.
    loc_data
        Mapping of experiment id -> file id -> single-molecule localization data
    tracks
        Mapping of experiment id -> file id -> track statistics (one track per line)
    """
    metadata = copy.deepcopy(metadata)
    metadata["file_version"] = 3
    # make paths relative to data_dir
    dd = Path(metadata["data_dir"])
    for dsets in metadata["files"].values():
        for src in dsets.values():
            new_src = {k: Path(v).relative_to(dd).as_posix() for k, v in src.items()}
            src.clear()
            src.update(new_src)

    yaml_path = Path(yaml_path)
    tmp_yaml_path = yaml_path.with_suffix(".tmp.yaml")
    h5_path = yaml_path.with_suffix(".h5")
    tmp_h5_path = yaml_path.with_suffix(".tmp.h5")

    try:
        with tmp_yaml_path.open("w") as yf:
            io.yaml.safe_dump(metadata, yf)

        import tables

        with pd.HDFStore(tmp_h5_path, "w") as s, warnings.catch_warnings():
            warnings.simplefilter("ignore", tables.NaturalNameWarning)
            for ekey, dset in loc_data.items():
                for dkey, ld in dset.items():
                    if isinstance(ld, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}/loc", ld)
                    else:
                        warnings.warn(
                            f"no localization data for dataset {ekey}, file {dkey}"
                        )
            for ekey, dset in track_stats.items():
                for dkey, ts in dset.items():
                    if isinstance(ts, pd.DataFrame):
                        s.put(f"/{ekey}/{dkey}/track_stats", ts)
                    else:
                        warnings.warn(
                            f"no track stats data for dataset {ekey}, file {dkey}"
                        )

        tmp_yaml_path.replace(yaml_path)
        tmp_h5_path.replace(h5_path)
    finally:
        tmp_yaml_path.unlink(missing_ok=True)
        tmp_h5_path.unlink(missing_ok=True)


def load_data(yaml_path, convert_interval=float, special=False, n_frames={}):
    from sdt import roi  # noqa F401; needed to load YAML file

    yaml_path = Path(yaml_path)
    with yaml_path.open() as yf:
        yaml_data = io.yaml.safe_load(yf)

    version = yaml_data.get("file_version", 1)

    if version <= 2:
        md, tracks, track_stats = load_data_v2(yaml_path, special, n_frames)
    elif version == 3:
        md, tracks, track_stats = load_data_v3(yaml_path, special)
    else:
        raise RuntimeError(f"save file version {version} not supported")

    # get absolute paths
    dd = Path(md["data_dir"])
    for files in md.get("files", {}).values():
        for entry in files.values():
            for src, f in entry.items():
                f = Path(f)
                if not f.is_absolute():
                    entry[src] = (dd / f).as_posix()

    # convert keys which are not special using `convert_interval`
    if callable(convert_interval):
        for k in list(md["files"].keys()):
            if k in special_keys:
                continue
            try:
                k_cvt = convert_interval(k)
            except ValueError:
                continue
            md["files"][k_cvt] = md["files"].pop(k)
            with contextlib.suppress(KeyError):
                tracks[k_cvt] = tracks.pop(k)
            with contextlib.suppress(KeyError):
                track_stats[k_cvt] = track_stats.pop(k)

    return md, tracks, track_stats


def load_data_v2(yaml_path, special=False, n_frames={}):
    yaml_path = Path(yaml_path)
    with yaml_path.open() as yf:
        yaml_data = io.yaml.safe_load(yf)

    if "channels" in yaml_data:
        ch = yaml_data["channels"]
        for v in ch.values():
            if "source" not in v:
                # sdt-python <= 17.4 YAML file
                v["source"] = f"source_{v.pop('source_id')}"
    if "track_options" in yaml_data:
        t = yaml_data["track_options"]
        t.setdefault("extra_frames", 0)  # sdt-python <= 17.4 YAML file
    if "registrator" in yaml_data:
        reg = yaml_data["registrator"]
        if set(reg.channel_names) != {"acceptor", "donor"}:
            reg.channel_names = ["acceptor", "donor"]

    # older YAML files store special dataset files under "special_files"
    all_files = {**yaml_data.pop("special_files", {}), **yaml_data.pop("files", {})}
    for interval, files in all_files.items():
        if isinstance(files, list):
            # older YAML files store list of file names
            all_files[interval] = {n: f for n, f in enumerate(files)}

    h5_path = yaml_path.with_suffix(".h5")
    tracks = {}
    if h5_path.exists():
        with pd.HDFStore(h5_path, "r") as s:
            for interval, dset in all_files.items():
                if interval in special_keys:
                    continue
                tracks[interval] = {}
                for dkey, dfiles in dset.items():
                    # new files use the file ID as key
                    # old files use the file name as key
                    possible_h5_keys = [dkey, dfiles["source_0"]]
                    for k in possible_h5_keys:
                        try:
                            tracks[interval][dkey] = s.get(f"/{interval}/{k}")
                        except KeyError:
                            pass
                        else:
                            break
                    else:
                        warnings.warn(
                            f"localization data not found for interval {dkey},"
                            f"file {dfiles['source_0']}"
                        )

    for files in all_files.values():
        for entry in files.values():
            for src, f in entry.items():
                # On Windows and sdt-python <= 17.4 paths were saved with backslashes
                entry[src] = f.replace("\\", "/")

    if not special:
        for k in special_keys:
            all_files.pop(k, None)

    yaml_data["files"] = all_files

    # calculate track stats
    if isinstance(n_frames, str):
        n_frames = re.compile(n_frames)
    elif isinstance(n_frames, collections.abc.Mapping):
        n_frames = {str(k): v for k, v in n_frames.items()}

    data_dir = Path(yaml_data["data_dir"])
    frame_sel = multicolor.FrameSelector(yaml_data["excitation_seq"])
    acc_src = yaml_data["channels"]["acceptor"]["source"]
    track_stats = {}
    for interval, trcs in tracks.items():
        if interval in special_keys:
            continue
        for did, t in trcs.items():
            if "particle" not in t:
                # file has not been tracked
                continue
            f = yaml_data["files"][interval][did][acc_src]
            try:
                with io.ImageSequence(data_dir / f) as ims:
                    nf = len(frame_sel.select(ims, "d"))
            except Exception:
                if isinstance(n_frames, re.Pattern):
                    try:
                        nf = int(n_frames.search(f).group(1))
                    except Exception:
                        nf = math.inf
                else:
                    nf = n_frames.get(interval, math.inf)
            if not math.isfinite(nf):
                warnings.warn(f"could not determine number of frames for {f}")
            s = calc_track_stats(t, nf)
            grp = t.groupby("particle")
            for col in "filter_param", "filter_manual":
                if col in t:
                    s[col] = grp[col].first()
                else:
                    s[col] = -1
            if "mass_seg" in t:
                s["changepoints"] = grp["mass_seg"].nunique() - 1
            track_stats.setdefault(interval, {})[did] = s

    return yaml_data, tracks, track_stats


def load_data_v3(yaml_path, special=False):
    yaml_path = Path(yaml_path)
    with yaml_path.open() as yf:
        yaml_data = io.yaml.safe_load(yf)

    if not special:
        for k in special_keys:
            yaml_data["files"].pop(k, None)

    h5_path = yaml_path.with_suffix(".h5")
    tracks = {}
    track_stats = {}
    if h5_path.exists():
        with pd.HDFStore(h5_path, "r") as s:
            for interval, dset in yaml_data["files"].items():
                if interval in special_keys:
                    continue
                tracks[interval] = {}
                track_stats[interval] = {}
                for dkey, dfiles in dset.items():
                    try:
                        tracks[interval][dkey] = s.get(f"/{interval}/{dkey}/loc")
                    except KeyError:
                        warnings.warn(
                            f"localization data not found for interval {dkey},"
                            f" file {dfiles.get('source_0', f'id {dkey}')}"
                        )
                    try:
                        track_stats[interval][dkey] = s.get(
                            f"/{interval}/{dkey}/track_stats"
                        )
                    except KeyError:
                        warnings.warn(
                            f"track statistics not found for interval {dkey},"
                            f" file {dfiles.get('source_0', f'id {dkey}')}"
                        )

    return yaml_data, tracks, track_stats
