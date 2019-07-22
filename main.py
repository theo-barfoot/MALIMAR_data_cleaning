import xnat
import os
import shutil

from data_io import MalimarSeries

# with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',
#                   user='tbarfoot', password='H3u#p5T3') as session:

with xnat.connect('http://localhost', user='admin', password='admin') as session:
    # TODO: Find way to include spreadsheet
    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    # project = session.projects["MALIMAR_ALL"]
    # mrSession = project.experiments['20171204_125025_Avanto']

    project = session.projects["MALIMAR_local"]
    mrSession = project.experiments['20180327_141908_Avanto']
    malimarSeries = MalimarSeries(mrSession)
    malimarSeries.download()
    malimarSeries.clean()

    # from cleaning import SliceMatchedVolumes
    # SliceMatchedVolumes.build_dcm_data_frames(malimarSeries.local_paths)

