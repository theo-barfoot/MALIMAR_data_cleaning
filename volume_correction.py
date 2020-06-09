import os
import pydicom
from pydicom.errors import InvalidDicomError
import SimpleITK as sitk
from tqdm import tqdm
from itertools import compress, cycle, islice
from more_itertools import run_length
import numpy as np
import matplotlib.pyplot as plt
import time
from collections import Counter
import subprocess
from termcolor import colored
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from registration_tools import VolumeSliceTranslation, SliceTranslation
from identify_dicom import DICOMName
from dicom_writer import write_dcm_series
import coronal_tools


class VolumeCollection:
    def __init__(self, *, path):
        self.path = path
        self.sup_folder = path.split('/')[0]  # todo: really need to improve how paths set globally with the mr_id
        self.volumes = {}
        self.load_dicom_files()

        for volume_name, volume in self.volumes.items():
            volume.calculate_slice_intervals()

        # todo: take input of HFS or otherwise and define slice order for instance numbers in DICOM header

    @staticmethod
    def walk_directory(path):
        """Walk through each file in the directory folder, yielding path"""
        if not os.path.isdir(path):
            raise NotADirectoryError('Invalid Path - Directory does not exist!')

        for dirName, subdirList, fileList in os.walk(path):
            for filename in fileList:
                yield os.path.join(dirName, filename)

    def load_dicom_files(self):
        """Read each DCM file header, identify dicom scan type, instantiate volume if it doesn't already
        exist. Instantiate and add slice to volume"""
        # tqdm implementation taken from: https://github.com/tqdm/tqdm/wiki/How-to-make-a-great-Progress-Bar
        file_counter = 0
        dcm_file_counter = 0
        for _ in self.walk_directory(self.path):
            file_counter += 1

        print(' Scanning {} files'.format(file_counter))
        time.sleep(.3)  # for some unknown reason the tqdm print starts before the previous print statement
        with tqdm(total=file_counter) as pbar:
            for path in self.walk_directory(self.path):
                try:
                    dcm_header = pydicom.dcmread(path, stop_before_pixels=True)
                    name = DICOMName(dcm_header)

                    if name:
                        volume_name = name.series
                        if volume_name not in self.volumes.keys():
                            self.volumes.update({volume_name: Volume(self, volume_name, dcm_header)})

                        if dcm_header.StudyInstanceUID == self.volumes[volume_name].dcm_header.StudyInstanceUID:
                            self.volumes[volume_name].add_slice(path, dcm_header)
                            dcm_file_counter += 1
                        else:
                            raise ValueError("Multiple Study UIDs found for some volume type!")

                except InvalidDicomError:
                    pass
                pbar.set_postfix(file=path[-10:], refresh=True)
                pbar.update()

        print(f'{dcm_file_counter} DICOM files loaded')

    def correct_slice_contiguity(self):
        for volume_name, volume in self.volumes.items():
            volume.correct_slice_contiguity()

    def display_slices(self, slice_idx, grid=True, text=True):
        """Create 2x2 subplot array and populate axis with slice image determined by slice_idx """
        num_cols, num_rows = 2, 2
        fig, axs = plt.subplots(num_rows, num_cols, figsize=(12, 12))
        fig.set_dpi(100)
        for volume_name, volume, ax in zip(self.volumes.keys(), self.volumes.values(), axs.flatten()):
            volume.slices[slice_idx].populate_ax_with_slice_image(ax, grid, text)

        for ax in axs.flatten():
            if not ax.images:
                ax.axis('off')

    def set_registration_as_translation(self, reference_name):
        reference = self.volumes[reference_name]
        for volume in self.volumes.values():
            if volume is not reference:
                volume.set_registration_as_translation()
                volume.registration.reference_volume = reference

    def register_slices(self, reference_name='adc', smooth=False):
        """Used too run registration in one-shot using pre-set values"""
        reference = self.volumes[reference_name]
        for volume in self.volumes.values():
            if volume is not reference:
                volume.registration(reference=reference, smooth=smooth)

    def compile_volumes(self):
        for volume in self.volumes.values():
            volume.compile_volume_from_slices()

    def write_to_nifti(self):
        for volume in self.volumes.values():
            volume.write_to_nifti()

    def write_to_dicom(self, **modified_tags):
        for volume in self.volumes.values():
            volume.write_to_dicom(**modified_tags)

    def open_in_itk_snap(self):
        # self.write_to_nifti()
        FNULL = open(os.devnull, 'w')
        path = os.path.join(self.sup_folder, 'output/nifti/')
        paths = [path + volume.name + '.nii.gz' for volume in self.volumes.values()]
        _ = subprocess.run(["itksnap", "-g", paths[0], "-o", *paths[1:]],
                                 stdout=FNULL, stderr=subprocess.STDOUT)

    def display_slice_locations(self):
        """Create 4x1 subplot array and populate axis with patch collection of rectangles representing slices """
        num_cols, num_rows = len(self.volumes), 1
        fig, axs = plt.subplots(num_rows, num_cols, figsize=(12, 12), sharey=True)
        fig.set_dpi(1000)
        for volume, ax in zip(self.volumes.values(), axs.flatten()):
            volume.populate_ax_with_slice_locations(ax)

        # for ax in axs.flatten():
        #     if not ax.collections:
        #         ax.axis('off')

    #todo: improve this function later on, when time permits
    def resample_volumes_to_match(self):
        # todo: danger here is that recompiling volume will over-write these changes, so need to write function that
        # compiles slices from volume after this operation has been performed.
        sizes = []
        spacings = []
        origins = []
        for volume in self.volumes.values():
            if volume.image_volume is None:
                volume.compile_volume_from_slices()
            sizes.append(volume.image_volume.GetSize())
            spacings.append(volume.image_volume.GetSpacing())
            origins.append(volume.image_volume.GetOrigin())

        if len({len(set(sizes)), len(set(spacings)), len(set(origins))}) > 1:
            raise ValueError("Volumes do not have same sampling!")
        else:
            print('All volumes in volume collection have same sampling')

    def resample_slices_to_common_origin(self):
        for volume in self.volumes.values():
            volume.resample_slices_to_common_origin()

    def reformat_to_axial(self):
        for volume in self.volumes.values():
            volume.reformat_to_axial()

    def stitch_coronal_slices(self):
        for volume in self.volumes.values():
            volume.stitch_coronal_slices()

    def info(self):
        for volume in self.volumes.values():
            volume.info()
            print('\n')


class Volume:
    def __init__(self, parent, name, dcm_header):
        self.vol_collection = parent
        self.name = name
        self.slices = []
        self.dcm_header = dcm_header
        self.dcm_reader = None
        self.orientation = None
        self.check_direction()
        self.slice_thickness = float(dcm_header.SliceThickness)
        self.image_volume = None
        self.registration = None
        # todo: going to need to think hard about how coronal data will be managed

    def check_direction(self):
        # todo: this needs to be changed for coronal data and it reformatted to axial
        iop = self.dcm_header.ImageOrientationPatient
        if set(abs(i) for i in iop) != {0, 1}:
            raise ValueError("Non-orthogonal Volume")
        if iop == [1, 0, 0, 0, 1, 0]:
            self.orientation = 'tra'
        elif iop == [1, 0, 0, 0, 0, -1]:
            self.orientation = 'cor'

    def add_slice(self, dcm_path, dcm_header):
        """Add new Slice object to Volume slices list"""
        slice_location = float(dcm_header.SliceLocation)
        self.slices.append(Slice(self, dcm_path, slice_location))

    def sort_slice_order(self):
        """Sort slices in descending order of slice location - superior to inferior for head first scan"""
        self.slices.sort(key=lambda s: s.slice_location, reverse=True)

    def calculate_slice_intervals(self):
        """Calculate intervals between ordered slices"""
        self.sort_slice_order()
        for i in range(len(self)-1):
            interval = self.slices[i+1].slice_location - self.slices[i].slice_location
            self.slices[i].slice_interval = round(abs(interval), 2)

    def info(self, display_order=False):
        print('-' * 5, self.name, 'volume', '-' * 5)
        print(f'{len(self)} slices')
        print(f'Orientation: {self.orientation}')
        x = round(self.slices[0].image.GetOrigin()[0], 2)
        y = round(self.slices[0].image.GetOrigin()[1], 2)
        z = round(self.slices[-1].slice_location, 2)  # z-origin used to be defined as slices[0].slice_location
        print(f'Origin (x,y,z) = ({x}, {y}, {z})')
        x = self.slices[0].image.GetSize()[0]
        y = self.slices[0].image.GetSize()[1]
        z = len(self)
        print(f'Size (x,y,z) = ({x}, {y}, {z})')
        x = round(self.slices[0].image.GetSpacing()[0], 2)
        y = round(self.slices[0].image.GetSpacing()[1], 2)
        z = round(self.slice_thickness, 2)
        print(f'Spacing (x,y,z) = ({x}, {y}, {z})')
        print('Slice Information:')
        intervals = [s.slice_interval for s in self.slices if s.slice_interval is not None]
        counts = Counter(intervals)
        header = 'Interval \t| Count \t| Description'
        print(header)
        print('-' * (len(header) + 13))
        for interval, count in counts.items():
            if interval > self.slice_thickness:
                print(colored(f'{interval} \t\t| {count} \t\t| Underlapping', 'red'))
            elif interval == self.slice_thickness:
                print(colored(f'{interval} \t\t| {count} \t\t| Contiguous', 'green'))
            elif self.slice_thickness > interval > 0:
                print(colored(f'{interval} \t\t| {count} \t\t| Overlapping', 'yellow'))
            elif interval == 0:
                print(colored(f'{interval} \t\t| {count} \t\t| Duplicated', 'blue'))
        if display_order:
            print('in order:')
            print(list(run_length.encode(intervals)))

    def remove_duplicated_slices(self, print_results=True):
        """Remove slices with interval (distance to next slice) 0"""
        # in-place object in list deletion taken from:
        # https://stackoverflow.com/questions/8312829/how-to-remove-item-from-a-python-list-in-a-loop
        # todo: need to edit code so that it can handle when there are no duplicates

        self.calculate_slice_intervals()

        selectors = [True for s in self.slices]
        for i in range(len(self.slices) - 1):
            if self.slices[i].slice_interval == 0:
                total = sitk.GetArrayFromImage(self.slices[i].image).sum()
                total_next = sitk.GetArrayFromImage(self.slices[i + 1].image).sum()
                if total < total_next:
                    selectors[i] = False
                else:
                    selectors[i + 1] = False

        num_before = len(self)
        self.slices = list(compress(self.slices, selectors))
        num_after = len(self)

        self.calculate_slice_intervals()

        if print_results:
            print('{} duplicated slices removed from {}'.format(num_before - num_after, self.name))

    def find_contiguous_block(self, print_results=True):
        """Find and label the largest consecutive group of contiguous slices and return indices """
        self.calculate_slice_intervals()
        # create list of slice intervals:
        intervals = [s.slice_interval for s in self.slices]
        # Run length encoding to group consecutive equal slice intervals in list of tuples: [(interval, count), ...]:
        groups = list(run_length.encode(intervals))
        # Keep groups where interval == slice thickness:
        # todo: should I be using isclose() here rather than == due to float?
        contiguous_groups = list(filter(lambda x: x[0] == self.slice_thickness, groups))
        # Find group tuple with largest count:
        largest_contiguous_group = max(contiguous_groups, key=lambda x: x[1])
        # Find index of that tuple in groups
        index_in_groups = groups.index(largest_contiguous_group)
        # Calculate index positions of start and end of that group in intervals list:
        start_idx = sum([x[1] for x in groups][:index_in_groups])
        end_idx = sum([x[1] for x in groups][:index_in_groups + 1])

        # for i in range(start_idx, end_idx + 1):
        #     self.slices[i].contiguous = True

        # Label contiguous slices, including those away from the main block:
        for s in self.slices:
            if round(s.slice_location - self.slices[start_idx].slice_location, 2) % self.slice_thickness == 0:
                s.contiguous = True

        if print_results:
            # todo: if all slices are contiguous then print that:
            start_location = self.slices[start_idx].slice_location
            end_location = self.slices[end_idx].slice_location
            print(f'Largest contiguous slice block, of length {end_idx-start_idx + 1}, found at:')
            print('Slice {a} at location {b}mm ---> slice {c} at location {d}mm'.format(a=start_idx,
                                                                                        b=round(start_location, 2),
                                                                                        c=end_idx,
                                                                                        d=round(end_location, 2)))
        return start_idx, end_idx

    def correct_slice_contiguity(self, print_results=True):
        # todo: could rename this to resample to common grid?
        """1. Remove duplicated slices
           2. Find and label largest contiguous group to minimise resampling
           3. Working from either end of that group create new blank slices at correct slice location
              re-order slices
           4. Calculate pixel values for new slices
           5. Remove old non-contiguous slices """

        if print_results:
            print('-'*5, self.name, 'volume', '-'*5)
        self.remove_duplicated_slices(print_results)

        start_idx, end_idx = self.find_contiguous_block(print_results)  # start and end idx of largest contiguous block
        start_location = self.slices[start_idx].slice_location  # start location of largest contiguous block
        end_location = self.slices[end_idx].slice_location  # end location of largest contiguous block

        first_slice_location = self.slices[0].slice_location  # location of first slice in volume
        last_slice_location = self.slices[-1].slice_location  # location of last slice in volume

        # instantiate new contiguous slices
        num_new_slices = 0
        slice_locs = [round(s.slice_location, 2) for s in self.slices]
        for slice_loc in np.arange(start_location + self.slice_thickness, first_slice_location, self.slice_thickness):
            if round(slice_loc, 2) not in slice_locs:
                self.slices.append(Slice(self, dcm_path=None, slice_location=slice_loc, contiguous=True))
                num_new_slices += 1

        for slice_loc in np.arange(end_location - self.slice_thickness, last_slice_location, -self.slice_thickness):
            if round(slice_loc, 2) not in slice_locs:
                self.slices.append(Slice(self, dcm_path=None, slice_location=slice_loc, contiguous=True))
                num_new_slices += 1

        self.sort_slice_order()
        self.calculate_empty_slices()

        selectors = (s.contiguous is True for s in self.slices)
        self.slices = list(compress(self.slices, selectors))

        if print_results:
            print(f'{num_new_slices} slices resampled (linear interpolation) \n')

        self.calculate_slice_intervals()

    def calculate_empty_slices(self):
        for i, s in enumerate(self.slices):
            if s.image is None and s.contiguous is True:
                s_prev = self.get_next_complete_slice(i, reverse=True)
                s_next = self.get_next_complete_slice(i)
                sl_prev, sl, sl_next = s_prev.slice_location, s.slice_location, s_next.slice_location
                pa_prev = sitk.GetArrayFromImage(s_prev.image)
                pa_next = sitk.GetArrayFromImage(s_next.image)
                x1, x2 = abs(sl - sl_prev), abs(sl_next - sl)
                r1, r2 = (x1 / (x1 + x2)), (x2 / (x1 + x2))
                pa = r1 * pa_prev + r2 * pa_next
                pa = pa.astype('uint16')
                s.image = sitk.GetImageFromArray(pa)
                s.image.CopyInformation(s_prev.image)
                # origin_prev = s.image.GetOrigin()
                # origin = origin_prev[0], origin_prev[1], s.slice_location
                # s.image.SetOrigin(origin)

    def get_next_complete_slice(self, slice_idx, reverse=False):
        while True:
            slice_idx = slice_idx - 1 if reverse else slice_idx + 1
            if self.slices[slice_idx].image is not None:
                break
        return self.slices[slice_idx]

    def compile_volume_from_slices(self):
        # todo: add warning if slice interval is non constant - can still compile though
        if len(Counter(s.image.GetOrigin() for s in self.slices)) > 1:
            self.resample_slices_to_common_origin()

        images = [s.image for s in self.slices]
        images.reverse()  # otherwise nifti volumes come out upside down in ITK-SNAP todo: need to look into this
        origin = self.slices[-1].slice_location
        spacing = self.slice_thickness
        self.image_volume = sitk.JoinSeries(images, origin, spacing)

        if self.orientation == 'cor':  # bit of a hack fix for coronal data
            self.image_volume.SetDirection((1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0))
            self.image_volume.SetOrigin((self.image_volume.GetOrigin()[0], self.image_volume.GetOrigin()[2],
                                         self.image_volume.GetOrigin()[1]))

    # todo: write function to take self.image_volume and turn it into slices
    def compile_slices_from_volume(self, orientation='tra'):
        
        pass

    def write_to_nifti(self):
        if self.image_volume is None:
            self.compile_volume_from_slices()

        output_folder = os.path.join(self.vol_collection.sup_folder, 'output')

        try:
            os.mkdir(output_folder)
        except FileExistsError:
            pass

        output_folder_nifti = os.path.join(output_folder, 'nifti')

        try:
            os.mkdir(output_folder_nifti)  # todo: want to allow output path to be set globally for niftis
        except FileExistsError:
            pass

        writer = sitk.ImageFileWriter()
        writer.SetImageIO('NiftiImageIO')
        path = os.path.join(output_folder_nifti, self.name) + '.nii.gz'
        writer.SetFileName(path)
        writer.Execute(self.image_volume)

        print(f'{self.name} saved as NIfTI file')

    def open_in_itk_snap(self):
        self.write_to_nifti()
        FNULL = open(os.devnull, 'w')

        output_folder = os.path.join(self.vol_collection.sup_folder, 'output')
        output_folder_nifti = os.path.join(output_folder, 'nifti')

        path = os.path.join(output_folder_nifti, self.name) + '.nii.gz'
        _ = subprocess.run(["itksnap", "-g", path], stdout=FNULL, stderr=subprocess.STDOUT)

    def write_to_dicom(self, **modified_tags):
        write_dcm_series(self, path=self.vol_collection.sup_folder, **modified_tags)

    def __len__(self):
        return len(self.slices)

    def display_slice_locations(self):
        fig = plt.figure(figsize=(3, 12), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        self.populate_ax_with_slice_locations(ax)

    def populate_ax_with_slice_locations(self, ax, padding=20):
        self.sort_slice_order()
        slices = [s.get_rectangle_repr() for s in self.slices]
        ax.add_collection(PatchCollection(slices, alpha=0.5)) # , cmap=plt.cm.hsv
        ax.set_xlim([-padding, slices[0].get_width()+padding])
        ax.set_ylim([slices[-1].get_y() - padding, slices[0].get_y() + padding])
        # extent = (0, size_x * spacing_x, size_y * spacing_y, 0)
        ax.set_title(self.name)
        ax.set_aspect('equal')
        return ax

    def set_registration_as_translation(self):
        self.registration = VolumeSliceTranslation(parent=self)
        # todo: is it necessary to do both of these?
        for s in self.slices:
            s.registration = SliceTranslation(parent_slice=s)

    def resample_slices_to_common_origin(self):
        """For volumes that have multiple origins, resample to most common origin for each slice """
        origin_counts = Counter(s.image.GetOrigin() for s in self.slices)
        most_common_origin = origin_counts.most_common(1)[0][0]

        ref_image = next((s.image for s in self.slices if s.image.GetOrigin() == most_common_origin), None)

        for s in self.slices:
            resampling_filter = sitk.ResampleImageFilter()
            resampling_filter.SetInterpolator(sitk.sitkLinear)
            resampling_filter.SetDefaultPixelValue(0)
            resampling_filter.SetReferenceImage(ref_image)
            resampling_filter.SetTransform(sitk.Transform())
            s.image = resampling_filter.Execute(s.image)

    def reformat_to_axial(self, print_results=True):
        if self.orientation == 'tra':
            raise ValueError("Volume is already in transaxial orientation!")

        if self.image_volume is None:
            self.compile_volume_from_slices()

        print(f'------- Reformating {self.name} -------')
        self.image_volume = coronal_tools.reformat_to_axial(self.image_volume)

    def stitch_coronal_slices(self):
        if self.orientation == 'tra':
            raise ValueError("Volume is in transaxial orientation!")

        num_stations = len(set(s.image.GetOrigin()[1] for s in self.slices))
        c = cycle(self.slices)
        stitched_slices = []
        for i in range(int(len(self) / num_stations)):
            unstitched_slices = list(islice(c, num_stations))
            unstitched_images = [s.image for s in unstitched_slices]
            slice_location = unstitched_slices[0].slice_location
            stitched_image = coronal_tools.stitch(unstitched_images, slice_location)
            stitched_slice = Slice(parent_volume=self, slice_location=slice_location)
            stitched_slice.image = stitched_image
            stitched_slices.append(stitched_slice)

        self.slices = stitched_slices
        self.sort_slice_order()
        self.calculate_slice_intervals()


class Slice:
    def __init__(self, parent_volume=None, dcm_path=None, slice_location=None, contiguous=False):
        self.volume = parent_volume
        self.dcm_path = dcm_path
        self.slice_location = slice_location
        self.slice_interval = None
        self.image = None
        self.contiguous = contiguous
        self.registration = None
        self.load_sitk_image()

    def load_sitk_image(self):
        if self.dcm_path:  # if there is a DICOM file to load
            reader = sitk.ImageFileReader()
            reader.SetImageIO("GDCMImageIO")
            reader.SetOutputPixelType(sitk.sitkUInt16)
            reader.SetFileName(self.dcm_path)
            vol = reader.Execute()
            img = sitk.Extract(vol, (vol.GetWidth(), vol.GetHeight(), 0), (0, 0, 0))  # get 2D image from 3D image

            if vol.GetDirection() == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
                pass

            if vol.GetDirection() == (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0):
                img.SetOrigin((vol.GetOrigin()[0], vol.GetOrigin()[2]))
                # hack fix for coronal data such that the x, z location of the upper left hand
                # part of the 2D image is stored as an x, y coordinate

            # https://discourse.itk.org/t/set-photometric-interpretation-for-gdcmimageio-as-monochrome2-in-simpleitk/3073/6
            photometric_interpretation = reader.GetMetaData('0028|0004').strip()
            if photometric_interpretation == 'MONOCHROME1':
                min_max_filter = sitk.MinimumMaximumImageFilter()
                min_max_filter.Execute(img)
                img = sitk.InvertIntensity(img, maximum=min_max_filter.GetMaximum())

            self.image = img

            if self.volume and not self.volume.dcm_reader:
                self.volume.dcm_reader = reader  # keep one reader for volume to make writing DICOMs easy

    def display_slice(self, grid=True, text=True):
        fig = plt.figure(figsize=(4, 4), dpi=100)
        ax = fig.add_axes([1, 1, 1, 1])
        self.populate_ax_with_slice_image(ax, grid, text)

    def populate_ax_with_slice_image(self, ax, grid=True, text=True):
        image = self.image
        spacing_x, spacing_y = image.GetSpacing()
        size_x, size_y = image.GetSize()
        extent = (0, size_x * spacing_x, size_y * spacing_y, 0)

        ax.grid(color='r', linestyle='--', linewidth=0.5) if grid else ax.grid(b=False)

        if self.volume:
            ax.text(0.12, 0.92, self.volume.name, color='g', size=20, weight='heavy', bbox=dict(facecolor='black'),
                    ha='center', va='center', transform=ax.transAxes, visible=text)
        if self.slice_location:
            z_loc = f'z = {round(self.slice_location, 2)} mm'
            ax.text(0.75, 0.05, z_loc, color='b', size=15, weight='heavy', bbox=dict(facecolor='black'),
                    ha='center', va='center', transform=ax.transAxes, visible=text)

        nda = sitk.GetArrayViewFromImage(image)
        t = ax.imshow(nda, extent=extent, interpolation=None, origin='upper', cmap='Greys_r',
                      vmin=nda.min(), vmax=nda.max())
        return t  # todo: not sure this return actually does anything

    def get_rectangle_repr(self):
        slice_width = self.image.GetWidth() * self.image.GetSpacing()[0]
        xy = (0, self.slice_location - self.volume.slice_thickness)  # bottom left of rectangle
        return Rectangle(xy, width=slice_width, height=self.volume.slice_thickness)
        # todo: can make them different colors based on series number? r.set_color


def match_fovs_between_collections(*collections, print_results=True):
    img_vols = []
    for col in collections:
        for volume in col.volumes.values():
            if volume.image_volume is None:
                volume.compile_volume_from_slices()
            img_vols.append(volume.image_volume)

    # Get innermost origin and innermost extent (smallest common volume)
    if all(set(img_vol.GetDirection()) != {0, 1} for img_vol in img_vols):
        raise ValueError("Non-orthogonal Volume Found")
    origin = tuple(np.max([img_vol.GetOrigin()[i] for img_vol in img_vols]) for i in range(3))
    extent = tuple(np.min([img_vol.GetSize()[i] * img_vol.GetSpacing()[i] for img_vol in img_vols]) for i in range(3))

    for col in collections:
        for volume in col.volumes.values():
            img_vol = volume.image_volume
            spacing = img_vol.GetSpacing()
            new_size = tuple(int(round(extent / spacing, 0)) for extent, spacing in zip(extent, spacing))

            resample = sitk.ResampleImageFilter()
            resample.SetOutputSpacing(spacing)
            resample.SetSize(new_size)
            resample.SetOutputDirection(img_vol.GetDirection())
            resample.SetOutputOrigin(origin)
            resample.SetTransform(sitk.Transform())
            resample.SetDefaultPixelValue(0)
            resample.SetInterpolator(sitk.sitkLinear)

            # quick function for rounding tuples:
            round_tuple = lambda t, n=2: tuple(round(e, n) for e in t)

            # record these values before execution for comparison
            old_origin = round_tuple(img_vol.GetOrigin())
            old_extent = round_tuple(tuple(sp * si for sp, si in zip(img_vol.GetSpacing(), img_vol.GetSize())))
            old_size = round_tuple(img_vol.GetSize())

            volume.image_volume = resample.Execute(img_vol)

            new_origin = round_tuple(volume.image_volume.GetOrigin())  # todo: set as vol.image_vol to really check
            new_extent = round_tuple(tuple(sp * si for sp, si in zip(volume.image_volume.GetSpacing(),
                                                                     volume.image_volume.GetSize())))
            new_size = round_tuple(volume.image_volume.GetSize())

            if print_results:
                print(f'------- Resampling {volume.name} -------')
                print('Origin:', old_origin, '---->', new_origin)
                print('Extent:', old_extent, '---->', new_extent)
                print('Size:', old_size, '---->', new_size, '\n')






