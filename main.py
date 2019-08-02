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

    print('Successfully connected to: ', session._original_uri,' as user: ', session._logged_in_user)
    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    project = session.projects["MALIMAR_local"]
    print('Project: ', project.name)
    mrSession = project.experiments['20181215_152525_Avanto']
    print('-------------------------------------------------')
    print('MR Session: ', mrSession.label)

    malimarSeries = MalimarSeries(mrSession)
    if malimarSeries.complete:
        malimarSeries.download_series()
        malimarSeries.clean()
        if malimarSeries.is_clean:
            print('yeee')
            malimarSeries.upload_nifti()

    # TODO: Series UID
    # TODO: DICOM upload
    # TODO: NIFTI upload
    # TODO: Fix multiple series of same type detection
    # TODO: Implement Spreadsheet
    # TODO: Unpack Aera b-values
    # TODO: inplane resolution correction
    # TODO: Slice resampling
    # TODO: figure out coronal data.....
