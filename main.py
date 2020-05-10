import xnat
import pandas as pd
from data_io import MalimarSeries

local = 'http://localhost'
anon = 'https://bifrost.icr.ac.uk:8443/XNAT_anonymised'
colab = 'https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS'

with xnat.connect(server=anon) as connection_down:
    with xnat.connect(server=colab) as connection_up:

        print('Successfully connected to download server: ', connection_down._original_uri,
              ' as user: ', connection_down._logged_in_user)
        print('Successfully connected to upload server: ', connection_up._original_uri,
              ' as user: ', connection_up._logged_in_user)

        project_down = connection_down.projects['MALIMAR_ALL']
        print('Download project: ', project_down.name)
        project_up = connection_up.projects['MALIMAR_PHASE1']
        print('Upload project: ', project_up.name)

        transfer_list = pd.read_excel('phase1_transfer.xlsx')

        completes = pd.read_excel('phase1_transfer_complete.xlsx')  # list of MR sessions that have been transferred
        duplicates = pd.read_excel('phase1_duplicate_series.xlsx')  # list of MR sessions with duplicated series
        incompletes = pd.read_excel('phase1_missing_series.xlsx')  # list of MR sessions with missing series
        unclean = pd.read_excel('phase1_for_cleaning.xlsx')  # list of MR sessions that still need cleaning
        missing = pd.read_excel('phase1_missing_mrsession.xlsx')  # lust of MR sessions that are missing from down

        hygiene_report = pd.read_csv('hygiene_report.csv')

        for idx, row in enumerate(transfer_list.itertuples()):

            mrSession_id = row.mr_session_id_xnat_colab
            print('{}:-------------------------{}-------------------------'.format(idx+1, mrSession_id))

            if mrSession_id in project_down.experiments and mrSession_id not in project_up.experiments:
                mrSession = project_down.experiments[mrSession_id]
                malimarSeries = MalimarSeries(mrSession)
                if malimarSeries.complete and not malimarSeries.duplicates:
                    malimarSeries.download_series()  # may be better to use the language session rather than series
                    malimarSeries.clean()
                    hygiene = malimarSeries.hygiene
                    hygiene.update({'session_id': mrSession_id})
                    hygiene_report = hygiene_report.append(pd.DataFrame(hygiene, index=[0]),
                                                           sort=False)[hygiene_report.columns.tolist()]
                    #  index to prevent: 'ValueError: If using all scalar values, you must pass an index'
                    #  columns.tolist() required to maintain column order, ie session_id first
                    hygiene_report.to_csv('hygiene_report.csv', index=False)
                    if malimarSeries.is_clean:
                        malimarSeries.upload_series(project_up)
                        malimarSeries.upload_session_vars(row)
                        completes = completes.append(transfer_list.loc[idx], ignore_index=True)

                    else:
                        unclean = unclean.append(transfer_list.loc[idx], ignore_index=True)

                elif not malimarSeries.complete:
                    incompletes = incompletes.append(transfer_list.loc[idx], ignore_index=True)

                elif malimarSeries.duplicates:
                    duplicates = duplicates.append(transfer_list.loc[idx], ignore_index=True)

            elif mrSession_id not in project_down.experiments:
                print(mrSession_id, 'NOT FOUND!')
                missing = missing.append(transfer_list.loc[idx], ignore_index=True)

            elif mrSession_id in project_up.experiments:
                print(mrSession_id, 'ALREADY UPLOADED!')

            transfer_list.drop(idx, inplace=True)
            completes.to_excel('phase1_transfer_complete.xlsx', index=False)
            duplicates.to_excel('phase1_duplicate_series.xlsx', index=False)
            incompletes.to_excel('phase1_missing_series.xlsx', index=False)
            unclean.to_excel('phase1_for_cleaning.xlsx', index=False)
            missing.to_excel('phase1_missing_mrsession.xlsx', index=False)
            transfer_list.to_excel('phase1_transfer.xlsx', index=False)

        # todo: compy the object orientation of the aera-wb project, create class of vol then child called dw or dx vol
        # todo: SequenceName is mising from cleaned DICOMS.....
        # TODO: How to deal with b-vals and b50 600 900 , which one to choose?
        # TODO: Worth coding for slices from different sequence in series? - or is it too rare?
        # quite simple: just choose the unpacked values and delete the b-val one, best to
        # implememt this in the download section so you never download the b-vals
        # TODO: look at errors
        # TODO: how to deal with non ['1', '0', '0', '0', '1', '0'] data
        # TODO: In cleaning change 'Sequence' to 'Group' -- OR remove group descriptions and just index based on dummy group name
        # TODO: allow series/group descriptions + series number to be left empty and write init function to make default ones