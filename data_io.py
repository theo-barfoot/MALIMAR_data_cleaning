import os


class MalimarSeries:
    def __init__(self, mr_session):

        self.mr_session = mr_session

        self.xnat_paths = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                           'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}

        self.local_paths = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                            'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}

        self.complete = False
        self.duplicates = False

    def __filter_xnat_session(self):
        """
        :param self:
        :return MalimarSeries:

        takes in XNATpy MRSessionData object and returns XNATpy MRScanData Object.
        """

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
                            self.xnat_paths['inPhase'].append(scan)
                        elif head.ScanOptions == 'DIXW':
                            self.xnat_paths['water'].append(scan)
                        elif head.ScanOptions == 'DIXF':
                            self.xnat_paths['fat'].append(scan)
                        elif ('ADD' or 'DIV') not in head.ImageType:
                            self.xnat_paths['outPhase'].append(scan)

                    if 'DIFFUSION' in head.ImageType:
                        if d['frames'] < 400:
                            if head.SequenceName[-7:] == 'ep_b50t':
                                self.xnat_paths['b50'].append(scan)
                            elif head.SequenceName[-8:] == 'ep_b600t':
                                self.xnat_paths['b600'].append(scan)
                            elif head.SequenceName[-8:] == 'ep_b900t':
                                self.xnat_paths['b900'].append(scan)
                            elif head.SequenceName[-10:] == 'ep_b50_900':
                                self.xnat_paths['adc'].append(scan)
                        elif 'COMP_DIF' in head.ImageType:
                            self.xnat_paths['diff'].append(scan)
            except Exception as e:
                print(e, 'oh')

    def __check_complete(self):
        comp = (1, 1, 1, 1, 1, 0, 1, 1, 0)
        # TODO: Better not to inspect diff, just unpack into b-vals and check for those
        a = []
        for key, c in zip(self.xnat_paths, comp):
            a.append(len(self.xnat_paths[key]) - c)
        self.complete = min(a) > -1
        self.duplicates = max(a) > 0

    def __download_filtered_series(self):
        for key in self.xnat_paths:
            for i, item in enumerate(self.xnat_paths[key]):
                path = os.path.join('temp', key+'('+str(i+1)+')')
                item.download_dir(path)
                self.local_paths[key].append(path)
                # TODO: create function for unpacking diff series and put path into MalimarSeries.local_paths dictonary

    def download(self):
        self.__filter_xnat_session()
        self.__check_complete()
        if self.complete:
            self.__download_filtered_series()
            return self.local_paths




