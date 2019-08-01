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


    # TODO: Nifti conversion and uploading
    # TODO: DICOM upload
    # TODO: Unpack Aera b-values into seperate series
    # TODO: Could have cleaning pass back lists for self.num_slice_order_corrected and then data_io concerts into
    # messaged that relate to the series which are corrupted ... or maybe just have the dict passed in the first place?

    # TODO: Ask jack how to add files to supervised git list..
    # TODO: Change input to cleaning back to dictionary and then build one large dataframe

    # change series descriptions for all series before upload as dicom
    # change series uid, (series number?) and sop instance uid - when any data (including istance number) has been changed
