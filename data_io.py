import os

class MalimarSeries:
    def __init__(self):

        self.xnat = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                     'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}

        self.local = {'inPhase': [], 'outPhase': [], 'fat': [], 'water': [],
                      'b50': [], 'b600': [], 'b900': [], 'adc': [], 'diff': []}


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
                        malimar_series.xnat['inPhase'].append(scan)
                    elif head.ScanOptions == 'DIXW':
                        malimar_series.xnat['water'].append(scan)
                    elif head.ScanOptions == 'DIXF':
                        malimar_series.xnat['fat'].append(scan)
                    elif ('ADD' or 'DIV') not in head.ImageType:
                        malimar_series.xnat['outPhase'].append(scan)

                if 'DIFFUSION' in head.ImageType:
                    if d['frames'] < 400:
                        if head.SequenceName[-7:] == 'ep_b50t':
                            malimar_series.xnat['b50'].append(scan)
                        elif head.SequenceName[-8:] == 'ep_b600t':
                            malimar_series.xnat['b600'].append(scan)
                        elif head.SequenceName[-8:] == 'ep_b900t':
                            malimar_series.xnat['b900'].append(scan)
                        elif head.SequenceName[-10:] == 'ep_b50_900':
                            malimar_series.xnat['adc'].append(scan)
                    elif 'COMP_DIF' in head.ImageType:
                        malimar_series.xnat['diff'].append(scan)
        except Exception as e:
            print(e, 'oh')
    # TODO: check is all required series are present and if not then write error to log file? or maybe pass back variable indicating completeness such that the download method can be called using condition
    return malimar_series


def download_series(malimar_series):
    for key in malimar_series.xnat:
        for i, item in enumerate(malimar_series.xnat[key]):
            path = os.path.join('temp', key+'('+str(i+1)+')')
            item.download_dir(path)
            malimar_series.local[key].append(path)

    return malimar_series

# TODO: create function for unpacking diff series and put path into MalimarSeries.local dictonary
