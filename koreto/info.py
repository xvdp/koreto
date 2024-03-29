""" empirical spectral density, gaussian kernel density estimation
measures of structure of information
"""
from typing import Union, Any, Optional
import math
import numpy as np
import scipy
import matplotlib.pyplot as plt
import torch
from torch import nn, Tensor
# pylint: disable=no-member
# pylint: disable=not-callable

def tensor_flat2(x: Tensor, axis: int = 0, num: int = 1) -> Tensor:
    """ Flattens ND, Tensors to 2D,
    Return 2d tensor (num axis kept flattened, flattened dims)
    Args
        x               (Tensor) Nd
        num_fixed_axis  (int [1]), defaults to batch dimension, in (0, x.ndim)
        axis            (int [0]), defaults to batch dimension, in (0, x.ndim)
            supports negative indexing: -1 == x.ndim -1
    Examples
    # x: shape N,C,H,W
    >>> x = tensor_flat(x, axis=0, num=0) -> (1, N*C*H*W) 
    >>> x = tensor_flat(x, axis=0, num=1) -> (N, C*H*W) # DEFAULT
    >>> x = tensor_flat(x, axis=1, num=1) -> (C, N*H*W) 
    >>> x = tensor_flat(x, axis=0, num=2) -> (N*C, H*W) 
    >>> x = tensor_flat(x, axis=-1, num=1) -> (W, N*C*H)
    >>> x = tensor_flat(x, axis=-1, num=2) -> (W*N, C*H)
    >>> x = tensor_flat(x, axis=<any>, num=x.ndim) -> (N*C*H*W, 1)
    """
    if x.ndim == 1:
        return x.reshape(1, -1)
    axis = axis % x.ndim
    num = np.clip(num, 0, x.ndim)
    shape = tuple(np.concatenate((np.mod(list(range(axis, axis+num)), x.ndim),
                                  np.mod(list(range(axis+num, axis+x.ndim)),
                                         x.ndim))).astype(np.int64))
    x = x.permute(shape).contiguous()
    return x.reshape(np.prod(x.shape[:num], dtype=np.int64), np.prod(x.shape[num:], dtype=np.int64))


def entropy(x: Tensor,
            num_fixed_axes: int = 0,
            low: float = 0,
            high: float = 0,
            base: Optional[float] = 2.,
            axis: int = 0) -> Union[Tensor, tuple]:
    """ Returns data entropy and entropy per item if num_fixed_axis > 0
    -> (entropy, entropies) or > entrooy
    where entropies is the entropy of each batch element ( if num_fixed_axis == 1)
    Args
        x           tensor
        num_fixed_axes (int [0]) in {0, tensor.ndim}, 0 returns only total entropy
        low, high, same as in torch.histc(min, max), if both are zero, are ignored.
        base        (float [2]) number of bits, None uses number of items
        axis    int [0] if num_fixed_axes >= 1, defaults to measure batch dimesnion, axis 0
            when x: N,C,H,W or channel with x: C,H,W
    Example:
    >>> tensor=torch.randn(2,3,25,25)
    >>> Hs,Ht = entropy(torch.randn(2,3,25,25), num_fixed_axes=2)
    # Out[*] (tensor(0.8872), tensor([0.8709, 0.8681, 0.8771, 0.8620, 0.8698, 0.8617]))
    # total entropy, and entropy of each of (6) 25x25 datapoints
    """
    if not x.dtype.is_floating_point:
        _dtype = torch.float64 if x.itemsize == 8 else torch.float32
        x = x.to(dtype=_dtype)

    out_h = _entropy(x, low=low, high=high, base=base)
    if num_fixed_axes == 0:
        return out_h

    x = tensor_flat2(x, axis=axis, num=num_fixed_axes)
    # compute entropy for each element
    sub_h = torch.stack([_entropy(_t, low=low, high=high, base=base) for _t in x], dim=0)
    return out_h, sub_h


def _entropy(x: Tensor, low: float, high: float, base: Optional[float] = 2.) -> Tensor:
    """ entropy of a tensor, number of bit it takes to encode each pixel
        Σ(-p.log2(p))
    Args
        x           tensor
        low, high   float if 0 & 0 are ignored, otherwise compute entrpy within range
        base        (int [2]) log base, number of bits, None: number of events
    """
    x = x.reshape(-1)
    p = torch.histc(x, len(x), low, high)/len(x)
    p = p[p > 0]
    base = len(x) if base is None else base
    return torch.sum(-1.*p*torch.log(p).div(np.log(base)))
    # return torch.sum(-1*_th*torch.log(_th)).div(math.log(_n))


def eigen_vals_low_rank(x: Tensor, num_fixed_axes: int = 1, components: int = 64) -> Tensor:
    """ Eigen Values of Vectors using fast SVD per batch element
    Args
        x   Tensor
        num_fixed_axis  (int [1]) by default compute eigen values per Batch element
        components      (int [64])  svd compression
    """
    x = tensor_flat2(x, num=num_fixed_axes)
    components = min(components, len(x))
    _u, _s, _v = torch.svd_lowrank(x, q=components)
    return _s**2 / len(_s)


def eigen_vals(x, num_fixed_axes: int = 1) -> Tensor:
    """ Eigen Values of Vectors using full SVD
        x   Tensor
        num_fixed_axis  (int [1]) by default compute eigen values per Batch element
    """
    x = tensor_flat2(x, num=num_fixed_axes)
    _u, _s, _v = torch.svd(x.T)
    return _s**2 / len(_s)


def esd(data, num_fixed_axes=1, norm=False, low_rank=False):
    """ Empirical Spectral Distribution
        histogram density
        eigen_vals = single_vals^2/len(single_vals)
        ESD = hist(eigen_vals)
    Args
        data,   tensor
        num_fixed_axes  int[1], division of (samples,data)
    """
    if not low_rank:
        eigen_data = eigen_vals(data, num_fixed_axes=num_fixed_axes)
    else:
        components = 64 if not isinstance(low_rank, int) else low_rank
        eigen_vals_low_rank(data, num_fixed_axes=num_fixed_axes, components=components)
    return _esd(eigen_data, norm=norm)

def _esd(evals, norm=False):
    _evals = evals.cpu().clone().detach()
    bins = max(len(_evals)//8, min(16, len(_evals)))
    _y = torch.histc(_evals, bins=bins)
    _step = (_evals.max() - _evals.min())/bins
    _x = torch.arange(_evals.min(), _evals.max(), _step)
    _x += abs(_x[1] - _x[0])/2
    if norm:
        _y /= _y.max()
    else:
        _y = _y.clone().detach().numpy().astype(int)
    return _x[:len(_y)], _y


def kde(data, num_fixed_axes=1, norm=False):
    """ Gaussian Kernel Density Estimation
    Args
        data,   tensor
        num_fixed_axes  int[1], division of (samples,data)
    """
    eigen_data = eigen_vals(data, num_fixed_axes=num_fixed_axes)
    return _kde(eigen_data, norm=norm)

def _kde(evals, norm=False):
    if torch.is_tensor(evals):
        evals = evals.cpu().clone().detach().numpy()
    kernel = scipy.stats.gaussian_kde(evals)
    _x = np.linspace(evals.min(), evals.max(), 100)
    _y = kernel(_x)
    if norm:
        _y /= _y.max()
    return _x, _y


def pca(data, components, method="full", q=None, verbose=False, normalize=False):
    """ Principal component Analysis: data projected on singular values of data
    Args
        data            tensor
        components      int, number of componenets returned
        method          str [full], {sparse, full}
        q               int [components] in {q <= components}
        normalize       bool [False] normalizes outputs to 1
    """
    _flat = data.view(len(data), -1).T
    if method == "full":
        _u, _s, _v = torch.svd(_flat)
    elif method == "sparse":
        q = min(q, components)
        _u, _s, _v = torch.svd_lowrank(_flat, q=q)
    else:
        assert NotImplementedError

    if verbose:
        print("U,S,V=torch.svd(x), USV[", tuple(_u.shape), tuple(_s.shape),
              tuple(_v.shape), "] input", tuple(_flat.shape))

    out = torch.matmul(_flat, _v[:, : components]).T.view(components, *data.shape[1:])
    if normalize:
        out.div_(torch.linalg.norm(out))
    return out


def get_layer_pca(model, layer=0, components=None):
    """ returns pca of layer weights
        Args
            model       (torch model)
            layer       (int[0]) layer by number
            components  (int[None]) if None: len(layer.weight)//2
    """
    modules = {k: dict(model.named_modules())[k] for k in dict(model.named_modules())
               if 'conv' in k or 'fc' in k}

    if isinstance(layer, int):
        layer = list(modules.keys())[layer]
    if isinstance(layer, str) and layer not in modules:
        print("layer <%s> not found"%layer)

    _weight = modules[layer].weight.cpu().clone().detach()
    if components is None:
        components = len(_weight)//2

    return pca(_weight, components=components)


def get_esds(model, min_param=0, max_param=None, name='weight'):
    params = [(n, p) for n,p in model.named_parameters() if name in n][min_param:max_param]
    esds = []
    for n,p in params:
        if torch.any(p):
            esds.append((n, esd(p.detach()), tuple(p.shape)))
        else:
            print(f'No ESD for layer {n}, all values = 0')
    return esds

def plot_esds(model, min_param=0, max_param=None, figsize=(20,20), name='weight'):
    """ plots a grid of empirical spectral distributions for models parameters
    """
    esds = get_esds(model, min_param, max_param, name)
    nparams = len(esds)
    if nparams:
        rows = (nparams)**(1/2)
        cols = math.ceil(rows)
        rows = int(rows)
        if rows*cols < nparams:
            rows += 1
        plt.figure(figsize=figsize)
        for i, n_e in enumerate(esds):
            _name, _esd, _shape = n_e
            plt.subplot(rows,cols,i+1)
            plt.plot(*_esd)
            plt.title(f'{_name}\n{_shape}')
            plt.grid()
        plt.tight_layout()
        plt.show()

def zero_kernels(x: torch.Tensor, threshold: float = 1e-5, name=None) -> tuple:
    """ returns ('n_dead_kernels', n_kernels)
    dead kernels are those where all weights are smaller than threshold
    Args
        x   torch.Tensor ndim 3,4,5
    """
    num_kernels = x.shape[0]*x.shape[1]
    out = ((x.view(num_kernels, -1).abs() > threshold).sum(dim=-1) == 0).sum().item(), num_kernels
    if name is not None:
        out = name, *out
    return out

def get_conv_zero_kernels(module: Union[nn.Module, nn.Conv1d, nn.Conv2d, nn.Conv3d],
                          threshold: float = 1e-5) -> Any:
    """ identifies kernels where all weights are below a threshold
    Args
        module:     torchTensor (in_channels, out_channels, ...)    -> tuple(dead, number)
                    nn.Conv<>d                                      -> tuple(dead, number)
                    nn.Module       -> tuple(name, dead, number) # only dead convs are shown
        threshold:  float [1e-5]
    """
    if isinstance(module, torch.Tensor) and module.ndim > 2:
        return zero_kernels(module, threshold=threshold)
    elif isinstance(module, (nn.Conv1d, nn.Conv2d, nn.Conv3d)):
        return zero_kernels(module.weight, threshold=threshold)
    elif isinstance(module, nn.Module):
        out = []
        for name, mod in module.named_modules():
            if isinstance(mod, (nn.Conv1d, nn.Conv2d, nn.Conv3d)):
                _bad = zero_kernels(mod.weight, threshold=threshold, name=name)
                if _bad[1]:
                    out.append(_bad)
        return out
    print(f"module {type(module)} expected in nn.Module or nn.Conv<>d")
    return None


def covariance(x: Tensor, y: Tensor) -> Tensor:
    """covariance matrix (x - μ) @ (y - μ) """
    return (x.sub(x.mean(dim=0)).t() @ y.sub(y.mean(dim=0)))/(len(x) - 1)


def mahalanobis(x: Tensor, y: Tensor) -> Tensor:
    """ Mahalanobis distance: distance between a point and a distribution
    multivariate generalization of square std score z = ( x - μ ) / σ
    stds between point and mean of distribution
    """
    return ((x - y) @ torch.inverse(covariance(x, y)) @ (x - y).t())#**(1/2)
