import xnat
import os
import shutil

from data_io import MalimarSeries

# Anonymised: https://bifrost.icr.ac.uk:8443/XNAT_anonymised/ tbarfoot - MALIMAR_ALL - 20171204_125025_Avanto
# Local: http://localhost admin admin - MALIMAR_local
# ICR: https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS tbarfoot - MALIMAR_PHASE1

with xnat.connect(server='http://localhost', user='admin',
                  password='admin') as session:
    # TODO: Find way to include spreadsheet

    print('Successfully connected to: ',session._original_uri,' as user: ',session._logged_in_user)
    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    project = session.projects["MALIMAR_local"]
    print('Project: ', project.name)
    mrSession = project.experiments['20181215_152525_Avanto']
    print('-------------------------------------------------')
    print('MR Session: ', mrSession.label)

    malimarSeries = MalimarSeries(mrSession)
    malimarSeries.download()
    output = malimarSeries.clean()

