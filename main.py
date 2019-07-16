import xnat

from data_io import filter_series

with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',
                  user='tbarfoot', password='H3u#p5T3') as session:
    project = session.projects["MALIMAR_ALL"]
    mrSession = project.experiments['20181205_080450_Aera']
    malimarSeries = filter_series(mrSession)


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
