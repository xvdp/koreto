""" @xvdp
simple loggers
* pands train logger
* plot train logger
"""
from typing import Any, Union
import sys
import datetime
from functools import wraps
import os
import os.path as osp
# import logging
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .utils import ObjDict


def contiguous(msg=None):
    """ test wrapper to ensure functions return contiguous tensors
    funcion output can be tensor, tuple or list of tensors
    Example
    >>> @contiguous("Permute Function"): 
    >>> def perm(x):
    >>>     return x.permute(3,1,0,2)
    >>> y = perm(torch.randn(3,2,12,22))
    []  make contiguous: Permute Function (22, 2, 3, 12)
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            res = f(*args, **kwargs)
            if torch.is_tensor(res) and not res.is_contiguous():
                res = res.contiguous()
                if msg is not None:
                    print(f"make contiguous: {msg} {tuple(res.shape)}")
            elif isinstance(res, (list, tuple)):
                _totuple = isinstance(res, tuple)
                res = list(res)
                for i in range(len(res)):
                    if torch.is_tensor(res[i]) and not res[i].is_contiguous():
                        res[i] = res[i].contiguous()
                        if msg is not None:
                            print(f"make contiguous[{i}]: {msg} {tuple(res[i].shape)}")
                if _totuple:
                    res = tuple(res)
            return res
        return wrapper
    return decorator

__all__ = ["sround", "Col", "PLog", "plotlog"]
def sround(x: Union[np.ndarray, float, list, tuple], digits: int=1) -> Any:
    """ 'smart' round to largest `digits` + 1
    Args
        x       (float, list, tuple, ndarray)
        digits  (int [1]) number of digits beyond highest
    Examples
    >>> sround(0.0212343, 2) # result 0.0212
    """

    if isinstance(x, (float, np.float64, np.float32)):
        safelog10 = lambda x: 0.0 if not x else np.log10(np.abs(x))
        _sround = lambda x, d=1: np.round(x, max((-np.floor(safelog10(x)).astype(int) + digits), 0))
        return _sround(x, digits)

    _as_tuple = False
    if isinstance(x, tuple):
        x = list(x)
        _as_tuple = True

    elif isinstance(x, (list, np.ndarray)):
        safelog10 = np.log10(np.abs(x))
        safelog10[np.abs(safelog10) == np.inf] = 0
        digits = np.maximum(-np.floor(safelog10).astype(int) + digits, 0)
        for i in range(len(x)):
            x[i] = np.round(x[i], digits[i])
    if _as_tuple:
        x = tuple(x)
    return x

class Col:
    """Color text
    """
    AU = '\033[0m'
    BB = '\033[94m\033[1m'
    GB = '\033[92m\033[1m'
    YB = '\033[93m\033[1m'
    RB = '\033[91m\033[1m'
    B = '\033[1m'
    @classmethod
    def print(cls, *args, color=None, **kwargs):
        """ print with "color" kwarg in ['blue', 'yellow', 'green' 'red']
        Example
            >>> from koreto import Col
            >>> print = Col().print
            >>> print("blue beard", color="blue")
            >>> print("standard", "colorless", "print")
        """
        if isinstance(color, str) and color[0].upper() in ['B','G','Y','R']:
            color = cls.__dict__[f"{color[0].upper()}B"]
            print(color, *args, cls.AU, **kwargs)
        else:
            print(*args, **kwargs)

# pylint: disable=unsubscriptable-object
# pylint: disable=no-member
class PLog:
    """ simple logger based in pandas
    Examples:
        log = PDLog(name)

        log.write(new_frame=True, Epoch=1, Iter=120, Loss=0.2, Acc=34)
    # or
        ...
        log.collect(new_frame=True, Epoch=1)
        log.collect(Iter=120)
        ...
        log.write() # write flushes .frame
    """
    def __init__(self, name, **kwargs):
        """ init reads csv if exists
        Args
            name     (str) csvfile
            iloc        (int[-1]) returns location as frame

        """
        self.name = osp.abspath(osp.expanduser(name))
        self.columns = None
        self.values = {}
        self.frame = {}
        self.len = 0

        self._log_interval = -1 if "log_interval" not in kwargs else kwargs["log_interval"]
        self._end = {"end":"\r"} if "end" not in kwargs else kwargs["end"]
        self._allow_missing = True if "allow_missing" not in kwargs else kwargs["allow_missing"]
        _iloc = -1 if "iloc" not in kwargs else kwargs["iloc"]
        init = True if 'init' not in kwargs else kwargs['init']
        self.read(iloc=_iloc, init=True)

    def read(self, iloc=-1, init=False):
        """
        Args
            iloc: fills self.values with dfl.iloc[iloc]
        """
        if not osp.isfile(self.name):
            os.makedirs(osp.split(self.name)[0], exist_ok=True)
            return None

        dfl = pd.read_csv(self.name)
        self.len = len(dfl)
        self.columns = list(dfl.columns)
        if len(dfl) > abs(iloc):
            self.values = {k: dfl[k].iloc[iloc] for k in dfl}
        if init:
            print(f"{self.name} found with len {self.len}\n{self.values}")
        return dfl

    def extend_keys(self, new_keys):
        """ adds new nan values for all rows of new keys
            overwrites stored file with new with kesy
        """
        dfl = self.read()
        for key in new_keys:
            if key not in dfl:
                dfl[key] = [np.nan for i in range(self.len)]
        self.columns = list(dfl.columns)
        dfl.to_csv(self.name, index=False)

    def _check_for_armaggeddon(self, **values):
        if self.columns is not None:
            _bad = [key for key in values if key not in self.columns]
            if self._allow_missing:
                self.extend_keys(_bad)
            else:
                assert not _bad, f"keys {_bad} not in columns {self.columns}, to add new key run, self.extend_keys({_bad})\n{Col.RB}{self.name}{Col.AU}"

    def collect(self, new_frame=False, **values):
        """collect key values to make dataframe
            values need to be key:[valyue]
        """
        if new_frame:
            self.frame = {}
        self._check_for_armaggeddon(**values)
        self.frame.update(**values)

    def _fix_columns(self):
        if self.columns is not None:
            _frame = {}
            for col in self.columns:
                if col not in self.frame:
                    assert self._allow_missing, "missing columns not allowed, pass [np.nan] to .write() or PLog(allow_missing=True)\n{Col.RB}{self.name}{Col.AU}"
                    _frame[col] = [np.nan]
                else:
                    _frame[col] = self.frame[col]
            self.frame = _frame
        else:
            self.columns = list(self.frame.keys())

        _lens = []
        for col in self.frame:
            if not isinstance(self.frame[col], list):
                self.frame[col] = [self.frame[col]]
            _len = len(self.frame[col])
            if _len not in _lens:
                _lens.append(_len)
        assert len(_lens) == 1, f"multiple column lengths found, {_lens}"

    def write(self, new_frame=False, printlog=True, **values):
        """collect key values to make dataframe
        """
        # build dict
        self.collect(new_frame=new_frame, **values)
        self._fix_columns()

        #assert check file has been created
        _check_creation = not osp.isfile(self.name)

        # write to csv
        dfl = pd.DataFrame(self.frame)
        dfl.to_csv(self.name, index=False, mode='a',
                   header=not osp.isfile(self.name))

        if _check_creation:
            assert osp.isfile(self.name), f"could not write file: {self.name}"
            print("logging file created:", self.name)

        # cleanup
        self.len += 1
        self.values = {**self.frame}
        self.frame = {}
        # log
        if not self.len%self._log_interval:
            if self.len == 1:
                print("\t".join(list(self.values.keys())))

            msg = [str(l[0]).replace("nan", "") for l in self.values.values()]
            if printlog:
                print("\t".join(msg), **self._end)


## TODO: move to PLOG, generalize, selfupdating
def plotlog(logname, column="Loss", figsize=(10,5), title=None, label=None, show=True, fro=0, to=None, ylog=True, ytick=None):
    """ plots column [Loss] from csv file
    if column 'Epoch' exists, ticks them
    Args
        logname     (str) csv. file
        column      (str ['Loss']) column to plot

    """

    assert osp.isfile(logname), f"log file {logname} not found"
    _maxtick = 21

    df = pd.read_csv(logname)
    assert column in df, f"column {column} not found in {list(df.columns)}"


    if figsize is not None:
        plt.figure(figsize=figsize)
    if title is not None:
        plt.title(title)
    y = np.asarray(df[column])
    if fro > 0 or to is not None:
        y = y[fro:to]

    kwargs = {}
    if label is not None:
        kwargs["label"] = label
    else:
        kwargs["label"] = column
    kwargs["label"] += f" {sround(y.min(), 2)}"
    kwargs["markevery"] = [np.argmin(y)]
    kwargs["marker"] = 'v'
    plt.plot(y, **kwargs)

    _info = f"Iters {len(df)}"
    if "Total_Time" in df:
        _info += f"\nTime {str(datetime.timedelta(seconds=int(df.Total_Time.iloc[-1])))}"

    folder = osp.split(logname)[0]
    ymls = [f.path for f in os.scandir(folder) if f.name.endswith(".yml")]
    if ymls:
        _meta = ObjDict()
        _meta.from_yaml(ymls[0])

        for k in ['lr', 'strategy']:
            if k in _meta:
                _info += f"\n{k}: {_meta[k]}"
        if "data_path" in _meta:
            _info += f"\n{osp.basename(_meta['data_path'])}"

    plt.scatter(0,0, s=1, label=_info)

    _ylabel = column
    if ylog:
        plt.yscale("log")
        _ylabel += " (log)"

    plt.grid()

    if "Epoch" in df:
        _epoch = df.Epoch
        if fro > 0 or to is not None:
            _epoch = _epoch.iloc[fro:to]

        epochs = np.unique(_epoch)
        print(epochs[0], epochs[-1])
        if len(epochs) > _maxtick:
            epochs = epochs[ np.linspace(0, epochs[-1]-epochs[0], _maxtick).astype(np.int64)]

        xlabels = [df.index[df.Epoch == e].values[0] for e in epochs]
        rotation = 0 if len(str(xlabels[-1])) < 3 else 45
        plt.xticks(xlabels, epochs+1-fro, rotation=rotation)
        plt.xlabel("Epochs")

    _yticks = [sround(y.min()), sround(y.max())]
    if ytick is not None:
        if isinstance(ytick, (int,float)):
            ytick = [ytick]
        _yticks += list(ytick)

    plt.yticks(_yticks, _yticks)
    plt.ylabel(_ylabel)

    if "label" in kwargs:
        plt.legend()

    if show:
        plt.show()

def _parseargs(args):
    name = "train.csv"
    col = "Loss"
    if not args:
        name = osp.join(os.getcwd(), name)
    else:
        if osp.isfile(args[0]):
            name = args[0]
        elif osp.isdir(args[0]):
            name = osp.join(args[0], name)
        if len(args) > 1:
            col = args[1]
    assert osp.isfile(name), f" file {name} not found"
    return name, col


# TODO , move all prints to absl.logging
# ##
# # logging based loggers
# #
# def logger(name, level=20, terminator="\n"):
#     """ level DEBUG = 10, defaults INFO 20, if None defaults to system WARNING

#     Example:
#         >>> from x_log import logger
#         >>> log = logger("FunctionLog")
#         >>> log[1].terminator = "\r"
#         >>> for i in range(20)"
#         >>>     log[0].info(f" iterating {i}")
#         >>> log[1].terminator = "\n"
#         >>> log[1].flush()
#     """
#     logger = logging.getLogger(name)
#     if level is not None:
#         logger.setLevel(level)
#     if not logger.handlers:
#         stream = logging.StreamHandler()
#         if level is not None:
#             stream.setLevel(level)
#         formatter = logging.Formatter('Siren: %(name)s - %(levelname)s - %(message)s')
#         stream.setFormatter(formatter)
#         logger.addHandler(stream)
#     else:
#         stream = logger.handlers[0]

#     stream.terminator = terminator

#     return logger, stream


if __name__ == "__main__":
    """ Example
    python x_log.py <csv_file | folder_containing_'train.csv'> <column_name default:[Loss]>
    python x_log.py /media/z/Malatesta/zXb/share/siren/eclipse_512_sub
    """
    plotlog(*_parseargs(sys.argv[1:]))
