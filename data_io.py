class MalimarSeries:
    def __init__(self):

        self.inPhase = []
        self.outPhase = []
        self.fat = []
        self.water = []
        self.b50 = []
        self.b600 = []
        self.b900 = []
        self.adc = []
        self.diff = []


def filter_series(mr_session):
    """
    :param mr_session:
    :return MalimarSeries:

    takes in XNATpy MRSessionData object and returns XNATpy MRScanData Object.
    """
    tra = [1, 0, 0, 0, 1, 0]
    cor = [1, 0, 0, 0, 0, -1]

    malimar_series = MalimarSeries()

    scans = mr_session.scans
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
                        malimar_series.inPhase.append(scan)
                    elif head.ScanOptions == 'DIXW':
                        malimar_series.water.append(scan)
                    elif head.ScanOptions == 'DIXF':
                        malimar_series.fat.append(scan)
                    elif ('ADD' or 'DIV') not in head.ImageType:
                        malimar_series.outPhase.append(scan)

                if 'DIFFUSION' in head.ImageType:
                    if d['frames'] < 400:
                        if head.SequenceName[-7:] == 'ep_b50t':
                            malimar_series.b50.append(scan)
                        elif head.SequenceName[-8:] == 'ep_b600t':
                            malimar_series.b600.append(scan)
                        elif head.SequenceName[-8:] == 'ep_b900t':
                            malimar_series.b900.append(scan)
                        elif head.SequenceName[-10:] == 'ep_b50_900':
                            malimar_series.adc.append(scan)
                    elif 'COMP_DIF' in head.ImageType:
                        malimar_series.diff.append(scan)
        except Exception as e:
            print(e, 'oh')

    return malimar_series

def download_series():
    return 0


