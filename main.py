import xnat
import os
import shutil

from data_io import filter_series, download_series

with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',
                  user='tbarfoot') as session:

    shutil.rmtree('temp',ignore_errors=True)
    os.mkdir('temp')

    project = session.projects["MALIMAR_ALL"]
    mrSession = project.experiments['20171204_125025_Avanto']
    malimarSeries = filter_series(mrSession)
    malimarSeries = download_series(malimarSeries)

    # shutil.rmtree('temp')

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
