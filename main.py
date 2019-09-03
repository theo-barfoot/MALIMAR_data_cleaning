import xnat
import pandas as pd
from data_io import MalimarSeries

local = 'http://localhost'
anon = 'https://bifrost.icr.ac.uk:8443/XNAT_anonymised'
colab = 'https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS'

with xnat.connect(server=anon) as connection_down:
    with xnat.connect(server=local) as connection_up:

        print('Successfully connected to: ', connection_down._original_uri,
              ' as user: ', connection_down._logged_in_user)

        #  transfer_df = pd.read_excel('phase1_transfer.xlsx')

        project = connection_down.projects["MALIMAR_ALL"]
        print('Project: ', project.name)
        mrSession = project.experiments['20170223_100216_Avanto']
        print('-------------------------------------------------')
        print('MR Session: ', mrSession.label)
        malimarSeries = MalimarSeries(mrSession)
        if malimarSeries.complete:
            malimarSeries.download_series()
            malimarSeries.clean()
            if malimarSeries.is_clean:
                malimarSeries.generate_nifti()
                malimarSeries.upload_series(connection_up, 'MALIMAR_local')


        # TODO: Custom Variables

        # TODO: Need XNAT_ICR to fix OHIF + ROIUploader -- might give up on this and just upload as resource
        # TODO: Improve console prints

        # TODO: Unpack Aera b-values
        # TODO: inplane resolution correction
        # TODO: Slice resampling
        # TODO: figure out coronal data.....
        # TODO: In cleaning change 'Sequence' to 'Group' -- OR remove group descriptions and just index based on dummy group name
        # TODO: allow series/group descriptions + series number to be left empty and write init function to make default ones