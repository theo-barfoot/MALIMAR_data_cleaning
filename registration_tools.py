import SimpleITK as sitk
from tqdm import tqdm
import matplotlib.pyplot as plt
import time
from pwc_noise_removal import fit_steps
from notebook_interactions import RegistrationDashboard


class VolumeSliceTranslation:
    """Translate each slice in the v"""

    def __init__(self, parent):
        self.volume = parent
        self._reference_volume = None
        self.x = []
        self.y = []
        self.dashboard = RegistrationDashboard(self)

    @property
    def reference_volume(self):
        return self._reference_volume

    @reference_volume.setter
    def reference_volume(self, vol):
        # todo: could take in a string here instead? or maybe allow both?
        if len(vol) != len(self.volume):
            # todo: use different error type, a custom one maybe?
            raise ValueError("volume must have the same number of slices")
        self._reference_volume = vol
        for s, r in zip(self.volume.slices, self.reference_volume.slices):
            s.registration.fixed = r

    def calculate(self, log=False, external_bar=None):
        if not external_bar:
            print(f'Calculating translation transform of {self.volume.name} to {self.reference_volume.name}')
            time.sleep(.3)
            with tqdm(total=len(self.volume)) as pbar:
                for s, r in zip(self.volume.slices, self.reference_volume.slices):
                    s.registration.calculate_transformation(log=log)
                    pbar.set_postfix(refresh=True)
                    pbar.update()

        else:
            for s, r in zip(self.volume.slices, self.reference_volume.slices):
                s.registration.calculate_transformation(log=log)
                external_bar.value += 1

    def get(self):
        """Update Volume Slice Translation Object with Slice Translation Registration Transform (x,y) parameters"""
        try:
            self.x = [s.registration.transformation.GetParameters()[0] for s in self.volume.slices]
            self.y = [s.registration.transformation.GetParameters()[1] for s in self.volume.slices]
        except AttributeError:
            # just remains as zeros
            pass

    def set(self):
        for s, x, y in zip(self.volume.slices, self.x, self.y):
            s.registration.transformation.SetParameters([x, y])

    def smooth(self, *, k_x=15, k_y=15, st_x=98, st_y=98, msl_x=30, msl_y=30):
        self.get()
        self.x = fit_steps(self.x, k=k_x, threshold=st_x, min_step_length=msl_x)
        self.y = fit_steps(self.y, k=k_y, threshold=st_y, min_step_length=msl_y)

    def plot(self):
        fig = plt.figure(figsize=[15, 12])
        try:
            x = [s.registration.transformation.GetParameters()[0] for s in self.volume.slices]
            y = [s.registration.transformation.GetParameters()[1] for s in self.volume.slices]
        except AttributeError:
            x = [0] * len(self.volume)
            y = [0] * len(self.volume)
        plt.plot(x)
        plt.plot(y)
        if self.x and self.y:
            plt.plot(self.x)
            plt.plot(self.y)

        plt.title(self.volume.name)
        plt.legend(['x', 'y', 'x adjusted', 'y adjusted'])
        plt.xlabel('Slice Index')
        plt.ylabel('Translation (mm)')
        plt.show()

    def transform(self):
        if self.x and self.y:
            self.set()
        [s.registration.transform() for s in self.volume.slices]

    def __call__(self, *args, reference, log=True, smooth=False, **kwargs):
        # use this to set reference volume, calculate, smooth if specified and transform, passing kwargs through
        self.reference_volume = reference
        self.calculate(log=log)
        if smooth:
            self.smooth(**kwargs)
        self.plot()
        self.transform()


class SliceTranslation:
    def __init__(self, parent_slice):
        self._moving = parent_slice
        self._fixed = None
        self.registration_method = None
        self.resampling_filter = None
        self.transformation = None
        self.metric = []

    @property
    def fixed(self):
        return self._fixed

    @fixed.setter
    def fixed(self, f):
        if round(f.slice_location, 2) != round(self._moving.slice_location, 2):
            raise ValueError(f"Slices are not in the same z location, fixed = {f.slice_location}, "
                             f"moving = {self._moving.slice_location}")
        self._fixed = f

    def calculate_transformation(self, log=False):
        self.set_registration_parameters()
        moving = sitk.Cast(self._moving.image, sitk.sitkFloat32)
        fixed = sitk.Cast(self._fixed.image, sitk.sitkFloat32)
        moving = self.get_log_image(moving) if log else moving
        fixed = self.get_log_image(fixed) if log else fixed
        self.transformation = self.registration_method.Execute(fixed, moving)

    def set_registration_parameters(self):
        num_bins, sampling_percentage, sampling_seed = 50, 0.5, sitk.sitkWallClock
        learning_rate, min_step, num_iter = 1.0, .001, 200

        self.registration_method = sitk.ImageRegistrationMethod()
        self.registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        self.registration_method.SetMetricSamplingPercentage(sampling_percentage, sampling_seed)
        self.registration_method.SetMetricSamplingStrategy(self.registration_method.RANDOM)
        self.registration_method.SetOptimizerAsRegularStepGradientDescent(learning_rate, min_step, num_iter)
        self.registration_method.SetInitialTransform(sitk.TranslationTransform(2))
        self.registration_method.SetInterpolator(sitk.sitkLinear)
        self.registration_method.SetOptimizerScalesFromPhysicalShift()
        self.registration_method.AddCommand(sitk.sitkIterationEvent, lambda: self.record_metric())

        self.resampling_filter = sitk.ResampleImageFilter()
        self.resampling_filter.SetInterpolator(sitk.sitkLinear)
        self.resampling_filter.SetDefaultPixelValue(0)

    def set_transformation(self, x, y):
        self.transformation.SetParameters([x, y])

    def __call__(self, *args, **kwargs):
        pass

    def transform(self):
        if self.transformation is None:
            self.calculate_transformation()

        moving = sitk.Cast(self._moving.image, sitk.sitkFloat32)
        fixed = sitk.Cast(self._fixed.image, sitk.sitkFloat32)

        self.resampling_filter.SetReferenceImage(fixed)
        self.resampling_filter.SetTransform(self.transformation)
        self._moving.image = sitk.Cast(self.resampling_filter.Execute(moving), self._moving.image.GetPixelID())

    def record_metric(self):
        self.metric.append(self.registration_method.GetMetricValue())

    def plot_metric(self):
        # todo: should in theory have some way of preventing plotting if registration hasn't happened
        plt.plot(self.metric)
        plt.xlabel('Iteration Number')
        plt.ylabel('(-ve) Mutual Information')
        plt.show()

    @staticmethod
    def get_log_image(image):
        """Get Log of image, with zero value pixels set to one"""
        image = sitk.Add(image, sitk.Cast(image == 0, sitk.sitkFloat32))  # replace zeros with ones
        return sitk.Log(image)

    # todo: consider:
    # Setup for the multi-resolution framework:
    # self.registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[10, 2, 1])
    # self.registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    # self.registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()


