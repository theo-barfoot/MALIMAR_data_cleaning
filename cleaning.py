import os
import pandas as pd
import pydicom


class SliceMatchedVolumes:
    def __init__(self, local_paths_list):

        self.paths = local_paths_list
        self.dcm_header_df_list = []
        self.build_dcm_data_frames()

        self.num_slice_order_corrected = 0
        self.num_inplane_dim_mismatch = 0

    def build_dcm_data_frames(self):
        fields = ['InstanceNumber', 'SliceLocation', 'SliceThickness', 'Rows', 'Columns', 'PixelSpacing']
        for g, group in enumerate(self.paths):
            self.dcm_header_df_list.append([])
            for path in group:
                rows = []
                for dirName, subdirList, fileList in os.walk(path):
                    for filename in fileList:
                        if ".dcm" in filename.lower():
                            dict1 = {}
                            dcm_path = os.path.join(dirName, filename)
                            dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                            for field in fields:
                                dict1.update({field: getattr(dcm, field)})
                            dict1.update({'path': dcm_path})
                            rows.append(dict1)
                self.dcm_header_df_list[g].append(pd.DataFrame(rows).sort_values(by=['SliceLocation']))

        print('List of Dataframes of DICOM headers constructed')

    def correct_slice_order(self):
        for group in self.dcm_header_df_list:
            for df in group:
                if not df['InstanceNumber'].is_monotonic:
                    df.reset_index(drop=True, inplace=True)
                    df['InstanceNumber'] = df.index + 1
                    [self.rewrite_instance_number(x, y) for x, y in zip(df['InstanceNumber'], df['path'])]
                    self.num_slice_order_corrected += 1

    def generate(self):
        self.correct_inplane_resolution()
        self.correct_slice_order()
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

        # Maybe start off by checking the length of each dataframe is the same








# class SliceMatchedVolumes:
#     def __init__(self, local_paths_dict):
#         self.local_paths_dict = local_paths_dict
#
#         self.local_dcms = {}
#
#     def build_dcm_data_frames(self):
#         fields = ['InstanceNumber', 'SliceLocation', 'Rows', 'Columns', 'SequenceName', 'SeriesNumber']
#
#         for group in self.local_paths_dict:
#             for key in self.local_paths_dict[group]:
#                 for path in self.local_paths_dict[group][key]:
#                     rows = []
#                     for dirName, subdirList, fileList in os.walk(path):
#                         for filename in fileList:
#                             if ".dcm" in filename.lower():
#                                 dict1 = {'FilePath': filename}
#                                 dcm = pydicom.dcmread(os.path.join(dirName, filename), stop_before_pixels=True)
#                                 for field in fields:
#                                     dict1.update({field: getattr(dcm, field)})
#                                 rows.append(dict1)
#                     self.local_dcms[key].append(pd.DataFrame(rows, columns=fields))
#
#     # TODO: Add constructor function for producing dataframe
