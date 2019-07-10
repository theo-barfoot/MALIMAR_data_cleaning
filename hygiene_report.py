import pandas as pd
import xnat


session = xnat.connect('https://bifrost.icr.ac.uk:8443/XNAT_anonymised/',user='tbarfoot',password='Iamawesome2')
project = session.projects["MALIMAR_ALL"]

# Check if patient scans are missing
patients = pd.read_excel('/Users/tbarfoot/Dropbox (ICR)/MALIMAR/Data Retrieval/allocation/Attempt_2/patients_allocated.xlsx')
pat_sess_missing = []

for sess in patients['MR Session ID XNAT_Colab']:
    try:
        project.experiments[sess]
    except:
        pat_sess_missing.append(sess)

print(len(pat_sess_missing), 'patient scans missing')

# Check if healthy volunteer scans are missing

hvs = pd.read_excel('/Users/tbarfoot/Dropbox (ICR)/MALIMAR/Data Retrieval/allocation/Attempt_2/hvs.xlsx')
hv_sess_missing = []

for sess in hvs['MR Session ID XNAT_Colab']:
    try:
        project.experiments[sess]
    except:
        hv_sess_missing .append(sess)

print(len(hv_sess_missing), 'hv scans missing')

total_sessions = len(patients) + len(hvs)

# Coronal DIXONS
no_cor = len(patients[patients['DIXON Orientation'] == 'cor']) + len(hvs[hvs['DIXON Orientation'] == 'cor'])

print(no_cor,'sessions with coronal DIXONS,','(',(no_cor/total_sessions)*100,'%'')',)

# Aera scans - assumed

session.disconnect()