import os
import cleaning
import dicom2nifti
#  import SimpleITK as sitk


class MalimarSeries:
    def __init__(self, mr_session):

        self.mr_session = mr_session

        self.xnat_paths_dict = {'dixon': {'inPhase': [], 'outPhase': [], 'fat': [], 'water': []},
                                'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.local_paths_dict = {'dixon': {'inPhase': [], 'outPhase': [], 'fat': [], 'water': []},
                                 'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.complete = False
        self.duplicates = False
        self.is_clean = False

        self.__filter_xnat_session()
        self.__check_complete()

    def __filter_xnat_session(self):
        """
        :param self:
        :return MalimarSeries:

        takes in XNATpy MRSessionData object and returns XNATpy MRScanData Object.
        """
        print('Identifying required series for MALIMAR')
        tra = [1, 0, 0, 0, 1, 0]
        cor = [1, 0, 0, 0, 0, -1]

        scans = self.mr_session.scans
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
                            self.xnat_paths_dict['dixon']['inPhase'].append(scan)
                            print('DIXON - in phase:', scan)
                        elif head.ScanOptions == 'DIXW':
                            self.xnat_paths_dict['dixon']['water'].append(scan)
                            print('DIXON - water:', scan)
                        elif head.ScanOptions == 'DIXF':
                            self.xnat_paths_dict['dixon']['fat'].append(scan)
                            print('DIXON - fat:', scan)
                        elif ('ADD' or 'DIV') not in head.ImageType:
                            self.xnat_paths_dict['dixon']['outPhase'].append(scan)
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
        for group in self.xnat_paths_dict:
            for key in self.xnat_paths_dict[group]:
                for i, item in enumerate(self.xnat_paths_dict[group][key]):
                    path = os.path.join('temp', key)
                    if i:
                        path = path+'_'+str(i+1)
                    print('Downloading: ', key)
                    item.download_dir(path)
                    self.local_paths_dict[group][key].append(path)

    def clean(self):
        self.is_clean = cleaning.SliceMatchedVolumes(self.local_paths_dict).generate()
        return self.is_clean

    def upload_nifti(self):
        os.mkdir('temp/nifti')
        for sequence in self.local_paths_dict:
            for series in self.local_paths_dict[sequence]:
                for i, path in enumerate(self.local_paths_dict[sequence][series]):
                    dicom2nifti.settings.enable_validate_slice_increment()
                    filename = series
                    if i:
                        filename = filename+'_'+str(i+1)
                    print('Converting', sequence, '-', filename, 'to', filename + '.nii.gz')
                    try:
                        dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')
                    except Exception as e:
                        print(e)
                        #  dicom2nifti.settings.disable_validate_slice_increment()
                        #  dicom2nifti.convert_dicom.dicom_series_to_nifti(path, 'temp/nifti/'+filename+'.nii.gz')



    def upload_dicom(self):
        pass


