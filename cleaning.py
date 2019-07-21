import os
import pandas as pd
import pydicom

class Cleaning:
    def __init__(self, local_paths)
        self.local_paths = local_paths

        self.local_dcms = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                            'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}


def correct_slice_order(malimarSeries):
    # malimarSeries.local_paths
    for key in malimarSeries.local:
        for path in malimarSeries.local[key]:
            dcm_files = get_dcm_filenames(path)

    def build_dcm_data_frames(self):
        fields = ['InstanceNumber', 'SliceLocation', 'Rows', 'Columns', 'SequenceName', 'SeriesNumber']
        for key in self.local_paths:
            for path in self.local_paths[key]:
                rows = []
                for dirName, subdirList, fileList in os.walk(path):
                    for filename in fileList:
                        if ".dcm" in filename.lower():
                            dict1 = {'FilePath': filename}
                            dcm = pydicom.dcmread(os.path.join(dirName, filename), stop_before_pixels=True)
                            for field in fields:
                                dict1.update({field: getattr(dcm, field)})
                            rows.append(dict1)
                self.local_dcms[key].append(pd.DataFrame(rows,columns=fields))
        return self