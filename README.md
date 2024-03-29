# koreto
Repo collecting some common tools for pytorch and numpy. Changed the name to これと, kore to, "this and..." to reflect the incomplete nature of this project.


### general
`ObjDict()`         class, thin wrap on Dict for accessing keys as object attributes, with rw to yaml and json <br>
`sround()`          'smart round', to highest digits, inputs float or list, tuple, ndarray<br>
`filter_kwargs`     filters kwarg dict to pass to callable
`deepclone()`       similar to deepcopy, clone and detach torch tensors to cpu <br>
`get_files()`       get files from folder, optionally recursive, sorted <br>
`randitem()`        get random item from a sequence <br>
`get_images()`      get images, shortcut to get files with image formats accessible from PIL <br>
`hash_file()`       returns a dictionary with md5 hash of date and file content  <br>


### logging
`Plog()`            class, running log to collect to pandas csv <br>
`Col()`             class, color print codes<br>

### memory
`@memory_profiler`  decorator class using digest of nvml, torch.profiler and torch.cuda.memory_stats()
`GPUse()`           class, thin wrap around nvidia-smi <br>
`CPUse()`           class, thin wrap around psutil.virtualmemory <br>
`ObjTrace()`        class, GPU and CPU collection based on ObjDict <br>

### training 
`Schedule()`        scheduler class, linear, exponential, with noisy periodic functions <br>

### grids
`mgrid()`           fast n dim meshgrid with layout and column order options (torch | numpy) <br>
`mgrid_pos()`       grid indices (torch | numpy) <br>

### random sampling
`unique_randint()`  non repeating random ints (torch | numpy) <br>

### pytorch sanity
`@contiguous(msg)`  decorator that ensure contiguous tensor or tensor tuple outputs, msg optional <br>

### pytorch general
`unsqueeze_to`      unsqueeze as many steps as required to match tensor.ndim or int
`extend_to`         add trailing dimensions for as many steps as required to match tensor.ndim or int

### cameras
*pytorch only, partial port from nerfies jax code* <br>
`pixels_to_rays()`  pixels to rays given camera intrinsics <br>
`points_to_pixels()`pixels to rays given camera intrinsics<br>
`rotate_rays()`     rotate rays by transform<br>
`Camera()`          camera class, io, intrinsics, extrinsics<br>

### info
*pytorch only,*<br>
`esd(tensor)`                     Empirical Spectral Distribution of a tensor (binned eigen values)<br>
`get_esds(model, name='weight')`  given a model returns list of (name, ESD, shape)<br>
`plot_esds(model, name='weight')` given a model, plots ESDs of weight parameters<br>
`pca`                             Principal Component Analysis of tensor<br>
`kde`                             Gaussian Kernel Density Estimation of tensor<br>
`get_conv_zero_kernels(nn.Module)`Identifies conv kernels where all weights are below threshold <br>
