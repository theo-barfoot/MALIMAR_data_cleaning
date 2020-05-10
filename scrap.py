import SimpleITK as sitk
import os
import pandas as pd
import numpy as np
import time
import sys
import pydicom
import shutil
import ast

def correct_slice_order(df):
    print('-- Checking DICOM slice order --')
    df.sort_values(by=['Sequence', 'Series', 'SliceLocation'], ascending=False, inplace=True)
    for idx, df_select in df.groupby(['Sequence', 'Series']):  # level = [0,1] == ['Sequence','Series']
        if df_select['InstanceNumber'].is_monotonic:
            print(idx, 'Slice order correct')
        else:
            print('Correcting', idx, 'slice order')
            df.loc[idx, 'InstanceNumber'] = range(1, len(df_select) + 1)

    df.reset_index(inplace=True)
    df.drop('Slice', axis=1, inplace=True)
    df.set_index(['Sequence', 'Series', 'InstanceNumber'], drop=False, inplace=True)
    df.drop(['Sequence', 'Series'], axis=1, inplace=True)
    df.rename_axis(index={'InstanceNumber': 'Slice'}, inplace=True)
    df.sort_index(inplace=True)  # Basica
    return df

df = pd.read_csv('df.csv')
df.drop('Slice', axis=1, inplace=True)  # for some reason df has a slice column, check in real code
df.set_index(['Sequence', 'Series', 'InstanceNumber'], drop=False, inplace=True)
df.drop(['Sequence', 'Series'], axis=1, inplace=True)  # Keep InstanceNumber column
df.rename_axis(index={'InstanceNumber': 'Slice'}, inplace=True)

st = 5

for idx, df_select in df.groupby(['Sequence', 'Series']):
    df.loc[idx, 'diff_down'] = df_select['SliceLocation'].diff().abs().round(2)
    # df.loc[idx][df.loc[idx,'diff_down'] == 0]['Path'].apply(lambda x: os.remove(x))  # remove duplicates
    print(idx, ' - Removed', len(df.loc[idx][df.loc[idx, 'diff_down'] == 0]), 'duplicates')
df = df[df['diff_down'] != 0]  # drop duplicate rows

for idx, df_select in df.groupby(['Sequence', 'Series']):
    df.loc[idx, 'diff_up'] = df_select['SliceLocation'].diff(-1).abs().round(2)

#####################

for idx, d in df.groupby(['Sequence', 'Series']):
    if not all(diff == st for diff in df.loc[idx, 'diff_down']):
        print(idx, 'Loading Pixel Array Data')
        df.loc[idx, 'PixelArray'] = d.Path.apply(lambda x: pydicom.dcmread(x).pixel_array)
        # df.loc[idx, 'Path'] = None ??  # Remove path -- also delete dcms?
        # first non-contiguous slice at beginnging of largest contiguous group
        start = d[d['diff_up'] != st].dropna()['InstanceNumber'].diff(-1).idxmin()[2]
        # first non-contiguous slice at end of largest contiguous group
        end = d[d['diff_down'] != st].dropna()['InstanceNumber'].diff().idxmax()[2]
        sl_ref_up = np.arange(df.loc[idx + (start + 1,)].SliceLocation + st,
                              df.loc[idx, 'SliceLocation'].max(), st)  # new slice locations
        sl_ref_down = np.arange(df.loc[idx + (end - 1,)].SliceLocation - st,
                                df.loc[idx, 'SliceLocation'].min(), -st)  # new slice locations
        s_template = pd.DataFrame.copy(df.loc[idx + (1,)])
        s_template.PixelArray = np.ones(df.loc[idx + (1,), 'PixelArray'].shape) * -1
        s_template.Path = ''
        for i, sl in enumerate(np.concatenate((sl_ref_down, sl_ref_up))):
            s_new = pd.DataFrame.copy(s_template)
            s_new.SliceLocation = sl
            ipp_new = ast.literal_eval(s_new.ImagePositionPatient)
            ipp_new[2] = sl
            s_new.ImagePositionPatient = ipp_new
            df.loc[idx + (i + len(d) + 50,)] = s_new
            # was having issues with slice overwriting so I just made the index gap big (50)

df = correct_slice_order(df)

for idx, d in df.groupby(['Sequence', 'Series']):
    if not all(diff == st for diff in df.loc[idx, 'diff_down']):
        print(idx, 'Interpolating new slices')
        for i in range(1, len(df.loc[idx])):
            print(idx, i)
            if np.all(df.loc[idx + (i,), 'PixelArray'] == -1):
                i_prev = i - 1
                i_next = i + 1
                while np.all(df.loc[idx + (i_prev,), 'PixelArray'] == -1): i_prev -= 1
                while np.all(df.loc[idx + (i_next,), 'PixelArray'] == -1): i_next += 1
                # Slice Locations:
                sl_prev = df.loc[idx + (i_prev,), 'SliceLocation']
                sl = df.loc[idx + (i,), 'SliceLocation']
                sl_next = df.loc[idx + (i_next,), 'SliceLocation']
                # Pixel Arrays:
                pa_prev = df.loc[idx + (i_prev,), 'PixelArray']
                pa_next = df.loc[idx + (i_next,), 'PixelArray']
                # pa_new = ((st - (sl-sl_prev))/st)*pa_prev + ((st - (sl_next-sl))/st)*pa_next
                x1 = abs(sl - sl_prev)
                x2 = abs(sl_next - sl)
                r1 = (x1 / (x1 + x2))
                r2 = (x2 / (x1 + x2))
                pa_new = r1 * pa_prev + r2 * pa_next
                # pa_new = np.add(np.multiply(r1,pa_prev), np.multiply(r2,pa_next))
                df.loc[idx + (i,), 'PixelArray'] = pa_new


