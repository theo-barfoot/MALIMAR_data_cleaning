def get_name(dcm_header):
    try:
        if 'ep_b' in dcm_header.SequenceName:
            name = identify_dwi(dcm_header)
        elif 'fl3d2' in dcm_header.SequenceName:
            name = identify_dix(dcm_header)
        else:
            name = None
        return name

    except AttributeError:
        pass


def identify_dwi(dcm_header):
    """Inspect each DICOM header and return diffusion volume label"""
    if 'TRACEW' in dcm_header[0x08, 0x08].value:
        try:
            b_val = str(int(dcm_header[0x19, 0x100c].value))  # RMH Aera
        except KeyError:
            b_val = str(int(dcm_header.MRDiffusionSequence[0][0x18, 0x9087].value))  # ICH Aera
        return 'b' + str(b_val)
    elif 'ADC' in dcm_header[0x08, 0x08].value:
        return 'adc'
    else:
        raise ValueError("Unknown DWI image!")  # todo: should this be NameError?


def identify_dix(header):
    """Inspect each DICOM header and return DIXON series label, ie. in/out/fat/water"""
    if ('IN_PHASE' in header.ImageType):
        return 'in'
    elif ('WATER' in header.ImageType) or (header.ScanOptions and header.ScanOptions == 'DIXW'):
        return 'water'
    elif ('FAT' in header.ImageType) or (header.ScanOptions and header.ScanOptions == 'DIXF'):
        return 'fat'
    elif ('OUT_PHASE' in header.ImageType) or (('ADD' or 'DIV') not in header.ImageType):
        return 'out'
    else:
        raise ValueError("Unknown ")