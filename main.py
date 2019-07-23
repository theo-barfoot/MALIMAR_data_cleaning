import xnat
import os
import shutil

from data_io import MalimarSeries

# Anonymised: https://bifrost.icr.ac.uk:8443/XNAT_anonymised/ tbarfoot - MALIMAR_ALL - 20171204_125025_Avanto
# Local: http://localhost admin admin - MALIMAR_local
# ICR: https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS tbarfoot - MALIMAR_PHASE1

with xnat.connect('https://xnatcruk.icr.ac.uk/XNAT_ICR_COLLABORATIONS', user='tbarfoot',
                  password='Iamawesome2') as session:
    # TODO: Find way to include spreadsheet

    shutil.rmtree('temp', ignore_errors=True)
    os.mkdir('temp')

    project = session.projects["MALIMAR_PHASE1"]
    mrSession = project.experiments['20170803_110927_Avanto']
    malimarSeries = MalimarSeries(mrSession)
    malimarSeries.download()
    malimarSeries.clean()

