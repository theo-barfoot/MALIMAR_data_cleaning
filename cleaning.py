import os
import pandas as pd
import pydicom


class SliceMatchedVolumes:
    def __init__(self, local_paths_dict):

        self.paths = local_paths_dict
        self.dcm_header_df = pd.DataFrame()
        self.build_dcm_data_frames()

        self.num_slice_order_corrected = 0
        self.num_inplane_dim_mismatch = 0

    def build_dcm_data_frames(self):
        fields = ['InstanceNumber', 'SliceLocation', 'SliceThickness', 'Rows', 'Columns', 'PixelSpacing']
        for sequence in self.paths:
            for series in self.paths[sequence]:
                for i, path in enumerate(self.paths[sequence][series]):
                    rows = []
                    for dirName, subdirList, fileList in os.walk(path):
                        for filename in fileList:
                            if ".dcm" in filename.lower():
                                dict1 = {'Sequence': sequence, 'Series': series}
                                if i:
                                    dict1['Series'] = dict1['Series']+'_'+str(i+1)
                                dcm_path = os.path.join(dirName, filename)
                                dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                                for field in fields:
                                    dict1.update({field: getattr(dcm, field)})
                                dict1.update({'Path': dcm_path})
                                rows.append(dict1)

                    df = pd.DataFrame(rows, columns=dict1.keys())
                    df.sort_values(by=['SliceLocation'], inplace=True)
                    self.dcm_header_df = self.dcm_header_df.append(df)

        self.dcm_header_df.set_index(['Sequence','Series'], inplace=True)
        print('List of Dataframes of DICOM headers constructed')

    def correct_slice_order(self):
        print('Checking DICOM slice order')
        for idx, df_select in self.dcm_header_df.groupby(level=[0, 1]):  # level = [0,1] == ['Sequence','Series']
            if not df_select['InstanceNumber'].is_monotonic:
                print('Correcting', idx, 'slice order and rewriting DICOM header')
                self.dcm_header_df.loc[idx, 'InstanceNumber'] = range(1, len(df_select)+1)
                [self.rewrite_instance_number(x, y) for x, y in zip(self.dcm_header_df.loc[idx]['InstanceNumber'],
                                                                    self.dcm_header_df.loc[idx]['Path'])]
                self.num_slice_order_corrected += 1

    # This could of been written in many ways. Could of iterated through the dictionary, but groupby is more elegant
    # Could of changed the df_select values and used them as inputs for the rewrite_instance_number function

    @staticmethod
    def rewrite_instance_number(instance_number, path):
        ds = pydicom.dcmread(path)
        ds.InstanceNumber = instance_number
        ds.save_as(path)

# Things to check: in plane resolution, slice issues, fields of view,
    def correct_inplane_resolution(self):
        print('Checking in-plane resolution')
        rows = []
        cols = []
        for g, group in enumerate(self.dcm_header_df_list):
            rows.append([])
            cols.append([])
            for df in group:
                if df['Columns'].nunique() == 1 and df['Rows'].nunique() == 1:  # Check dimensions of same series are constant ( this should always be the case)
                    rows[g].append(df['Columns'].iloc[0])
                    cols[g].append(df['Rows'].iloc[0])
                else:
                    print('In-plane resolution differs inside volume!!')
            if not (rows[g].count(rows[g][0]) == len(rows[g])) and (cols[g].count(cols[g][0]) == len(cols[g])):   # Check rows and cols are same for series in same group
                # TODO: resample in plane resolution to mode resoltuion
                self.num_inplane_dim_mismatch += 1
                print('Uh oh in-plane res mismatch!')
            else:
                print('in-plane resolution match')

    def correct_fov(self):
        # Check that all slice locations of the same group are the same
        # Actully fov and slice issues are the same thing, just do it in slice
        pass

    def match_slice_locations(self):
        # for noew (getting avanto data moving) just check that all slice locations
        # and slice thicknesses are the same for all series across both groups
        # Also check that the slices are contiguous
        pass
        # Maybe start off by checking the length of each dataframe is the same

    def generate(self):
        #self.correct_inplane_resolution()
        self.correct_slice_order()
        return self









