import xnat
import pandas as pd
from data_io import MalimarSeries

local = 'http://localhost'
anon = 'https://bifrost.icr.ac.uk:8443/XNAT_anonymised'
colab = 'https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS'

with xnat.connect(server=anon) as connection_down:
    with xnat.connect(server=local) as connection_up:

        print('Successfully connected to download server: ', connection_down._original_uri,
              ' as user: ', connection_down._logged_in_user)
        print('Successfully connected to upload server: ', connection_up._original_uri,
              ' as user: ', connection_up._logged_in_user)

        project_down = connection_down.projects['MALIMAR_ALL']
        print('Download project: ', project_down.name)
        project_up = connection_up.projects['MALIMAR_local']
        print('Upload project: ', project_up.name)

        transfer_list = pd.read_excel('phase1_transfer.xlsx')
        hygiene_report = pd.read_csv('hygiene_report.csv')

        for idx, row in enumerate(transfer_list.itertuples()):

            mrSession_id = row.mr_session_id_xnat_colab
            print('{}:-------------------------{}-------------------------'.format(idx+1, mrSession_id))

            if mrSession_id in project_down.experiments and mrSession_id not in project_up.experiments:
                mrSession = project_down.experiments[mrSession_id]
                malimarSeries = MalimarSeries(mrSession)
                if malimarSeries.complete:
                    malimarSeries.download_series()  # may be better to use the language session rather than series
                    malimarSeries.clean()
                    if malimarSeries.is_clean:
                        malimarSeries.upload_series(project_up)
                        malimarSeries.upload_session_vars(row)
                hygiene = malimarSeries.hygiene
                hygiene.update({'session_id': mrSession_id})
                hygiene_report = hygiene_report.append(pd.DataFrame(hygiene, index=[0]),
                                                       sort=False)[hygiene_report.columns.tolist()]
                #  index to prevent: 'ValueError: If using all scalar values, you must pass an index'
                #  columns.tolist() required to maintain column order, ie session_id first

            elif mrSession_id not in project_down.experiments:
                print(mrSession_id, 'NOT FOUND!')

            elif mrSession_id in project_up.experiments:
                print(mrSession_id, 'ALREADY UPLOADED!')

        hygiene_report.to_csv('hygiene_report.csv', index=False)

        # TODO: Need XNAT_ICR to fix OHIF + ROIUploader -- might give up on this and just upload as resource

        # TODO: Unpack Aera b-values
        # TODO: inplane resolution correction
        # TODO: Slice resampling
        # TODO: figure out coronal data.....
        # TODO: In cleaning change 'Sequence' to 'Group' -- OR remove group descriptions and just index based on dummy group name
        # TODO: allow series/group descriptions + series number to be left empty and write init function to make default ones