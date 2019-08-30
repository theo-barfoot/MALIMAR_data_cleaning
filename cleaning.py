import os
import pandas as pd
import pydicom
import ast


class SliceMatchedVolumes:
    def __init__(self, series_paths, group_descriptions, series_descriptions,
                 series_numbers, uid_prefix='1.2.826.0.1.3680043.8.498.'):

        self.paths = series_paths
        self.group_descriptions = group_descriptions
        self.series_descriptions = series_descriptions
        self.series_numbers = series_numbers
        self.uid_prefix = uid_prefix

        self.fields = ['InstanceNumber', 'SliceLocation', 'SliceThickness', 'Rows', 'Columns',
                       'PixelSpacing', 'SeriesInstanceUID', 'SOPInstanceUID']

        self.df = pd.DataFrame()
        self.build_dcm_data_frames()

        self.num_slice_order_corrected = 0
        self.num_inplane_dim_mismatch = 0
        self.slice_matched = False
        self.is_clean = False

    def build_dcm_data_frames(self):
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
                df.sort_values(by=['SliceLocation'], inplace=True)
                self.df = self.df.append(df)

        self.df.set_index(['Sequence', 'Series'], inplace=True)
        self.df.sort_index()  # to prevent 'indexing past lexsort depth' warning
        print('List of Dataframes of DICOM headers constructed')

    def correct_slice_order(self):
        print('Checking DICOM slice order')
        for idx in self.df.index:  # level = [0,1] == ['Sequence','Series']
            if not self.df.loc[idx, 'InstanceNumber'].is_monotonic:
                print('Correcting', idx, 'slice order and rewriting DICOM header')
                self.df.loc[idx, 'InstanceNumber'] = range(1, len(self.df.loc[idx, 'InstanceNumber']) + 1)
                self.num_slice_order_corrected += 1

# Things to check: in plane resolution, slice issues, fields of view,
    def correct_inplane_resolution(self):
        print('Checking in-plane resolution')
        for idx, df_select in self.df.groupby('Sequence'):
            if not df_select['Columns'].nunique() == 1 and df_select['Rows'].nunique() == 1:
                print(idx, 'in-plane resolution MISMATCH')
                self.num_inplane_dim_mismatch += 1
                # TODO: resample in plane resolution to mode resoltuion
            else:
                print(idx, 'in-plane resolution MATCH')

    def match_slice_locations(self):
        a = self.df.groupby(level=[0, 1])['SliceLocation']
        # Check all series have the same number of slices:
        if a.count().nunique() == 1:
            # Check for duplicate slices in each series:
            if all(a.count() == a.nunique()):  # or a.count().equals(a.nunique())
                # Check all slice locations are the same between series:
                match = []
                for i in range(len(a.unique()) - 1):
                    match.append((a.unique()[i + 1].round(2) == a.unique()[i].round(2)).all())
                if sum(match) == len(match):
                    print('All slice (location and number) are matched between series')
                    self.slice_matched = True

        # a.first()
        # a.last()  -- will check for first and last slice

    def rewrite_uids(self):
        # series UID, instance UID in df
        for idx in self.df.index:  # group by series effectively
            series_uid = pydicom.uid.generate_uid(prefix=self.uid_prefix)
            self.df.loc[idx, 'SeriesInstanceUID'] = series_uid
            #[x = pydicom.uid.generate_uid(prefix=self.uid_prefix) for x in self.df['SOPInstanceUID']]
            # need to figure out best way to iterate over df and change each value

    def edit_dicom(self):
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
            ds.save_as(slice_.Path)

    def generate(self):
        self.correct_inplane_resolution()
        self.match_slice_locations()
        self.rewrite_uids()
        self.edit_dicom()
        if self.num_inplane_dim_mismatch == 0 and self.slice_matched:
            self.is_clean = True
        # self.df.drop('SeriesInstanceUID', axis=1)
        # self.df.drop('SOPInstanceUID', axis=1)
        # self.df.to_excel('df.xlsx')
        self.df.to_csv('df.csv')
        return self.is_clean

# probably going to be best to write this so that it checks if the volume is clean and if not then you call
# the cleaning function, rather than having the two together
# may be better to not have it as multi index, but need to figure out how this works with: self.df.loc[idx, 'InstanceNumber'] = range(1, len(df_select)+1)








