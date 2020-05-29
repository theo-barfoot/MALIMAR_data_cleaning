import time
import SimpleITK as sitk
import os
import pydicom
import shutil


def write_dcm_series(volume, path, **modified_tags):

    output_folder = os.path.join(path, 'output')
    try:
        os.mkdir(output_folder)
    except FileExistsError:
        pass

    output_folder_dicom = os.path.join(output_folder, 'dicom')
    try:
        os.mkdir(output_folder_dicom)
    except FileExistsError:
        pass

    reader = volume.dcm_reader
    series_description = volume.name
    # todo move this somewhere else:
    series_number_dict = {'in': 1, 'out': 2, 'fat': 3, 'water': 4,
                          'b50': 5, 'b600': 6, 'b800': 7, 'b900': 7, 'adc': 8}
    series_number = series_number_dict[volume.name]

    shutil.rmtree(os.path.join(output_folder_dicom, series_description), ignore_errors=True)
    os.mkdir(os.path.join(output_folder_dicom, series_description))

    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()

    """ this is sloppy, but I am going to use the dcm_header as a means of allowing the 
        modification of the following tags:
    "0010|0010",  # Patient Name         eg. RMH4820HV_014
    "0010|0020",  # Patient ID           eg. 758STJO
    "0010|0030",  # Patient Birth Date   eg. 19000101
    "0010|0040",  # Patient Sex
    "0010|4000",  # Patient Comments # 'Project: MALIMAR_ALL; Subject: ICH4820_003; Session: 20200119_133224'
    "0008|0020",  # Study Date
    "0008|0030",  # Study Time """

    for tag, value in modified_tags.items():
        setattr(volume.dcm_header, tag, value)

    volume.dcm_header.PatientComments = f'Project: MALIMAR_ALL; Subject: {volume.dcm_header.PatientName};' \
                                        f' Session: {volume.dcm_header.StudyDate}_{volume.dcm_header.StudyTime[:6]}_' \
                                        f'{volume.dcm_header.ManufacturerModelName}'
    # Patient Comments # 'Project: MALIMAR_ALL; Subject: ICH4820_003; Session: 20200119_133224_Avanto'

    tags_to_copy = [
                    "0020|000d",  # Study Instance UID, for machine consumption
                    "0020|0010",  # Study ID, for human consumption
                    "0008|0050",  # Accession Number
                    "0008|0060",  # Modality
                    "0018|5100",  # Patient Position
                    "0010|1030",  # Patient's Weight
                    "0010|1020",  # Patient's Size
                    "0008|0070",  # Manufacturer
                    "0008|1090",  # Manufacturer's Model Name
                    "0010|1010",  # Patient's Age
                    "0018|0015",  # Body Part Examined
                    "0018|0020",  # Scanning Sequence
                    "0018|0021",  # Sequence Variant
                    "0018|0022",  # Scan Options
                    "0018|0023",  # MR Acquisition Type
                    "0018|0024",  # Sequence Name
                    "0018|0080",  # Repetition Time
                    "0018|0081",  # Echo Time
                    "0018|0083",  # Number of Averages
                    "0018|0084",  # Imaging Frequency
                    "0018|0085",  # Imaged Nucleus
                    "0018|0086",  # Echo Number
                    "0018|0087",  # Magnetic Field Strength
                    "0018|0089",  # Number of Phase Encoding Steps
                    "0018|0091",  # Echo Train Length
                    "0018|0093",  # Percent Sampling
                    "0018|0094",  # Percent Phase Field of View
                    "0018|0095",  # Pixel Bandwidth
                    "0018|1000",  # Device Serial Number
                    "0018|1020",  # Software Versions
                    "0018|1251",  # Transmit Coil Name
                    "0018|1310",  # Acquisition Matrix
                    "0018|1312",  # In - plane Phase Encoding Direction
                    "0018|1314",  # Flip Angle
                    "0018|9117",  # MR Diffusion Sequence
                    "0019|0100",  # B-Value
                    ]

    modification_time = time.strftime("%H%M%S")
    modification_date = time.strftime("%Y%m%d")

    direction = volume.image_volume.GetDirection()
    slice_thickness = volume.slice_thickness

    series_tag_values = [(k, reader.GetMetaData(k)) for k in tags_to_copy if
                         reader.HasMetaDataKey(k)] + \
                        [("0008|0031", modification_time),                                      # Series Time
                         ("0008|0021", modification_date),                                      # Series Date
                         ("0020|0037", '\\'.join(map(str, (
                             direction[0], direction[3], direction[6],                          # Image Orientation
                             direction[1], direction[4], direction[7])))),
                         ("0008|103e", series_description),                                     # Series Description
                         ('0020|0011', str(series_number)),                                     # Series Number
                         ("0008|0008", "DERIVED\\SECONDARY"),                                   # Image Type
                         ("0018|0050", slice_thickness),                                        # Slice Thickness
                         ("0018|0088", slice_thickness),                                        # Spacing Between Slices
                         ("0020|000e", pydicom.uid.generate_uid(prefix='1.2.826.0.1.534147.')), # Series Instance UID
                         ("0010|0010", volume.dcm_header.PatientName),                          # Patient Name
                         ("0010|0020", volume.dcm_header.PatientID),                            # Patient ID
                         ("0010|0030", volume.dcm_header.PatientBirthDate),                     # Patient Birth Date
                         ("0010|0040", volume.dcm_header.PatientSex),                           # Patient Sex
                         ("0010|4000", volume.dcm_header.PatientComments),                      # Patient Comments
                         ("0008|0020", volume.dcm_header.StudyDate),                            # Study Date
                         ("0008|0030", volume.dcm_header.StudyTime[:6])                         # Study Time
                         ]
    for i in range(volume.image_volume.GetDepth()):
        image_slice = volume.image_volume[:, :, i]
        # Tags shared by the series.
        for tag, value in series_tag_values:
            image_slice.SetMetaData(tag, str(value))

        j = volume.image_volume.GetDepth() - i
        # Slice specific tags.
        image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d"))                         # Instance Creation Date
        image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S"))                         # Instance Creation Time
        image_slice.SetMetaData("0020|0032", '\\'.join(
            map(str, volume.image_volume.TransformIndexToPhysicalPoint((0, 0, i)))))          # Image Position (Patient)
        image_slice.SetMetaData("0020|1041",
                                str(volume.image_volume.TransformIndexToPhysicalPoint((0, 0, i))[2]))  # slice loc
        image_slice.SetMetaData("0020|0013", str(j))                                          # Instance Number
        image_slice.SetMetaData("0008|0018", pydicom.uid.generate_uid(prefix='1.2.826.0.1.534147.'))

        # Write to the output directory and add the extension dcm, to force writing in DICOM format.

        writer.SetFileName(os.path.join(output_folder_dicom, series_description, str(j) + '.dcm'))
        writer.Execute(image_slice)

    print('"' + series_description + '"', 'image volume saved as DICOM series')