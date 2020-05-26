import pandas as pd
import shutil
import os


def get_icht_case_variables(trial_number):
    df = pd.read_excel('patients_phase1_ICH.xlsx')
    row = df[df['Trial Number'] == trial_number]

    # patient tags required for editing DICOM headers of ICHT data
    patient_tags = {'PatientName': row['Anon Patient Name'].iloc[0],
                    'PatientBirthDate': '19010101',  # default anon DoB
                    'StudyDate': row['DOS'].iloc[0].strftime('%Y%m%d')}

    session_vars = {'disease_pattern': row['Disease Pattern'].iloc[0],
                    'disease_category': row['Disease Category'].iloc[0],
                    'dixon_orientation': 'tra',
                    'cm_comments': row['Comments'].iloc[0],  # Comments field in spreadsheet
                    'mk_comments': row['Indication'].iloc[0],  # Indication field in spreadsheet
                    'Age': int(row['AGE'].iloc[0]),
                    'Gender': row['Sex'].iloc[0]}

    session_vars = {k: v for k, v in session_vars.items() if pd.notna(v)}

    return patient_tags, session_vars


def get_rmh_case_variables(mr_id):
    df = pd.read_excel('patients_phase1_RMH.xlsx')
    row = df[df['MR Session ID XNAT_Colab'] == mr_id]

    session_vars = {'disease_pattern': row['Disease Pattern'].iloc[0],
                    'disease_category': row['Disease Category'].iloc[0],
                    'dixon_orientation': row['DIXON Orientation'].iloc[0],
                    'cm_comments': row['CM Comments'].iloc[0],  # Comments field in spreadsheet
                    'mk_comments': row['MK Comments'].iloc[0],  # Indication field in spreadsheet
                    'response_mk_imwg': row['Response MK IMWG'].iloc[0],
                    'Age': int(row['Age'].iloc[0])}

    session_vars = {k: v for k, v in session_vars.items() if pd.notna(v)}

    return session_vars


def transfer_icht_scan_files(trial_number, directory, composed=False, filt=False):
    num_dix = 0
    num_dwi = 0
    for folder in os.listdir(path=directory):
        if trial_number in folder:
            for dirName, subdirList, fileList in os.walk(os.path.join(directory, folder)):
                for subdir in subdirList:
                    if filt or 'FILT' not in subdir:
                        if 'dixon' in subdir and 'cor' not in subdir:
                            if 'COMP' in subdir and composed:
                                shutil.copytree(os.path.join(directory, folder, dirName, subdir),
                                                os.path.join('input/dix/', subdir))
                                num_dix += 1
                            elif 'COMP' not in subdir and not composed:
                                shutil.copytree(os.path.join(directory, folder, dirName, subdir),
                                                os.path.join('input/dix/', subdir))
                                num_dix += 1
                        elif 'ep2d' in subdir and 'CALC' not in subdir:
                            if 'COMP' in subdir and composed:
                                shutil.copytree(os.path.join(directory, folder, dirName, subdir),
                                                os.path.join('input/dwi/', subdir))
                                num_dwi += 1
                            elif 'COMP' not in subdir and not composed:
                                shutil.copytree(os.path.join(directory, folder, dirName, subdir),
                                                os.path.join('input/dwi/', subdir))
                                num_dwi += 1
    print(f'{num_dix} DIXON and {num_dwi} diffusion series transferred')
