import os
from cleaning import SliceMatchedVolumes
import dicom2nifti
import shutil
# import xml.etree.cElementTree as ET
# import datetime
# import uuid
# from io import BytesIO
import requests

#  import SimpleITK as sitk


class MalimarSeries:
    def __init__(self, mr_session):
        self.mr_session_down = mr_session
        self.mr_session_up = None

        self.xnat_paths_dict = {'dixon': {'in': [], 'out': [], 'fat': [], 'water': []},
                                'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.local_paths_dict = {'dixon': {'in': None, 'out': None, 'fat': None, 'water': None},
                                 'diffusion': {'b50': None, 'b600': None, 'b900': None, 'adc': None, 'bvals': None}}

        self.complete = False
        self.duplicates = False

        self.hygiene = {'num_slice_order_corrected': 0, 'num_inplane_dim_mismatch': 0, 'slice_matched': False}
        self.is_clean = False

        self.__filter_xnat_session()
        self.__check_complete()
        shutil.rmtree('temp', ignore_errors=True)
        os.mkdir('temp')

    def __filter_xnat_session(self):
        """
        :param self:
        :return MalimarSeries:

        takes in XNATpy MRSessionData object and returns XNATpy MRScanData Object.
        """
        print('Identifying required series for MALIMAR')
        tra = [1, 0, 0, 0, 1, 0]
        cor = [1, 0, 0, 0, 0, -1]

        scans = self.mr_session_down.scans
        for scan in scans.values():
            try:
                head = scan.read_dicom()
                d = scan.data
                if (
                        (head.ImageOrientationPatient == cor and 'COMPOSED' in head.ImageType) or
                        (head.ImageOrientationPatient == tra and d['frames'] > 120)
                ):
                    if head.SequenceName[-5:] == 'fl3d2':
                        if (head.EchoTime > 3) or ('IN_PHASE' in head.ImageType):
                            self.xnat_paths_dict['dixon']['in'].append(scan)
                            print('DIXON - in phase:', scan)
                        elif head.ScanOptions == 'DIXW':
                            self.xnat_paths_dict['dixon']['water'].append(scan)
                            print('DIXON - water:', scan)
                        elif head.ScanOptions == 'DIXF':
                            self.xnat_paths_dict['dixon']['fat'].append(scan)
                            print('DIXON - fat:', scan)
                        elif ('ADD' or 'DIV') not in head.ImageType:
                            self.xnat_paths_dict['dixon']['out'].append(scan)
                            print('DIXON - out of phase:', scan)

                    if 'DIFFUSION' in head.ImageType:
                        if d['frames'] < 400:
                            if head.SequenceName[-7:] == 'ep_b50t':
                                self.xnat_paths_dict['diffusion']['b50'].append(scan)
                                print('Diffusion - b50:', scan)
                            elif head.SequenceName[-8:] == 'ep_b600t':
                                self.xnat_paths_dict['diffusion']['b600'].append(scan)
                                print('Diffusion - b600:', scan)
                            elif head.SequenceName[-8:] == 'ep_b900t':
                                self.xnat_paths_dict['diffusion']['b900'].append(scan)
                                print('Diffusion - b900:', scan)
                            elif head.SequenceName[-10:] == 'ep_b50_900':
                                self.xnat_paths_dict['diffusion']['adc'].append(scan)
                                print('Diffusion - ADC:', scan)
                        elif 'COMP_DIF' in head.ImageType:
                            self.xnat_paths_dict['diffusion']['bvals'].append(scan)
                            print('Diffusion - b values:', scan)
            except Exception as e:
                print(e)

    def __check_complete(self):
        complete = ((1, 1, 1, 1), (1, 0, 1, 1, 0))  # Avanto complete
        # TODO: Be useful to print which series are missing
        a = []
        for sequence, comp in zip(self.xnat_paths_dict, complete):
            for series, c in zip(self.xnat_paths_dict[sequence], comp):
                if c:  # if the series is required
                    a.append(len(self.xnat_paths_dict[sequence][series]) - c)
        self.complete = min(a) > -1
        if self.complete:
            print('All required series found!')
        else:
            print('ERROR: Unable to locate all required series')

        self.duplicates = max(a) > 0
        if self.duplicates:
            print('WARNING: Multiple series of same type found!')
        return self

    def download_series(self):
        os.mkdir('temp/dicoms')
        for sequence in self.xnat_paths_dict:
            for series in self.xnat_paths_dict[sequence]:
                for i, item in enumerate(self.xnat_paths_dict[sequence][series]):
                    path = os.path.join('temp/dicoms', series)
                    if i:
                        print('ERROR: Multiple series of same type trying to be downloaded!')
                    print('Downloading: ', series)
                    item.download_dir(path)
                    self.local_paths_dict[sequence][series] = path

    def clean(self):
        local_paths_list = []
        series_descriptions = []
        series_numbers = []
        ser_no = 1
        group_descriptions = ['dixon', 'diffusion']

        for seq_no, sequence in enumerate(self.local_paths_dict):
            local_paths_list.append([])
            series_descriptions.append([])
            series_numbers.append([])
            for series in self.local_paths_dict[sequence]:
                if self.local_paths_dict[sequence][series]:
                    local_paths_list[seq_no].append(self.local_paths_dict[sequence][series])
                    series_descriptions[seq_no].append(series)
                    series_numbers[seq_no].append(ser_no)
                ser_no += 1

        matched_volume = SliceMatchedVolumes(local_paths_list, group_descriptions, series_descriptions,
                                                     series_numbers, uid_prefix='1.2.826.0.1.534147.')
        matched_volume.generate()

        for param in self.hygiene:
            self.hygiene[param] = getattr(matched_volume, param)

        self.is_clean = matched_volume.is_clean

    def generate_nifti(self):
        os.mkdir('temp/nifti')
        for sequence in self.local_paths_dict:
            for series in self.local_paths_dict[sequence]:
                if self.local_paths_dict[sequence][series]:
                    path = self.local_paths_dict[sequence][series]
                    dicom2nifti.settings.enable_validate_slice_increment()
                    filename = series
                    print('Converting', sequence, '-', filename, 'to', filename + '.nii.gz')
                    try:
                        dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')
                    except Exception as e:
                        print(e)

                        #  dicom2nifti.settings.disable_validate_slice_increment()
                        #  dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')

    def upload_dicom(self, project_up):
        path = 'temp/dicoms'
        print('Zipping DICOMs')
        shutil.make_archive(path, 'zip', path)
        connection_up = project_up.xnat_session
        print('Uploading DICOMs to', connection_up._original_uri)
        pre = connection_up.services.import_('temp/dicoms.zip', project=project_up.id, destination='/prearchive')
        print('Archiving MrSessionData')
        self.mr_session_up = pre.archive()
        print(self.mr_session_up.label, 'successfully archived')

        scans = self.mr_session_up.scans
        for i, scan in scans.items():
            print('Changing XNAT scan type', scan.type, 'to:', scan.series_description.split('_')[0])
            scan.type = scan.series_description.split('_')[0]  # Can probably remove splits now

        self.mr_session_up = connection_up.experiments[self.mr_session_up.label]
        # Required to update object with new types

    def upload_nifti(self):
        scans = self.mr_session_up.scans
        for i, scan in scans.items():
            a = scan.create_resource(label='NIFTI', format='NIFTI')
            print('Uploading', scan.series_description + '.nii.gz')
            scan.resources['NIFTI'].upload('temp/nifti/' + scan.series_description + '.nii.gz', scan.series_description + '.nii.gz')
        # TODO: Really need to clean these file paths

    def upload_series(self, project_up):
        MalimarSeries.upload_dicom(self, project_up)
        MalimarSeries.generate_nifti(self)
        MalimarSeries.upload_nifti(self)
        #  MalimarSeries.upload_seg(mr_session_up, 'RMH_083_20170309_t1seg_theo.nii.gz', 'in')

    def upload_session_vars(self, row):

        session_vars = ['disease_pattern', 'disease_category', 'dixon_orientation', 'cm_comments',
                        'mk_comments', 'tb_comments', 'response_mk_imwg']

        for var in session_vars:
            self.mr_session_up.fields[var] = getattr(row, var)

        self.mr_session_up.set('Age', row.Age)

        # need to write method to upload crf, see phone camera for placement

    @staticmethod
    def upload_seg(mr_session_up, path, series):
        print('Uploading', path.split('/')[-1], 'to', series, 'scan')
        root_uri = mr_session_up.xnat_session._original_uri
        project = mr_session_up.project
        session_id = mr_session_up.id
        series_uid = mr_session_up.scans[series].read_dicom().SeriesInstanceUID
        label = 't1seg'  # needs changing - not sure exactly what it is best as

        uri = '{}/xapi/roi/projects/{}/sessions/{}/collections/{}?type=NIFTI&overwrite=true&seriesuid={}'.format(root_uri, project, session_id, label, series_uid)
        headers = {'Content-Type': 'application/octet-stream'}
        file_handle = open(path, 'rb')

        response = requests.put(url=uri, data=file_handle, headers=headers, auth=('admin', 'admin'))  # Auth can be netrc
        print(response)
        file_handle.close()








