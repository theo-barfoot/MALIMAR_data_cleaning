def get_scans(MR_session):
    scans = MR_session.scans
    for scan in scans.values():
        d = scan.data
        if (
                ((d.get('parameters/orientation', '') == 'Cor') and ('COMPOSED' in d.get('parameters/imageType', ''))) or
                ((d.get('parameters/orientation', '') == 'Tra') and (d['frames'] > 100))
        ):
            if d.get('parameters/sequence', '')[-5:] == 'fl3d2':
                if (d['parameters/te'] > 3) or ('IN_PHASE' in d['parameters/imageType']):
                    print(scan, 'in')
                elif (d.get('parameters/scanOptions', '') == 'DIXW'):  # or ('WATER' in d['parameters/imageType']):
                    print(scan, 'water')
                elif (d.get('parameters/scanOptions', '') == 'DIXF'):  # or ('FAT' in d['parameters/imageType']):
                    print(scan, 'fat')
                elif (('ADD') not in d.get('parameters/imageType',
                                           '')):  # or ('OUT_PHASE' in d['parameters/imageType']) (('WATER' or 'FAT') not in d.get('parameters/imageType',''))
                    print(scan, 'out')

            if 'DIFFUSION' in d.get('parameters/imageType', ''):
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
