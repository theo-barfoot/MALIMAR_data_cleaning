class MalimarSeries:
    def __index__(self):
        # self.__dictionary = {'in': [], 'out': [], 'fat': [], 'water': [], 'b50': [], 'b600': [], 'b900': [], 'ADC': [], 'diff': []}
        self.inPhase = []
        self.outPhase = []
        self.fat = []
        self.water = []
        self.b50 = []
        self.b600 = []
        self.b900 = []
        self.adc = []
        self.diff = []

    def getInPhase(self):
        return self.inPhase

    def appendIn(self, inVal):
        self.__dictionary['in'].append(inVal)

    def getIn(self):
        return self.__dictionary['in']



def filter_series(mr_session):
    """
    :param mr_session:
    :return series:

    takes in MRSessionData object and returns dictionary of series numbers for each series type required in
    MALIMAR project.
    """
    tra = [1, 0, 0, 0, 1, 0]
    cor = [1, 0, 0, 0, 0, -1]

    series = {'in': [], 'out': [], 'fat': [], 'water': [], 'b50': [], 'b600': [], 'b900': [], 'ADC': [], 'diff': []}

    malimarSeries = MalimarSeries()

    malimarSeries.appendIn('TEST')

    malimarSeries.getIn()

    scans = mr_session.scans
    for scan in scans.values():
        try:
            head = scan.read_dicom()
            d = scan.data
            if (
                    (head.ImageOrientationPatient == cor and 'COMPOSED' in head.ImageType) or
                    (head.ImageOrientationPatient == tra and d['frames'] > 100)
            ):
                if head.SequenceName[-5:] == 'fl3d2':
                    if (head.EchoTime > 3) or ('IN_PHASE' in head.ImageType):
                        malimarSeries.inPhase.append(d['ID'])
                    elif head.ScanOptions == 'DIXW':
                        series['water'].append(d['ID'])
                    elif head.ScanOptions == 'DIXF':
                        series['fat'].append(d['ID'])
                    elif ('ADD' or 'DIV') not in head.ImageType:
                        series['out'].append(d['ID'])

                if 'DIFFUSION' in head.ImageType:
                    if head.SequenceName[-7:] == 'ep_b50t':
                        series['b50'].append(d['ID'])
                    elif head.SequenceName[-8:] == 'ep_b600t':
                        series['b600'].append(d['ID'])
                    elif head.SequenceName[-8:] == 'ep_b900t':
                        series['b900'].append(d['ID'])
                    elif head.SequenceName[-10:] == 'ep_b50_900':
                        series['ADC'].append(d['ID'])
                    elif 'COMPOSED' in head.ImageType:
                        series['diff'].append(d['ID'])
        except Exception as e:
            print(e)

    return series

