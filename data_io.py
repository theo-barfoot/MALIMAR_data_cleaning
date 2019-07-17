import os


class MalimarSeries:
    def __init__(self, mr_session):

        self.mr_session = mr_session

        self.xnat = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                     'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}

        self.local = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                      'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}

    def __check_complete(self):
        comp = (1, 1, 1, 1, 1, 0, 1, 1, 0)
        a = []
        for key, c in zip(self.xnat, comp):
            a.append(len(self.xnat[key]) - c)
        return min(a) > -1

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
                            self.xnat['inPhase'].append(scan)
                        elif head.ScanOptions == 'DIXW':
                            self.xnat['water'].append(scan)
                        elif head.ScanOptions == 'DIXF':
                            self.xnat['fat'].append(scan)
                        elif ('ADD' or 'DIV') not in head.ImageType:
                            self.xnat['outPhase'].append(scan)

                    if 'DIFFUSION' in head.ImageType:
                        if d['frames'] < 400:
                            if head.SequenceName[-7:] == 'ep_b50t':
                                self.xnat['b50'].append(scan)
                            elif head.SequenceName[-8:] == 'ep_b600t':
                                self.xnat['b600'].append(scan)
                            elif head.SequenceName[-8:] == 'ep_b900t':
                                self.xnat['b900'].append(scan)
                            elif head.SequenceName[-10:] == 'ep_b50_900':
                                self.xnat['adc'].append(scan)
                        elif 'COMP_DIF' in head.ImageType:
                            self.xnat['diff'].append(scan)
            except Exception as e:
                print(e, 'oh')

        return self

    def __download_filtered_series(self):
        for key in self.xnat:
            for i, item in enumerate(self.xnat[key]):
                path = os.path.join('temp', key+'('+str(i+1)+')')
                item.download_dir(path)
                self.local[key].append(path)

        return self

    def get_series(self):
        self.__filter_xnat_session()
        if self.__check_complete():
            self.__download_filtered_series()
            return self
        else:
            return 0


# TODO: create function for unpacking diff series and put path into MalimarSeries.local dictonary
