import xnat


class XNATUploader:
    def __init__(self, project):
        self.project = project
        self.connection = project.xnat_session
        self.mr_session = None

    def upload_dicom(self):
        print(f'Uploading DICOMs to {self.connection._original_uri}')
        pre = self.connection.services.import_('output/dicom.zip', project=self.project.id, destination='/prearchive')
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
            scan.resources['NIFTI'].upload('output/nifti/' + scan.series_description + '.nii.gz', scan.series_description + '.nii.gz')

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
        self.mr_session.resources['cleaning_report'].upload(data=path, remotepath=path)
