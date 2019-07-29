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
                for path in self.paths[sequence][series]:
                    rows = []
                    for dirName, subdirList, fileList in os.walk(path):
                        for filename in fileList:
                            if ".dcm" in filename.lower():
                                dict1 = {'Sequence': sequence, 'Series': series}
                                dcm_path = os.path.join(dirName, filename)
                                dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                                for field in fields:
                                    dict1.update({field: getattr(dcm, field)})
                                dict1.update({'path': dcm_path})
                                rows.append(dict1)
                df = pd.DataFrame(rows, columns=dict1.keys())
                df.sort_values(by=['SliceLocation'], inplace=True)
                self.dcm_header_df = self.dcm_header_df.append(df)

        print('List of Dataframes of DICOM headers constructed')
        # todo: make InstanceNumber index? Can I still check for monotonic and reset if neccessary

    def correct_slice_order(self):
        for group in self.dcm_header_df_list:
            for df in group:
                if not df['InstanceNumber'].is_monotonic:
                    df.reset_index(drop=True, inplace=True)
                    df['InstanceNumber'] = df.index + 1
                    [self.rewrite_instance_number(x, y) for x, y in zip(df['InstanceNumber'], df['path'])]
                    self.num_slice_order_corrected += 1
                    # todo: this needs changing to deal with new df structure

    def generate(self):
        #self.correct_inplane_resolution()
        #self.correct_slice_order()
        return self

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









