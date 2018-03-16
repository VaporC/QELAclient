'''
extends json.dumps to also save 
'''
__name__ = 'json'
from json import *
from json import decoder
from json import dumps as _dumps
import numpy as np


class NumpyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


def dumps(*args, **kwargs):
    return _dumps(*args, **kwargs, cls=NumpyEncoder)


if __name__ == '__main__':

    a = np.array([1, 2, 3])
    out = dumps({'aa': [2, (2, 3, 4), a], 'bb': [2]})

    assert str(out) == '''{"aa": [2, [2, 3, 4], [1, 2, 3]], "bb": [2]}'''
