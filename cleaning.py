import os
import pandas as pd
import pydicom
import ast


class SliceMatchedVolumes:
    def __init__(self, local_paths_dict):

        self.paths = local_paths_dict
        self.dcm_header_df = pd.DataFrame()
        self.build_dcm_data_frames()

        self.num_slice_order_corrected = 0
        self.num_inplane_dim_mismatch = 0
        self.slice_matched = False
        self.is_clean = False

        self.fields = ['InstanceNumber', 'SliceLocation', 'SliceThickness', 'Rows', 'Columns', 'PixelSpacing',
                  'SeriesInstanceUID', 'SOPInstanceUID']

        # self.uid_prefix = Not sure how to set it to '1.2.826.0.1.3680043.8.498.' as default or argument if passed

    def build_dcm_data_frames(self):
        sn = 1  # New series number
        for sequence in self.paths:
            for series in self.paths[sequence]:
                for i, path in enumerate(self.paths[sequence][series]):
                    rows = []
                    for dirName, subdirList, fileList in os.walk(path):
                        for filename in fileList:
                            if ".dcm" in filename.lower():
                                dict1 = {'Sequence': sequence, 'Series': series, 'SeriesNumber': sn}
                                if i:
                                    dict1['Series'] = dict1['Series']+'_'+str(i+1)
                                dcm_path = os.path.join(dirName, filename)
                                dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                                for field in self.fields:
                                    dict1.update({field: getattr(dcm, field)})
                                dict1.update({'Path': dcm_path})
                                rows.append(dict1)

                    sn += 1
                    df = pd.DataFrame(rows, columns=dict1.keys())
                    df.sort_values(by=['SliceLocation'], inplace=True)
                    self.dcm_header_df = self.dcm_header_df.append(df)

        self.dcm_header_df.set_index(['Sequence', 'Series'], inplace=True)
        self.dcm_header_df.sort_index()  # to prevent 'indexing past lexsort depth' warning
        print('List of Dataframes of DICOM headers constructed')

    def correct_slice_order(self):
        print('Checking DICOM slice order')
        for idx, df_select in self.dcm_header_df.groupby(level=[0, 1]):  # level = [0,1] == ['Sequence','Series']
            if not df_select['InstanceNumber'].is_monotonic:
                print('Correcting', idx, 'slice order and rewriting DICOM header')
                self.dcm_header_df.loc[idx, 'InstanceNumber'] = range(1, len(df_select)+1)
                self.rewrite_instance_number(idx)
                self.num_slice_order_corrected += 1

    # This could of been written in many ways. Could of iterated through the dictionary, but groupby is more elegant
    # Could of changed the df_select values and used them as inputs for the rewrite_instance_number function

    def rewrite_instance_number(self, idx):
        for i, p in zip(self.dcm_header_df.loc[idx]['InstanceNumber'], self.dcm_header_df.loc[idx]['Path']):
            ds = pydicom.dcmread(p)
            ds.InstanceNumber = i
            ds.save_as(p) #######################


# Things to check: in plane resolution, slice issues, fields of view,
    def correct_inplane_resolution(self):
        print('Checking in-plane resolution')

        for idx, df_select in self.dcm_header_df.groupby('Sequence'):
            if not df_select['Columns'].nunique() == 1 and df_select['Rows'].nunique() == 1:
                print(idx, 'in-plane resolution MISMATCH')
                self.num_inplane_dim_mismatch += 1
                # TODO: resample in plane resolution to mode resoltuion
            else:
                print(idx, 'in-plane resolution MATCH')


    def match_slice_locations(self):
        a = self.dcm_header_df.groupby(level=[0, 1])['SliceLocation']
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

    def rewrite_series_info(self):
        # Rewrite series number, series description, series UID, instance UID
        prefix = '1.2.826.0.1.3680043.8.498.'
        for idx in self.dcm_header_df.index:  # group by series effectively
            series_uid = pydicom.uid.generate_uid(prefix=prefix)

        series_uid = pydicom.uid.generate_uid()  # should use icr unique prefix
        ds.SeriesInstanceUID = series_uid
        ds.SOPInstanceUID = pydicom.uid.generate_uid(prefix='1.2.826.0.1.534147.')  # ICR prefix - need to add as class argument
        pass

    def edit_dicom(self):
        for row in self.dcm_header_df.itertuples():
            ds = pydicom.dcmread(row.Path)
            ds.SeriesDescription = row.Index[1]
            for field in self.fields:
                try:
                    setattr(ds, field, getattr(row, field))
                except ValueError:
                    setattr(ds, field, ast.literal_eval(getattr(row, field)))
                    # Pixelspacing is stored in df as "['0.83984375', '0.83984375']"
                    # ast.literal_eval changes this back to ['0.83984375', '0.83984375']

    @staticmethod
    def rewrite_series_info_REMOVE(index, sn, path):
        ds = pydicom.dcmread(path)
        ds.SeriesDescription = index[1]
        ds.SeriesNumber = sn
        ds.save_as(path)

    def generate(self):
        # [self.rewrite_series_info(x, y, z) for x, y, z in zip(self.dcm_header_df.index,
        #                                                       self.dcm_header_df['SeriesNumber'],
        #                                                       self.dcm_header_df['Path'])]
        self.correct_slice_order()
        self.correct_inplane_resolution()
        self.match_slice_locations()
        self.rewrite_series_info()
        # self.rewrite seris info - including uids?
        # self.rewrite_uids
        if self.num_inplane_dim_mismatch == 0 and self.slice_matched:
            self.is_clean = True
        self.dcm_header_df.to_excel('df.xlsx')
        return self.is_clean

# probably going to be best to write this so that it checks if the volume is clean and if not then you call
# the cleaning function, rather than having the two together
# probably best to create rewrite dicom header function that just takes the columns as argments for the header elements
# and then writes the value in that row for the header element
# may be better to not have it as multi index, but need to figure out how this works with: self.dcm_header_df.loc[idx, 'InstanceNumber'] = range(1, len(df_select)+1)








