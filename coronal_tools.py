import SimpleITK as sitk
from functools import reduce


def reformat_to_axial(image_volume, print_results=True):
    spacing = (image_volume.GetSpacing()[0], image_volume.GetSpacing()[2],
               image_volume.GetSpacing()[1])
    size = (image_volume.GetSize()[0], image_volume.GetSize()[2], image_volume.GetSize()[1])
    direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

    origin = (image_volume.GetOrigin()[0], image_volume.GetOrigin()[1],
              image_volume.GetOrigin()[2] - image_volume.GetSpacing()[1] * image_volume.GetSize()[1])

    resample = sitk.ResampleImageFilter()
    resample.SetOutputSpacing(spacing)
    resample.SetSize(size)
    resample.SetOutputDirection(direction)
    resample.SetOutputOrigin(origin)
    resample.SetTransform(sitk.Transform())
    resample.SetDefaultPixelValue(0)
    resample.SetInterpolator(sitk.sitkLinear)

    # quick function for rounding tuples:
    round_tuple = lambda t, n=2: tuple(round(e, n) for e in t)

    # record these values before execution for comparison
    old_direction = image_volume.GetDirection()
    old_origin = round_tuple(image_volume.GetOrigin())
    old_spacing = round_tuple(image_volume.GetSpacing())
    old_size = image_volume.GetSize()

    image_volume = resample.Execute(image_volume)

    new_direction = image_volume.GetDirection()
    new_origin = round_tuple(image_volume.GetOrigin())
    new_spacing = round_tuple(image_volume.GetSpacing())
    new_size = image_volume.GetSize()

    if print_results:
        print('Direction:', old_direction, '---->', new_direction)
        print('Origin:', old_origin, '---->', new_origin)
        print('Spacing:', old_spacing, '---->', new_spacing)
        print('Size:', old_size, '---->', new_size, '\n')

    return image_volume


def stitch(unstitched_images: list, slice_location: float):
    # make the 2D "coronal" images 3D coronal images:
    images_3d = [get_3d_image(i, slice_location) for i in unstitched_images]

    # sort images in descending order of image z (in scanner coordinated) location:
    images_3d.sort(key=lambda i: i.GetOrigin()[2], reverse=True)

    # remove bottom overlapping region of each image:
    bottom_cropped_images = []
    for i in range(len(images_3d) - 1):
        size = (images_3d[i].GetOrigin()[2] - (images_3d[i + 1].GetOrigin()[2])) / images_3d[0].GetSpacing()[1]
        bottom_cropped_images.append(images_3d[i][:, :int(size) + 1, :])
    bottom_cropped_images.append(images_3d[-1])

    # remove top overlapping region from each image:
    top_cropped_images = [images_3d[0]]
    for i in range(1, len(images_3d)):
        size = images_3d[i].GetOrigin()[2] - (
                    images_3d[i - 1].GetOrigin()[2] - images_3d[i - 1].GetSize()[1] * images_3d[i - 1].GetSpacing()[1])
        size = size / images_3d[0].GetSpacing()[1]
        top_cropped_images.append(images_3d[i][:, int(size):, :])

    bottom_cropped_combined_image = combine_stations(bottom_cropped_images)
    top_cropped_combined_image = combine_stations(top_cropped_images)

    stitched_image = sitk.Add(bottom_cropped_combined_image, top_cropped_combined_image)/2

    # convert 3D image back to 2D image
    stitched_image_2d = sitk.Extract(stitched_image, (stitched_image.GetWidth(), stitched_image.GetHeight(), 0), (0, 0, 0))
    stitched_image_2d.SetOrigin((stitched_image.GetOrigin()[0], stitched_image.GetOrigin()[2]))

    return stitched_image_2d


def get_3d_image(image, slice_location):
    i3d = sitk.JoinSeries(image, slice_location, 1)
    origin = i3d.GetOrigin()
    i3d.SetOrigin((origin[0], origin[2], origin[1]))
    i3d.SetDirection((1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0))
    return i3d


def combine_stations(stations):
    """Resample each station to occupy same physical extent, then add volumes together"""
    stations.sort(key=lambda s: s.GetOrigin()[2], reverse=True)
    top = stations[0].GetOrigin()[2]
    bottom = stations[-1].GetOrigin()[2] - stations[-1].GetHeight() * stations[-1].GetSpacing()[1]
    height = (top - bottom) / stations[0].GetSpacing()[1]
    size_out = (stations[0].GetWidth(), int(height), 1)

    resampler = sitk.ResampleImageFilter()
    resampler.SetDefaultPixelValue(0)
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetOutputDirection((stations[0].GetDirection()))
    resampler.SetOutputOrigin(stations[0].GetOrigin())
    resampler.SetOutputSpacing(stations[0].GetSpacing())
    resampler.SetSize(size_out)

    volumes = [resampler.Execute(station) for station in stations]

    return reduce(sitk.Add, volumes)