class DICOMName:
    def __init__(self, dcm_header):
        self.sequence = None
        self.series = None
        self.get_name(dcm_header)

    def get_name(self, dcm_header):
        try:
            if 'ep_b' in dcm_header.SequenceName and not any(['MIP' in s for s in dcm_header.ImageType]):
                self.sequence = 'dwi'
                if 'ADC' in dcm_header.ImageType:
                    self.series = 'adc'
                elif any(s in dcm_header.ImageType for s in ['TRACEW', 'DIFFUSION']):
                    if dcm_header.ManufacturerModelName == 'Aera':
                        try:
                            b_val = str(int(dcm_header[0x19, 0x100c].value))  # RMH Aera
                        except KeyError:
                            try:
                                b_val = str(int(dcm_header.MRDiffusionSequence[0][0x18, 0x9087].value))  # ICH Aera
                            except AttributeError:
                                # Old RMH Aera DWIs require same rule as Avanto DWI:
                                if '#' in dcm_header.SequenceName:
                                    dcm_header.SequenceName = dcm_header.SequenceName.split('#')[0]
                                elif '.' in dcm_header.SequenceName:
                                    dcm_header.SequenceName = dcm_header.SequenceName.split('.')[0]

                                b_val = ''.join([s for s in dcm_header.SequenceName if s.isdigit()])

                    elif dcm_header.ManufacturerModelName == 'Avanto':
                        b_val = ''.join([s for s in dcm_header.SequenceName if s.isdigit()])  # RMH Avanto

                    else:
                        raise ValueError('Manufacturer Model Name Unknown')

                    self.series = 'b' + str(b_val)
                else:
                    # print(dcm_header)
                    raise ValueError("Unknown DWI image!")  # todo: should this be NameError?

            elif 'fl3d2' in dcm_header.SequenceName:
                if 'ADD' not in dcm_header.ImageType:  # or 'DIV'?
                    if ('WATER' in dcm_header.ImageType) or (
                            dcm_header.ScanOptions and dcm_header.ScanOptions == 'DIXW'):
                        self.sequence = 'dix'
                        self.series = 'water'
                    elif ('FAT' in dcm_header.ImageType) or (
                            dcm_header.ScanOptions and dcm_header.ScanOptions == 'DIXF'):
                        self.sequence = 'dix'
                        self.series = 'fat'

                    elif dcm_header.ManufacturerModelName == 'Aera':
                        if 'IN_PHASE' in dcm_header.ImageType or (
                                any(s in dcm_header.SeriesDescription.lower() for s in ['in'])):  # sometimes ip needed
                            self.sequence = 'dix'
                            self.series = 'in'

                        elif 'OUT_PHASE' in dcm_header.ImageType or (
                                any(s in dcm_header.SeriesDescription.lower() for s in ['op', 'opp', 'out', '0pp'])):
                            self.sequence = 'dix'
                            self.series = 'out'

                    elif dcm_header.ManufacturerModelName == 'Avanto':
                        if dcm_header.EchoTime > 3:
                            self.sequence = 'dix'
                            self.series = 'in'
                        else:
                            self.sequence = 'dix'
                            self.series = 'out'

        except AttributeError:
            pass

        # todo: think about software version maybe 'syngo MR B17' 'syngo MR E11'

    def __str__(self):
        return f'Sequence: {self.sequence}, Series: {self.series}'

    def __bool__(self):
        return bool(self.sequence and self.series)





