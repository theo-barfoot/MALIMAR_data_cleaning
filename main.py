import xnat
import os
import shutil
import pandas as pd

from data_io import MalimarSeries

with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',
                  user='tbarfoot', password='-----') as session:
    # TODO: Find way to include spreadsheet
    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    project = session.projects["MALIMAR_ALL"]
    mrSession = project.experiments['20171204_125025_Avanto']
    malimarSeries = MalimarSeries(mrSession)
    malimarSeries = MalimarSeries.get_series(malimarSeries)
    malimarSeries = MalimarSeries.build_dcm_data_frames(malimarSeries)
    malimarSeries.local_dcms['inPhase'][0].to_excel('test.xlsx', index=False)
    # #filtered_series = malimarSeries.get_filtered_series()
    # series = malimarSeries.downloadSeries()
    #
    # malimarSeries = filter_series(mrSession)
    # malimarSeries = download_series(malimarSeries)
    # print(malimarSeries.comlete())
    # # shutil.rmtree('temp')

# dicts = []
#
# for experiment in project.experiments.values():
#     print('------------new scan------------')
#     print(experiment.label)
#     try:
#         d = filter_series(experiment)
#         dicts.append(d)
#     except:
#         continue
#     print(d)
#     print('\n')

# MR_session = project.experiments['20131007_110748_Avanto']
# scans = MR_session.scans
# for scan in scans.values():
#     print(scan)
# print('end')
