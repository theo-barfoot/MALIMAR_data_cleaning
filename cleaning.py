import os
import pandas as pd
import pydicom


class SliceMatchedVolumes:
    def __init__(self, local_paths_list):

        self.paths = local_paths_list
        self.dcm_header_df_list = []
        self.build_dcm_data_frames()

        self.num_slice_order_corrected = 0

    def build_dcm_data_frames(self):
        fields = ['InstanceNumber', 'SliceLocation', 'Rows', 'Columns', 'SequenceName', 'SeriesNumber']
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
                    ds = pydicom.dcmread(df['path'], stop_before_pixels=True)
                    # TODO: Need to find a way to iterate through df (maybe using .apply) are rewrite Instance No
                    self.num_slice_order_corrected += 1

    def generate(self):
        self.correct_slice_order()
        return self






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
