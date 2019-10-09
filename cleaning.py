import os
import pandas as pd
import pydicom
import ast
import SimpleITK as sitk
import numpy as np
import time
import shutil


class SliceMatchedVolumes:
    def __init__(self, series_paths, group_descriptions, series_descriptions,
                 series_numbers, uid_prefix='1.2.826.0.1.3680043.8.498.'):

        self.paths = series_paths
        self.group_descriptions = group_descriptions
        self.series_descriptions = series_descriptions
        self.series_numbers = series_numbers
        self.uid_prefix = uid_prefix

        self.fields = ['SequenceName', 'InstanceNumber', 'SliceLocation', 'SliceThickness', 'Rows', 'Columns',
                       'PixelSpacing', 'ImagePositionPatient', 'SeriesInstanceUID', 'SOPInstanceUID']

        self.df = pd.DataFrame()
        self.build_dcm_data_frames()
        self.df.to_csv('df.csv')
        self.num_slice_order_corrected = 0
        self.num_inplane_dim_mismatch = 0
        self.num_non_contiguous = 0
        self.num_fov = 0
        self.num_cor = 0
        self.slice_matched = False
        self.is_clean = False

        self.image_volumes = []
        self.readers = []

    def build_dcm_data_frames(self):
        print('-- Building DICOM Dataframe --')
        for g, group in enumerate(self.paths):
            for i, path in enumerate(group):
                rows = []
                for dirName, subdirList, fileList in os.walk(path):
                    for filename in fileList:
                        if ".dcm" in filename.lower():
                            dict1 = {'Sequence': self.group_descriptions[g],
                                     'Series': self.series_descriptions[g][i],
                                     'SeriesNumber': self.series_numbers[g][i]}
                            dcm_path = os.path.join(dirName, filename)
                            dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                            for field in self.fields:
                                dict1.update({field: getattr(dcm, field)})
                            dict1.update({'Path': dcm_path})
                            rows.append(dict1)

                df = pd.DataFrame(rows, columns=dict1.keys())
                # Convert string (eg "['_', '_', '_']" to list of strings (eg ['_', '_', '_']):
                ##df['ImagePositionPatient'] = df['ImagePositionPatient'].apply(lambda x: ast.literal_eval(x))
                # Convert list of strings to list of floats (eg [ _ , _ , _ ]):
                df['ImagePositionPatient'] = df['ImagePositionPatient'].apply(lambda x: [float(elem) for elem in x])
                ##df['PixelSpacing'] = df['PixelSpacing'].apply(lambda x: ast.literal_eval(x))
                df['PixelSpacing'] = df['PixelSpacing'].apply(lambda x: [float(elem) for elem in x])
                self.df = self.df.append(df)

        self.df.set_index(['Sequence', 'Series', 'InstanceNumber'], drop=False, inplace=True)
        self.df.drop(['Sequence', 'Series'], axis=1, inplace=True)  # Keep InstanceNumber column
        self.df.rename_axis(index={'InstanceNumber': 'Slice'}, inplace=True)

        self.df.sort_index(inplace=True)  # to prevent 'indexing past lexsort depth' warning

        for idx, d in self.df.groupby(['Sequence', 'Series']):
            if d.SequenceName.nunique() != 1:
                print('Series containing multiple sequences found in: ', idx)
                seq = d.SequenceName.value_counts().idxmax()
                for i, row in self.df.loc[idx].iterrows():
                    if row['SequenceName'] != seq:
                        self.df.drop(idx + (i,), inplace=True)
                        print(row['SequenceName'], ' removed!')

        print('Dataframe of DICOM headers constructed')

    def correct_slice_order(self):
        print('-- Checking DICOM slice order --')
        self.df.sort_values(by=['Sequence', 'Series', 'SliceLocation'], ascending=False, inplace=True)
        for idx, df_select in self.df.groupby(['Sequence', 'Series']):  # level = [0,1] == ['Sequence','Series']
            if df_select['InstanceNumber'].is_monotonic:
                print(idx, 'Slice order correct')
            else:
                print('Correcting', idx, 'slice order')
                self.num_slice_order_corrected += 1
            self.df.loc[idx, 'InstanceNumber'] = range(1, len(df_select) + 1)

        self.df.reset_index(inplace=True)
        self.df.drop('Slice', axis=1, inplace=True)
        self.df.set_index(['Sequence', 'Series', 'InstanceNumber'], drop=False, inplace=True)
        self.df.drop(['Sequence', 'Series'], axis=1, inplace=True)
        self.df.rename_axis(index={'InstanceNumber': 'Slice'}, inplace=True)
        self.df.sort_index(inplace=True)  # Basically just resetting the slice index to match the new instance number

# Things to check: in plane resolution, slice issues, fields of view,
    def check_inplane_resolution(self):
        print('-- Checking in-plane resolution --')
        for idx, df_select in self.df.groupby('Sequence'):
            if df_select['Columns'].nunique() == 1 and df_select['Rows'].nunique() == 1:
                print(idx, 'in-plane resolution MATCH')
            else:
                print(idx, 'in-plane resolution MISMATCH')
                self.num_inplane_dim_mismatch += 1
                # TODO: resample in plane resolution to mode resoltuion

    def match_slice_locations(self):  # this needs changing
        print('-- Matching Slices between Series --')
        a = self.df.groupby(level=[0, 1])['SliceLocation']
        # Check all series have the same number of slices:
        if a.count().nunique() == 1:
            # Check all slice locations are the same between series:
            match = []
            for i in range(len(a.unique()) - 1):
                match.append((a.unique()[i + 1].round(2) == a.unique()[i].round(2)).all())
            if sum(match) == len(match):  # Need to look at what the above is actually doing
                print('All slice (location and number) are matched between series')
                self.slice_matched = True
            else:
                print('Slices are not matched between series!')
        else:
            print('Slices are not matched between series!')

    def check_slice_contiguity(self):
        print('-- Checking slice contiguity for all series --')
        for idx, df_select in self.df.groupby(['Sequence', 'Series']):

            if df_select['SliceThickness'].nunique() == 1:
                st = df_select['SliceThickness'].unique()[0]
            else:
                print('WARNING: Multi slcie thickness series!')
                st = df_select['SliceThickness'].mode()[0]

            diff = df_select['SliceLocation'].diff().round(2).abs()
            diff.dropna(inplace=True)
            vals = diff.unique()

            if all(elem == st for elem in vals):  # or: min_ == st and max_ == st:
                print(idx, 'all', len(df_select), 'slice are contiguous')
            else:
                self.num_non_contiguous += 1
                if any(elem == 0 for elem in vals):
                    num = diff[diff == 0].count()  # or counts[counts.index == 0][0]
                    print(idx, 'has', num, 'duplicated slices')
                if any(0 < elem < st for elem in vals):
                    num = pd.cut(diff, [0.01, st], right=False).count()
                    print(idx, 'has', num, 'overlapping slices')
                if any(elem > st for elem in vals):
                    num = diff[diff > st].count()
                    print(idx, 'has', num, 'underlapping slices',
                          'largest gap is {}mm'.format(diff.max()))

    def check_fov(self):
        print('-- Checking FOVs between all series --')
        ipp = self.df['ImagePositionPatient'].apply(lambda x: [round(elem, 2) for elem in x])
        ipp_g = ipp.groupby(['Sequence', 'Series'])
        mins = ipp_g.min().apply(lambda x: tuple(x))  # issue with this as sometimes the min isn't the min for all 3
        maxs = ipp_g.max().apply(lambda x: tuple(x))  # try implement method used in resample volumes
        # lists are not hashable as they are mutable, therefore .nunique() doesn't work unless a tuple
        if mins.nunique() == 1 and maxs.nunique() == 1:
            print('FOVs for all series equal')
            self.num_fov = 1
        else:
            self.num_fov = max(mins.nunique(), maxs.nunique())
            print('FOVs not equal:')
            print('Minimum pixel locations (mm):', '\n', mins)
            print('-------------------')
            print('Maximum pixel locations (mm):', '\n', maxs)

    def rewrite_uids(self):
        print('-- Editing UIDs --')
        # At the moment all UIDs are changed as code changes series number/description for all, but needs to be changed
        # at some point to allow optionally no series desc/num
        # Rewrite all Seires Instance UIDs:
        for idx, df_select in self.df.groupby(['Sequence', 'Series']):
            series_uid = pydicom.uid.generate_uid(prefix=self.uid_prefix)
            self.df.loc[idx, 'SeriesInstanceUID'] = series_uid

        # Rewrite all SOP Instance UIDs:
        self.df.SOPInstanceUID = self.df.SOPInstanceUID.apply(lambda x: pydicom.uid.generate_uid(prefix=self.uid_prefix))

        # # Equivalent but slower: - Probably very useful for pixel calculations to come
        # for idx, df_select in self.df.groupby(['Sequence', 'Series', 'Slice']):
        #     self.df.loc[idx, 'SOPInstanceUID'] = pydicom.uid.generate_uid(prefix=self.uid_prefix)

        #     self.df.at[idx, 'SOPInstanceUID'] = ...... is another, possibly better method.

    def edit_dicom(self):
        print('-- Rewriting DICOM files --')
        for slice_ in self.df.itertuples():
            ds = pydicom.dcmread(slice_.Path)
            ds.SeriesDescription = slice_.Index[1]
            ds.SeriesNumber = slice_.SeriesNumber
            for field in self.fields:
                try:
                    setattr(ds, field, getattr(slice_, field))
                except ValueError:
                    setattr(ds, field, ast.literal_eval(getattr(slice_, field)))
                    # Pixelspacing is stored in df as "['0.83984375', '0.83984375']"
                    # ast.literal_eval changes this back to ['0.83984375', '0.83984375']
                    # Not required anymore as done in dataframe construction - TODO: may still need to convert to floats
            ds.save_as(slice_.Path)

    def load_sitk_image_volumes(self):
        print('--- Loading Image Volumes in SimpleITK ---')
        for g, group in enumerate(self.paths):
            self.image_volumes.append([])
            self.readers.append([])
            for i, path in enumerate(group):
                for dirName, subdirList, fileList in os.walk(path):
                    verbose_path = list(set([dirName for filename in fileList if filename.lower().endswith('.dcm')]))
                    if len(verbose_path):  # this code is pretty gross but it works
                        print('"' + self.series_descriptions[g][i] + '"', 'image volume loaded')
                        reader = sitk.ImageSeriesReader()
                        dcm_names = reader.GetGDCMSeriesFileNames(verbose_path[0])
                        reader.SetFileNames(dcm_names)
                        reader.MetaDataDictionaryArrayUpdateOn()
                        reader.LoadPrivateTagsOn()
                        self.image_volumes[g].append(reader.Execute())
                        self.readers[g].append(reader)

    def reformat_to_axial(self):
        print('--- Checking for Coronal Image Volumes and Reformatting to Axial ---')
        for g, group in enumerate(self.image_volumes):
            for i, img in enumerate(group):
                if img.GetDirection() == (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0):
                    self.num_cor += 1
                    print('"' + self.series_descriptions[g][i] + '"', 'in Coronal Orientation')
                    spacing = (img.GetSpacing()[0], img.GetSpacing()[2], img.GetSpacing()[1])
                    size = (img.GetSize()[0], img.GetSize()[2], img.GetSize()[1])
                    direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
                    origin = (img.GetOrigin()[0], img.GetOrigin()[1],
                              img.GetOrigin()[2] - img.GetSpacing()[1] * img.GetSize()[1])

                    print('Reformatting "' + self.series_descriptions[g][i] + '"', 'to Axial Orientation')

                    resample = sitk.ResampleImageFilter()
                    resample.SetOutputSpacing(spacing)
                    resample.SetSize(size)
                    resample.SetOutputDirection(direction)
                    resample.SetOutputOrigin(origin)
                    resample.SetTransform(sitk.Transform())
                    resample.SetDefaultPixelValue(3)
                    resample.SetInterpolator(sitk.sitkLinear)

                    self.image_volumes[g][i] = resample.Execute(img)

                if img.GetDirection() == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
                    print('"' + self.series_descriptions[g][i] + '"', 'already in Axial Orientation')

    def resample_volumes(self):
        print('--- Resampling Image Volumes to match FOV and slice positions ---')

        # determine global variables
        imgs_flat = [img for group in self.image_volumes for img in group]  # flattens nested list
        origin = tuple(np.max([img.GetOrigin()[i] for img in imgs_flat]) for i in range(3))
        fov = tuple(np.min([img.GetSize()[i] * img.GetSpacing()[i] for img in imgs_flat]) for i in range(3))
        directions = [img.GetDirection() for img in imgs_flat]
        direction = max(set(directions), key=directions.count)

        imgs_new = []

        for g, group in enumerate(self.image_volumes):

            # determine group parameters:
            spacings = [img.GetSpacing() for img in group]
            ref_spacing = max(set(spacings), key=spacings.count)
            ref_size = tuple(int(round(fov / spacing, 0)) for fov, spacing in zip(fov, ref_spacing))

            resample = sitk.ResampleImageFilter()
            resample.SetOutputSpacing(ref_spacing)
            resample.SetSize(ref_size)
            resample.SetOutputDirection(direction)
            resample.SetOutputOrigin(origin)
            resample.SetTransform(sitk.Transform())
            resample.SetDefaultPixelValue(3)
            resample.SetInterpolator(sitk.sitkLinear)

            print('Resampling Image Volumes:')
            imgs_new.append([resample.Execute(img) for img in group])

            for i, img in enumerate(group):
                print('-------', self.series_descriptions[g][i], '-------')
                print('Origin:', img.GetOrigin(), '---->', origin)
                print('Direction:', img.GetDirection(), '---->', direction)
                print('Spacing:', img.GetSpacing(), '---->', ref_spacing)
                print('FOV:', tuple(sp * si for sp, si in zip(img.GetSpacing(), img.GetSize())),
                      '---->', fov)
                print('Size:', img.GetSize(), '---->', ref_size)

        self.image_volumes = imgs_new

    def write_sitk_image_volumes(self):
        print('--- Writing DICOM Series from SimpleITK ---')
        # shutil.rmtree('temp/dicoms_new', ignore_errors=True)
        os.mkdir('temp/dicoms_new')
        for g, group in enumerate(self.image_volumes):
            for i, img in enumerate(group):
                reader = self.readers[g][i]
                series_description = self.series_descriptions[g][i]
                series_number = self.series_numbers[g][i]

                os.mkdir(os.path.join('temp/dicoms_new/', series_description))

                writer = sitk.ImageFileWriter()
                writer.KeepOriginalImageUIDOn()

                tags_to_copy = ["0010|0010",  # Patient Name
                                "0010|0020",  # Patient ID
                                "0010|0030",  # Patient Birth Date
                                "0010|0040",  # Patient Sex
                                "0010|4000",  # Patient Comments
                                "0020|000d",  # Study Instance UID, for machine consumption
                                "0020|0010",  # Study ID, for human consumption
                                "0008|0020",  # Study Date
                                "0008|0030",  # Study Time
                                "0008|0050",  # Accession Number
                                "0008|0060",  # Modality
                                "0018|5100"  # Patient Position
                                ]  # in theory you don't need to repeat most info (patient and series) for each series

                modification_time = time.strftime("%H%M%S")
                modification_date = time.strftime("%Y%m%d")

                direction = img.GetDirection()
                slice_thickness = str(img.GetSpacing()[2])

                series_tag_values = [(k, reader.GetMetaData(0, k)) for k in tags_to_copy if
                                     reader.HasMetaDataKey(0, k)] + \
                                    [("0008|0031", modification_time),  # Series Time
                                     ("0008|0021", modification_date),  # Series Date
                                     ("0020|0037", '\\'.join(map(str, (
                                     direction[0], direction[3], direction[6],  # Image Orientation (Patient)
                                     direction[1], direction[4], direction[7])))),
                                     ("0008|103e", series_description),  # Series Description
                                     ('0020|0011', str(series_number)),  # Series Number
                                     ("0008|0008", "DERIVED\\SECONDARY"),  # Image Type
                                     ("0018|0050", slice_thickness),  # Slice Thickness
                                     ("0018|0088", slice_thickness),  # Spacing Between Slices
                                     ("0020|000e", pydicom.uid.generate_uid(prefix=self.uid_prefix))
                                     # Series Instance UID
                                     ]
                for i in range(img.GetDepth()):
                    image_slice = img[:, :, i]
                    # Tags shared by the series.
                    for tag, value in series_tag_values:
                        # print(tag)
                        image_slice.SetMetaData(tag, value)

                    j = img.GetDepth() - i
                    # Slice specific tags.
                    image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d"))  # Instance Creation Date
                    image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S"))  # Instance Creation Time
                    image_slice.SetMetaData("0020|0032", '\\'.join(
                        map(str, img.TransformIndexToPhysicalPoint((0, 0, i)))))  # Image Position (Patient)
                    image_slice.SetMetaData("0020|0013", str(j))  # Instance Number
                    image_slice.SetMetaData("0008|0018", pydicom.uid.generate_uid(prefix=self.uid_prefix))

                    # Write to the output directory and add the extension dcm, to force writing in DICOM format.

                    writer.SetFileName(os.path.join('temp/dicoms_new', series_description, str(j) + '.dcm'))
                    writer.Execute(image_slice)
                print('"' + series_description + '"', 'image volume saved')
        shutil.rmtree('temp/dicoms', ignore_errors=True)
        os.rename('temp/dicoms_new', 'temp/dicoms')

    def correct_slice_contiguity(self):
        print('--- Correcting Slice Contiguity ---')
        # st = 5  # NOT TRUE for soem old area diffusions
        # This code has become a real mess and needs reworking....

        for idx, df_select in self.df.groupby(['Sequence', 'Series']):
            self.df.loc[idx, 'diff_down'] = df_select['SliceLocation'].diff().abs().round(2)
            print(idx, ' - Removed', len(self.df.loc[idx][self.df.loc[idx, 'diff_down'] == 0]), 'duplicates')
        self.df = self.df[self.df['diff_down'] != 0]  # drop duplicate rows

        for idx, df_select in self.df.groupby(['Sequence', 'Series']):
            self.df.loc[idx, 'diff_up'] = df_select['SliceLocation'].diff(-1).abs().round(2)

        # Calculate largest contiguous group and determine new slice locations:

        for idx, d in self.df.groupby(['Sequence', 'Series']):
            st = self.df.loc[idx + (1,), 'SliceThickness']
            print(idx, 'Loading Pixel Array Data')
            self.df.loc[idx, 'PixelArray'] = d.Path.apply(lambda x: pydicom.dcmread(x).pixel_array)

            diff = d['SliceLocation'].diff().round(2).abs()
            diff.dropna(inplace=True)
            vals = diff.unique()  # copied from above as it just works -- but is the same as using ['diff_down']

            if not all(elem == st for elem in vals):
                # first non-contiguous slice at beginning of largest contiguous group
                d['diff_up'].to_csv('test.csv')
                if d[d['diff_down'] != st]['diff_down'].count() == 1:
                    sl_ref = np.arange(self.df.loc[idx, 'SliceLocation'].max(),
                                       self.df.loc[idx, 'SliceLocation'].min(), -st)
                else:
                    start = d[d['diff_up'] != st].dropna()['InstanceNumber'].diff(-1).idxmin()[2]
                    # first non-contiguous slice at end of largest contiguous group
                    end = d[d['diff_down'] != st].dropna()['InstanceNumber'].diff().idxmax()[2]
                    for i in range(start + 1, end):
                        self.df.loc[idx + (i,), 'Contiguous'] = 'yes'
                    # df.loc[idx + (range(start+1, end),), 'Contiguous'] = 'yes' -- NO IDEA WHY THIS DOESN'T WORK
                    sl_ref_up = np.arange(self.df.loc[idx + (start + 1,)].SliceLocation + st,
                                          self.df.loc[idx, 'SliceLocation'].max(), st)  # new slice locations
                    sl_ref_down = np.arange(self.df.loc[idx + (end - 1,)].SliceLocation - st,
                                            self.df.loc[idx, 'SliceLocation'].min(), -st)  # new slice locations
                    sl_ref = np.concatenate((sl_ref_down, sl_ref_up))

                s_template = pd.DataFrame.copy(self.df.loc[idx + (1,)])
                shape = self.df.loc[idx + (1,), 'PixelArray'].shape
                s_template.PixelArray = np.ones(shape) * -1  # array is initialised with -1's
                s_template.Path = 'no path'
                print(idx, 'Calculating New Slice Locations')
                for i, sl in enumerate(sl_ref):
                    s_new = pd.DataFrame.copy(s_template)
                    s_new.SliceLocation = sl
                    try:
                        ipp_new = ast.literal_eval(s_new.ImagePositionPatient)
                    except ValueError:
                        ipp_new = s_new.ImagePositionPatient
                    ipp_new[2] = sl
                    s_new.ImagePositionPatient = ipp_new
                    s_new.Contiguous = 'yes'
                    self.df.loc[idx + (i + len(d) + 50,)] = s_new
                    # was having issues with slice overwriting so I just made the index gap big (50)
            elif all(elem == st for elem in vals):
                self.df.loc[idx, 'Contiguous'] = 'yes'

        self.correct_slice_order()

        for idx, d in self.df.groupby(['Sequence', 'Series']):
            # st = self.df.loc[idx + (1,), 'SliceThickness']
            if not all(c == 'yes' for c in self.df.loc[idx, 'Contiguous']):
                print(idx, 'Interpolating new slices')
                shape = self.df.loc[idx + (1,), 'PixelArray'].shape
                for i in range(1, len(self.df.loc[idx])):
                    if np.all(self.df.loc[idx + (i,), 'PixelArray'] == -1):
                        i_prev = i - 1
                        i_next = i + 1
                        while np.all(self.df.loc[idx + (i_prev,), 'PixelArray'] == -1): i_prev -= 1
                        while np.all(self.df.loc[idx + (i_next,), 'PixelArray'] == -1): i_next += 1
                        # Slice Locations:
                        sl_prev = self.df.loc[idx + (i_prev,), 'SliceLocation']
                        sl = self.df.loc[idx + (i,), 'SliceLocation']
                        sl_next = self.df.loc[idx + (i_next,), 'SliceLocation']
                        # Pixel Arrays:
                        pa_prev = self.df.loc[idx + (i_prev,), 'PixelArray'].reshape(shape)
                        pa_next = self.df.loc[idx + (i_next,), 'PixelArray'].reshape(shape)
                        # for some bizarre reason the calculated 2d array is 1d (flat) in the df
                        x1 = abs(sl - sl_prev)
                        x2 = abs(sl_next - sl)
                        r1 = (x1 / (x1 + x2))
                        r2 = (x2 / (x1 + x2))
                        pa_new = r1 * pa_prev + r2 * pa_next
                        self.df.loc[idx + (i,), 'PixelArray'] = pa_new

        self.df = self.df[self.df['Contiguous'] == 'yes']
        self.correct_slice_order()
        self.df.dropna(subset=['PixelArray'], inplace=True)  # this should not be required.... something wrong
        # also not sure what effect this will have on series which don't have contiguity issues
        # could either fix this or just re-create the dicom dataframe

    def df_to_sitk_image_volumes(self):
        print('--- Loading Image Volumes in SimpleITK ---')
        # st = 5
        for g, group in enumerate(self.series_descriptions):
            self.image_volumes.append([])
            self.readers.append([])
            for s, series in enumerate(group):
                idx = self.group_descriptions[g], series
                st = self.df.loc[idx].iloc[0]['SliceThickness']
                print('"' + self.series_descriptions[g][s] + '"', 'image volume loaded')
                shape = self.df.loc[self.group_descriptions[g], series, 1][['Rows', 'Columns']].to_list()
                shape = list(map(int, shape))
                volume = self.df.loc[self.group_descriptions[g], series]['PixelArray'].values
                volume = np.array([array.reshape(shape) for array in volume])
                volume = np.flip(volume, 0)
                volume = volume.astype(np.int16)
                img = sitk.GetImageFromArray(volume)
                try:
                    PixelSpacing = ast.literal_eval(self.df.loc[self.group_descriptions[g], series, 1]['PixelSpacing'])
                except ValueError:
                    PixelSpacing = self.df.loc[self.group_descriptions[g], series, 1]['PixelSpacing']
                PixelSpacing.append(st)
                img.SetSpacing(PixelSpacing)
                try:
                    Origin = ast.literal_eval(self.df.loc[self.group_descriptions[g], series].iloc[-1]['ImagePositionPatient'])
                except ValueError:
                    Origin = self.df.loc[self.group_descriptions[g], series].iloc[-1]['ImagePositionPatient']
                img.SetOrigin(Origin)
                self.image_volumes[g].append(img)

                a = []
                path = self.paths[g][s]
                for dirName, subdirList, fileList in os.walk(path):
                    for filename in fileList:
                        if ".dcm" in filename.lower():
                            a.append(os.path.join(dirName, filename))
                            template_dcm_paths = a[:2]

                # template_dcm_paths = list(self.df.loc[idx][self.df.loc[idx, 'Path'] != 'no path'].iloc[:2].Path)
                reader = sitk.ImageSeriesReader()
                reader.SetFileNames(list(template_dcm_paths))
                reader.MetaDataDictionaryArrayUpdateOn()
                reader.LoadPrivateTagsOn()
                _ = reader.Execute()
                self.readers[g].append(reader)

    def generate(self):
        self.correct_slice_order()
        self.df.to_csv('df.csv')
        self.check_inplane_resolution()
        self.match_slice_locations()
        self.check_slice_contiguity()
        self.check_fov()
        if (self.num_inplane_dim_mismatch == 0 and self.num_non_contiguous == 0 and self.num_fov == 1
                and self.slice_matched):
            self.is_clean = True
            self.rewrite_uids()
            self.edit_dicom()

        elif ((self.num_inplane_dim_mismatch > 0 or self.num_fov > 1 or not self.slice_matched)
              and self.num_non_contiguous == 0):
            self.load_sitk_image_volumes()
            self.reformat_to_axial()
            self.resample_volumes()
            self.write_sitk_image_volumes()
            self.is_clean = True

        elif self.num_non_contiguous > 0:
            self.correct_slice_contiguity()
            self.df_to_sitk_image_volumes()
            self.resample_volumes()
            self.write_sitk_image_volumes()
            self.is_clean = True



# probably going to be best to write this so that it checks if the volume is clean and if not then you call
# the cleaning function, rather than having the two together
# may be better to not have it as multi index, but need to figure out how this works with: self.df.loc[idx, 'InstanceNumber'] = range(1, len(df_select)+1)








