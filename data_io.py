import os
import cleaning


class MalimarSeries:
    def __init__(self, mr_session):

        self.mr_session = mr_session

        self.xnat_paths_dict = {'dixon': {'inPhase': [], 'outPhase': [], 'fat': [], 'water': []},
                                'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.local_paths_dict = {'dixon': {'inPhase': [], 'outPhase': [], 'fat': [], 'water': []},
                                 'diffusion': {'b50': [], 'b600': [], 'b900': [], 'adc': [], 'bvals': []}}

        self.complete = False
        self.duplicates = False

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
                print(e, 'oh')

    def __check_complete(self):
        complete = ((1, 1, 1, 1), (1, 0, 1, 1, 0))
        # TODO: Better not to inspect bvals, just unpack into b-vals and check for those
        # TODO: Need to change this so it checks dix and dif separately
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

    def __download_filtered_series(self):
        for group in self.xnat_paths_dict:
            for key in self.xnat_paths_dict[group]:
                for i, item in enumerate(self.xnat_paths_dict[group][key]):
                    path = os.path.join('temp', key+'('+str(i+1)+')')
                    print('Downloading: ', key)
                    item.download_dir(path)
                    self.local_paths_dict[group][key].append(path)
                # TODO: create function for unpacking bvals series and put path into MalimarSeries.local_paths_dict dictonary
                # TODO: change variable palceholders, eg key item to more useful names

    def download(self):
        self.__filter_xnat_session()
        self.__check_complete()
        if self.complete:
            self.__download_filtered_series()
        return self.local_paths_dict

    def clean(self):
        local_paths_list = []
        for g, group in enumerate(self.local_paths_dict):
            local_paths_list.append([])
            for series in self.local_paths_dict[group]:
                for item in self.local_paths_dict[group][series]:
                    local_paths_list[g].append(item)
        return cleaning.SliceMatchedVolumes(local_paths_list).generate()


