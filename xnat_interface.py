import xnat
from identify_dicom import DICOMName
import os
import time


class XNATDownloader:
    def __init__(self, project, mr_id, composed=False, path=None):
        self.project = project
        self.connection = project.xnat_session
        self.mr_id = mr_id
        self.mr_session = project.experiments[mr_id]
        self.path = path if path else mr_id
        self.composed = composed
        self.dix = []
        self.dwi = []

    def identify_scans(self):

        def scan_is_composed(dcm_header, frames):
            return ('COMPOSED' in dcm_header.ImageType) or (frames > 120)

        for scan in self.mr_session.scans.values():
            volume_name = None
            try:
                dcm_header = scan.read_dicom()
                if (self.composed and scan_is_composed(dcm_header, scan.frames)) or \
                        (not self.composed and not scan_is_composed(dcm_header, scan.frames)):
                    volume_name = DICOMName(dcm_header)
            except ValueError:
                pass

            if volume_name:
                print(scan, volume_name)
                if volume_name.sequence == 'dix':
                    self.dix.append(scan)
                elif volume_name.sequence == 'dwi':
                    self.dwi.append(scan)

    def download_scans(self):
        os.mkdir(self.path)
        download_folder = os.path.join(self.path, 'input')
        os.mkdir(download_folder)
        for scan in self.dix:
            print(scan)
            time.sleep(.3)
            scan.download_dir(os.path.join(download_folder, 'dix'))
        for scan in self.dwi:
            print(scan)
            time.sleep(.3)
            scan.download_dir(os.path.join(download_folder, 'dwi'))


class XNATUploader:
    def __init__(self, project, path):
        self.project = project
        self.path = path
        self.connection = project.xnat_session
        self.mr_session = None

    def upload_dicom(self):
        print(f'Uploading DICOMs to {self.connection._original_uri}')
        pre = self.connection.services.import_(os.path.join(self.path, 'output/dicom.zip'),
                                               project=self.project.id, destination='/prearchive')
        print('Archiving MrSessionData')
        self.mr_session = pre.archive()
        print(self.mr_session.label, 'successfully archived')

        scans = self.mr_session.scans
        for i, scan in scans.items():
            print('Changing XNAT scan type', scan.type, 'to:', scan.series_description)
            scan.type = scan.series_description  # Can probably remove splits now

        try:  # Sometimes there is an issue with finding the scan that has just been uploaded, this seems to fix it
            self.mr_session = self.connection.experiments[self.mr_session.label]
        except KeyError:
            self.project.xnat_session.clearcache()
            self.mr_session = self.connection.experiments[self.mr_session.label]

    def upload_nifti(self):
        print('-- Uploading NIFTIs --')

        scans = self.mr_session.scans
        for i, scan in scans.items():
            a = scan.create_resource(label='NIFTI', format='NIFTI')
            print('Uploading', scan.series_description + '.nii.gz')
            scan.resources['NIFTI'].upload(os.path.join(self.path, 'output/nifti/') + scan.series_description + '.nii.gz',
                                           scan.series_description + '.nii.gz')

    def upload_session_vars(self, **session_vars):
        print('-- Uploading Session Variables --')
        defaults = {'roi_done_theo': 'No', 'roi_done_maira': 'No', 'roi_signed_off_andrea': 'No',
                    'disease_labelled_andrea': 'No'}

        session_vars = {**defaults, **session_vars}  # defaults will be overwritted if in session_vars

        for key, value in session_vars.items():
            print('Uploading', value, 'to field', key)
            if key == 'Age':
                self.mr_session.set('Age', value)
            elif key == 'Gender':
                self.mr_session.subject.demographics.gender = value
            else:
                self.mr_session.fields[key] = value

    def upload_cleaning_notebook(self):
        uri = f'{self.mr_session.uri}/resources/cleaning_report'
        self.connection.put(uri)
        self.mr_session.clearcache()
        path = 'cleaning_notebook.html'
        self.mr_session.resources['cleaning_report'].upload(data=os.path.join(self.path, path), remotepath=path)
