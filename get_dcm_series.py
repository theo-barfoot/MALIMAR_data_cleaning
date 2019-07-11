def get_series(mr_session):

    tra = [1, 0, 0, 0, 1, 0]
    cor = [1, 0, 0, 0, 0, -1]

    scans = mr_session.scans
    for scan in scans.values():
        head = scan.read_dicom()
        d = scan.data

        if (
                (head.ImageOrientationPatient == cor and 'COMPOSED' in head.ImageType) or
                (head.ImageOrientationPatient == tra and d['frames'] > 100)
        ):
            if head.SequenceName[-5:] == 'fl3d2':
                if (head.EchoTime > 3) or ('IN_PHASE' in head.ImageType):
                    print(scan, 'in')
                elif head.ScanOptions == 'DIXW':  # or ('WATER' in d['parameters/imageType']):
                    print(scan, 'water')
                elif head.ScanOptions == 'DIXF':  # or ('FAT' in d['parameters/imageType']):
                    print(scan, 'fat')
                elif ('ADD' or 'DIV') not in head.ImageType:  # or ('OUT_PHASE' in d['parameters/imageType']) (('WATER' or 'FAT') not in d.get('parameters/imageType',''))
                    print(scan, 'out')

            if 'DIFFUSION' in head.ImageType:
                if d.get('parameters/sequence', '')[-7:] == 'ep_b50t':
                    print(scan, 'b50')
                elif d.get('parameters/sequence', '')[-8:] == 'ep_b600t':
                    print(scan, 'b600')
                elif d.get('parameters/sequence', '')[-8:] == 'ep_b900t':
                    print(scan, 'b900')
                elif d.get('parameters/sequence', '')[-10:] == 'ep_b50_900':
                    print(scan, 'ADC')
                elif 'COMPOSED' in d.get('parameters/imageType', ''):
                    print(scan, 'diff')



    # if (
    #         (head.ImageOrientationPatient == cor and (d.get('parameters/orientation', '') != 'Cor'))
    #     or
    #         (head.ImageOrientationPatient == tra and (d.get('parameters/orientation', '') != 'Tra'))
    # ):
    #     print('uh oh')
