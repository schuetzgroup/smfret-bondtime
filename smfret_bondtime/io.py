import contextlib
from decimal import Decimal
from pathlib import Path

import pandas as pd

from sdt import io


special_keys = ["registration"]


def load_data(yaml_path, convert_interval=Decimal, special=False):
    from sdt import multicolor, roi  # noqa F401; needed to load YAML file

    yaml_path = Path(yaml_path)
    with yaml_path.open() as yf:
        yaml_data = io.yaml.safe_load(yf)

    version = yaml_data.get("file_version", 1)

    if version <= 2:
        md, tracks, track_stats = load_data_v2(yaml_path, special)
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


def load_data_v2(yaml_path, special=False):
    raise RuntimeError("v2 not yet fully implemented")

    yaml_path = Path(yaml_path)
    with yaml_path.open() as yf:
        yaml_data = io.yaml.safe_load(yf)

    yaml_data["data_dir"] = Path(yaml_data["data_dir"])
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
    if all_files:
        for interval, files in all_files.items():
            if isinstance(files, list):
                # older YAML files store list of file names
                all_files[interval] = {n: f for n, f in enumerate(files)}
        for files in all_files.values():
            for entry in files.values():
                for src, f in entry.items():
                    # Replace backslashes by forward slashes
                    # On Windows and sdt-python <= 17.4 paths were saved
                    # with backslashes
                    f = f.replace("\\", "/")
                    entry[src] = (yaml_data["data_dir"] / f).as_posix()

        if not special:
            for k in special_keys:
                all_files.pop(k, None)

        yaml_data["files"] = all_files

    h5_path = yaml_path.with_suffix(".h5")
    tracks = {}
    if h5_path.exists():
        with pd.HDFStore(h5_path, "r") as s:
            for interval, dset in yaml_data["files"].items():
                tracks[interval] = {}
                for dkey, dfiles in dset.items():
                    # new files use the file ID as key
                    possible_h5_keys = [dkey]
                    try:
                        # old files use the file name as key
                        dpath = Path(dfiles["source_0"]).relative_to(
                            yaml_data["data_dir"]
                        )
                        # try with forward slashes
                        dpath = dpath.as_posix()
                        possible_h5_keys.append(dpath)
                        # try with backward slashes (sdt-python <= 17.4)
                        dpath_bs = dpath.replace("/", "\\")
                        possible_h5_keys.append(dpath_bs)
                    except Exception:
                        pass

                    for k in possible_h5_keys:
                        try:
                            tracks[interval][dkey] = s.get(f"/{interval}/{k}")
                        except KeyError:
                            pass
                        else:
                            break

    return yaml_data, tracks


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
                tracks[interval] = {}
                track_stats[interval] = {}
                for dkey, dfiles in dset.items():
                    with contextlib.suppress(KeyError):
                        tracks[interval][dkey] = s.get(f"/{interval}/{dkey}/loc")
                    with contextlib.suppress(KeyError):
                        track_stats[interval][dkey] = s.get(
                            f"/{interval}/{dkey}/track_stats"
                        )


    return yaml_data, tracks, track_stats
