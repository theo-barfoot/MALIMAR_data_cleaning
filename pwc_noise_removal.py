import math
import numpy as np
from more_itertools import run_length


def rolling_median(x, k=15, padding=False):
    xm = [np.median(x[i:i + k]) for i in range(len(x) - k + 1)]  # rolling median of kernel length k
    pad_len = math.floor(k / 2)
    if padding:
        xm = ([xm[0]] * pad_len) + xm + ([xm[-1]] * (k - pad_len - 1))  # pad with end values
    else:
        xm = ([np.nan] * pad_len) + xm + ([np.nan] * (k - pad_len - 1))  # pad with nans
    return xm


def fit_steps(x: list, k: int = 15, threshold=98, min_step_length=0):
    """Remove noise from a piecewise constant (PWC) signal"""
    # inspired by: https://stats.stackexchange.com/questions/377310/how-to-fit-a-robust-step-function-to-a-time-series
    # 1. Smooth signal with rolling median
    xm = rolling_median(x, k)
    # 2. Calculate threshold for steps
    diffs = abs(np.diff(xm))
    threshold = np.nanpercentile(diffs, threshold)
    # 3. Find step locations using threshold
    steps = np.nan_to_num(diffs) > threshold
    step_locs = np.nonzero(steps)[0] + 1
    step_locs = np.concatenate([[0], step_locs, [len(x)]])
    # 4. remove steps that are closer than min-step length:
    step_locs = [step_locs[i-1] for i in range(1, len(step_locs)) if step_locs[i] - step_locs[i-1] >= min_step_length]
    step_locs = np.concatenate([step_locs,[len(x)]])
    # 5. Find medians between steps
    step_medians = [np.median(x[step_locs[i-1]:step_locs[i]]) for i in range(1, len(step_locs))]
    # 6. Recreate signal
    step_lengths = list(np.diff(step_locs))
    xms = list(run_length.decode((zip(step_medians, step_lengths))))
    return xms