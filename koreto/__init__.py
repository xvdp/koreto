""" @xvdp """
import logging
from .version import __version__
WITH_TORCH = True
try:
    import torch
except:
    WITH_TORCH = False
    logging.warning("\033[93m\033[1mpytorch not found, only numpy functions loaded...\033[0m")

# pylint: disable=wrong-import-position
from .utils import DeepClone, deepclone, ObjDict, IPP, filter_kwargs
from .memory import ObjTrace, TraceMem, GPUse, CPUse, has_cuda
from .log import Col, PLog, sround, plotlog, contiguous
from .scheduling import Schedule
from .grids import  mgrid, mgrid_pos, np_mgrid, np_mgrid_pos
from .rndm import unique_randint, randint, randitem, rndlist
from .lut import apply_cmap
from .fileio import get_files, get_images, hash_file, hash_folder, get_last, clip_image
from .info import plot_esds, get_esds, get_layer_pca, pca, kde, esd
from .info import entropy, eigen_vals, eigen_vals_low_rank, covariance, mahalanobis
from .draw import draw_points, draw_axis, draw_vector
from .points import zscore_keep, irq_keep, sort_points_by_distance
from .transformations import fit_plane_normal, estimate_points_normals
from .bounds import factorial, log_factorial

if WITH_TORCH:
    from .camera import pixels_to_rays, rotate_rays, points_to_pixels, transform_points, Camera
    from .memory import memory_profiler
    from .tensor_utils import extend_to, unsqueeze_to
