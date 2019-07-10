def get_series(mr_session):
    scans = mr_session.scans
    for scan in scans.values():
        head = scan.read_dicom()
        print(head.SeriesDescription)
        print(head.ImageOrientationPatient)

        # axial = ['1', '0', '0', '0', '1', '0']
        # cor = ['1', '0', '0', '0', '0', '-1']