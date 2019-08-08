import xnat


from data_io import MalimarSeries

# Anonymised: https://bifrost.icr.ac.uk:8443/XNAT_anonymised/ tbarfoot - MALIMAR_ALL - 20171204_125025_Avanto
# Local: http://localhost admin admin - MALIMAR_local
# ICR: https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS tbarfoot - MALIMAR_PHASE1

with xnat.connect(server='https://bifrost.icr.ac.uk:8443/XNAT_anonymised/', user='tbarfoot',
                  password='H3u#p5T3') as session_down:
    with xnat.connect(server='http://localhost', user='admin', password='admin') as session_up:
        # TODO: Find way to include spreadsheet

        print('Successfully connected to: ', session_down._original_uri, ' as user: ', session_down._logged_in_user)


        project = session_down.projects["MALIMAR_ALL"]
        print('Project: ', project.name)
        mrSession = project.experiments['20170223_100216_Avanto']
        print('-------------------------------------------------')
        print('MR Session: ', mrSession.label)

        malimarSeries = MalimarSeries(mrSession)
        if malimarSeries.complete:
            malimarSeries.download_series()
            malimarSeries.clean()
            if malimarSeries.is_clean:
                malimarSeries.upload_series(session_up, 'MALIMAR_local')


        # TODO: NIFTI upload
        # TODO: Fix multiple series of same type detection
        # TODO: change inPhase to in and outPhase to out
        # TODO: Implement Spreadsheet
        # TODO: Improve console prints
        # TODO: Unpack Aera b-values
        # TODO: inplane resolution correction
        # TODO: Slice resampling
        # TODO: figure out coronal data.....

#  'MrSessionData',
#  'MrsScanData',