import os
import pandas as pd
import pydicom


def build_dcm_data_frames(paths):
    fields = ['InstanceNumber', 'SliceLocation', 'Rows', 'Columns', 'SequenceName', 'SeriesNumber']
    local_dcms = []
    for g, group in enumerate(paths):
        local_dcms.append([])
        for path in group:
            rows = []
            for dirName, subdirList, fileList in os.walk(path):
                for filename in fileList:
                    if ".dcm" in filename.lower():
                        dict1 = {'FilePath': filename}
                        dcm = pydicom.dcmread(os.path.join(dirName, filename), stop_before_pixels=True)
                        for field in fields:
                            dict1.update({field: getattr(dcm, field)})
                        rows.append(dict1)
            local_dcms[g].append(pd.DataFrame(rows, columns=fields))
    print('Dataframes of DICOM headers constructed')
    return local_dcms

# class SliceMatchedVolumes:
#     def __init__(self, local_paths):
#         self.local_paths = local_paths
#
#         self.local_dcms = {}
#
#     def build_dcm_data_frames(self):
#         fields = ['InstanceNumber', 'SliceLocation', 'Rows', 'Columns', 'SequenceName', 'SeriesNumber']
#
#         for group in self.local_paths:
#             for key in self.local_paths[group]:
#                 for path in self.local_paths[group][key]:
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




# def correct_slice_order(malimarSeries):
#     # malimarSeries.local_paths
#     for key in malimarSeries.local:
#         for path in malimarSeries.local[key]:
#             dcm_files = get_dcm_filenames(path)