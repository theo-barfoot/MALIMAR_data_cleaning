import os
import cleaning
import dicom2nifti
import shutil
import xml.etree.cElementTree as ET
import datetime
import uuid
from io import BytesIO

#  import SimpleITK as sitk


class MalimarSeries:
    def __init__(self, mr_session):
        # todo: add self.connection_up
        # todo: add self.connection_down - pass connections as arguments and then just the mr_session_down as a string
        self.mr_session_down = mr_session
        self.mr_session_up = None

        self.xnat_paths_dict = {'dixon': {'in': [], 'out': [], 'fat': [], 'water': []},
                                'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.local_paths_dict = {'dixon': {'in': [], 'out': [], 'fat': [], 'water': []},
                                 'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.complete = False
        self.duplicates = False
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
        for group, comp in zip(self.xnat_paths_dict, complete):
            for key, c in zip(self.xnat_paths_dict[group], comp):
                a.append(len(self.xnat_paths_dict[group][key]) - c)
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
        for group in self.xnat_paths_dict:
            for key in self.xnat_paths_dict[group]:
                for i, item in enumerate(self.xnat_paths_dict[group][key]):
                    path = os.path.join('temp/dicoms', key)
                    if i:
                        path = path+'_'+str(i+1)
                    print('Downloading: ', key)
                    item.download_dir(path)
                    self.local_paths_dict[group][key].append(path)

    def clean(self):
        self.is_clean = cleaning.SliceMatchedVolumes(self.local_paths_dict).generate()
        return self.is_clean

    def generate_nifti(self):
        os.mkdir('temp/nifti')
        for sequence in self.local_paths_dict:
            for series in self.local_paths_dict[sequence]:
                for i, path in enumerate(self.local_paths_dict[sequence][series]):
                    dicom2nifti.settings.enable_validate_slice_increment()
                    filename = series
                    if i:
                        filename = filename+'_'+str(i+1)
                    print('Converting', sequence, '-', filename, 'to', filename + '.nii.gz')
                    try:                        dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')
                    except Exception as e:
                        print(e)

                        #  dicom2nifti.settings.disable_validate_slice_increment()
                        #  dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')

    def upload_nifti(self):
        # TODO: need to think carefully about what are class/instance methods and what can be static
        scans = self.mr_session_up.scans
        for i, scan in scans.items():
            a = scan.create_resource(label='NIFTI', format='NIFTI')
            scan.resources['NIFTI'].upload('temp/nifti/' + scan.series_description + '.nii.gz', scan.series_description + '.nii.gz')
        # TODO: Really need to clean these file paths

    def upload_dicom(self, connection_up, project):
        print('Zipping DICOMs')
        shutil.make_archive('temp/dicoms', 'zip', 'temp/dicoms')
        print('Uploading DICOMs to', connection_up._original_uri)
        pre = connection_up.services.import_('temp/dicoms.zip', project=project, destination='/prearchive')
        print('Archiving MrSessionData')
        self.mr_session_up = pre.archive()
        print(self.mr_session_up.label, 'successfully archived')

        scans = self.mr_session_up.scans
        for i, scan in scans.items():
            scan.type = scan.series_description.split('_')[0]  # this doesn't change mr_sessions_up object

        self.mr_session_up = connection_up.experiments[self.mr_session_up.label]

    @staticmethod
    def upload_seg(mr_session_up, path, series):

        d = datetime.date.today().strftime('%Y-%m-%d')
        t = datetime.datetime.now().time().strftime('%H:%M:%S')
        dt = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        uid_ = str(uuid.uuid1())  # could change to datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        label = 'NIFTI_' + dt
        id_ = 'RoiCollection_' + dt  # could use uid, but a little unsightly

        filename_long = path.split('/')[-1]
        filename = filename_long.split('.')[0]


        root = ET.Element('RoiCollection')
        root.set('xmlns:icr', 'http://www.icr.ac.uk/icr')
        root.set('xmlns:prov', 'http://www.nbirn.net/prov')
        root.set('xmlns:xnat', 'http://nrg.wustl.edu/xnat')
        root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        root.set('id', id_)
        root.set('label', label)
        root.set('project', mr_session_up.project)
        root.set('version', '1')

        ET.SubElement(root, 'date').text = d
        ET.SubElement(root, 'time').text = t
        ET.SubElement(root, 'imageSession_ID').text = mr_session_up.label
        ET.SubElement(root, 'UID').text = uid_
        ET.SubElement(root, 'collectionType').text='NIFTI'
        ET.SubElement(root, 'subjectID').text = mr_session_up.subject_id
        ref = ET.SubElement(root, 'references')
        ET.SubElement(ref, 'seriesUID').text = mr_session_up.scans[series].uid
        ET.SubElement(root, 'name').text = filename

        tree = ET.ElementTree(root)
        f = BytesIO()
        tree.write(f, encoding='utf-8', xml_declaration=True)

        assessorUrl = mr_session_up.fulluri + '/assessors/' + id_
        putResourceMetadataUrl = assessorUrl + '?inbody=true'
        putCreateResourceUrl = assessorUrl + '/resources/NIFTI?content=EXTERNAL&format=NIFTI&description=NIFTI+instance+file&name=NIFTI'
        #  putUploadNiftiUrl = '/resources/NIFTI/files/{}?inbody=true&content=EXTERNAL&format=NIFTI'.format(filename)
        UploadNiftiUrl = filename_long+'?inbody=true&content=EXTERNAL&format=NIFTI'

        file_handle = open(path, 'rb')

        headers = {'Content-Type': 'text/xml'}

        print(putResourceMetadataUrl)
        mr_session_up.xnat_session.put(path=putResourceMetadataUrl, data=f.getvalue(), headers=headers)
        print(putCreateResourceUrl)
        mr_session_up.xnat_session.put(path=putCreateResourceUrl)
        print(UploadNiftiUrl)
        mr_session_up.assessors[id_].resources['NIFTI'].upload(path, UploadNiftiUrl)

        # headers = {'Content-Type': 'application/octet-stream'} -- two lines encounter 403 (permission) error
        # mr_session_up.xnat_session.put(path=putUploadNiftiUrl, data=file_handle, headers=headers)

        file_handle.close()

    def upload_series(self, connection_up, project):
        self.upload_dicom(connection_up, project)
        self.generate_nifti()
        self.upload_nifti()
        self.upload_seg(self.mr_session_up, 'temp/RMH_083_20170309_t1seg_theo.nii.gz', 'in')
        # while archiving do the nifti conversion?



