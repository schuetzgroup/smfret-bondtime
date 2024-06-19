import pandas as pd


def calc_track_stats(tracks: pd.DataFrame, n_frames: int) -> pd.DataFrame:
    if "extra_frame" in tracks:
        tracks = tracks[tracks["extra_frame"] == 0]

    frame_counts = tracks.groupby("particle")["frame"].aggregate(["min", "max"])
    frame_counts.columns = ["start", "end"]
    frame_counts["track_len"] = frame_counts["end"] - frame_counts["start"] + 1

    censored_start = (frame_counts["start"].to_numpy() <= 0).astype(int)
    censored_end = (frame_counts["end"].to_numpy() >= n_frames - 1).astype(int)
    frame_counts["censored"] = censored_start | (censored_end << 1)

    mean_vals = tracks.groupby("particle")[["bg", "mass"]].mean()

    ret = pd.concat([frame_counts, mean_vals], axis=1)

    return ret
