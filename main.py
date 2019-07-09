import xnat

from get_dcm_series_d import get_scans

session = xnat.connect('https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',user='tbarfoot',password='Iamawesome2')
project = session.projects["MALIMAR_ALL"]

for experiment in project.experiments.values():
    print('------------new scan------------')
    print(experiment.label)
    get_scans(experiment)
    print('\n')

# MR_session = project.experiments['20131007_110748_Avanto']
# scans = MR_session.scans
# for scan in scans.values():
#     print(scan)
# print('end')