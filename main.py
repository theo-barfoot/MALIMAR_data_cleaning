import xnat
import os
import shutil

from data_io import MalimarSeries

# with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',
#                   user='tbarfoot', password='-----') as session:

with xnat.connect('http://localhost', user='admin', password='admin') as session:
    # TODO: Find way to include spreadsheet
    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    # project = session.projects["MALIMAR_ALL"]
    # mrSession = project.experiments['20171204_125025_Avanto']

    project = session.projects["MALIMAR_local"]
    mrSession = project.experiments['20180327_141908_Avanto']
    malimarSeries = MalimarSeries(mrSession)
    paths = malimarSeries.download()

    # malimarSeries = MalimarSeries.build_dcm_data_frames(malimarSeries)
    # malimarSeries.local_dcms['inPhase'][0].to_excel('test.xlsx', index=False)

