'''
various image input/output routines
'''
import os
import cv2
import numpy as np


from imgProcessor.transformations import toNoUintArray, toUIntArray, toGray,\
    applyColorMap


# TODO:
# from imgProcessor import reader
# READERS = {'elbin':reader.elbin}


def _changeArrayDType(img, dtype, **kwargs):
    if dtype == 'noUint':
        return toNoUintArray(img)
    if issubclass(np.dtype(dtype).type, np.integer):
        return toUIntArray(img, dtype, **kwargs)
    return img.astype(dtype)


def getSupportedImageTypes():
    return ('bmp', 'dib',  # Windows bitmaps
            'jpg', 'jpeg', 'jpe', 'jp2'  # JPEG files
            'png',  # Portable Network Graphics
            'webp',
            'pbm', 'pgm', 'ppm',  # Portable image format
            'tiff', 'tif')


def imread(img, color=None, dtype=None):
    '''
    dtype = 'noUint', uint8, float, 'float', ...
    '''
    COLOR2CV = {'gray': cv2.IMREAD_GRAYSCALE,
                'all': cv2.IMREAD_COLOR,
                None: cv2.IMREAD_ANYCOLOR
                }
    c = COLOR2CV[color]
    if callable(img):
        img = img()
    elif isinstance(img, str):  # string_types):
        #         from_file = True
        #         try:
        #             ftype = img[img.find('.'):]
        #             img = READERS[ftype](img)[0]
        #         except KeyError:
        # open with openCV
        # grey - 8 bit
        if dtype in (None, "noUint") or np.dtype(dtype) != np.uint8:
            c |= cv2.IMREAD_ANYDEPTH
        img2 = cv2.imread(img, c)
        if img2 is None:
            if os.path.exists(img):
                raise IOError("image '%s' cannot be read" % img)
            raise IOError("image '%s' is not existing" % img)
        img = img2

    elif color == 'gray' and img.ndim == 3:  # multi channel img like rgb
        # cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) #cannot handle float64
        img = toGray(img)
    # transform array to uint8 array due to openCV restriction
    if dtype is not None:
        if isinstance(img, np.ndarray):
            img = _changeArrayDType(img, dtype, cutHigh=False)

    return img


def imwrite(path, img, dtype=None, cmap=None, **kwargs):
    '''
    accepted file types are...
        for 8 and 16 bit grayscale and RGB images:
            Windows bitmaps - *.bmp, *.dib
            JPEG files - *.jpeg, *.jpg, *.jpe
            JPEG 2000 files - *.jp2
            Portable Network Graphics - *.png
            WebP - *.webp
            Portable image format - *.pbm, *.pgm, *.ppm
            Sun rasters - *.sr, *.ras 
            TIFF files - *.tiff, *.tif
        for binary (bool) masks:
            *.png
        for 32 bit float images:
            *.tiff
    dtype = (None, float,bool)
            all other dtypes are converted to either uint8 or uint16
    cmap = display grayscale as rgb using colormap: 'flame', 'gnuplot2' etc.
    '''
    if dtype in (float, np.float64, np.float32):
        assert path.endswith(
            '.tiff') or path.endswith(
            '.tif'), 'float arrays can only be saved as TIFF/TIF images'
        from PIL import Image
        Image.fromarray(np.asfarray(img)).save(path)
        # ... PIL is about 3x faster than tifffile.imwrite
    elif dtype in (bool, np.bool):
        # this method at about 10x slower than cv2.imwrite
        # however, it generates 8x smaller images (1bit vs 8bit)
        assert path.endswith(
            '.png'), 'boolean masks can only be saved as PNG images'
        assert img.ndim == 2, 'can only save grayscale images as type(bool)'
        from png import Writer
        with open(path, 'wb') as f:
            s0, s1 = img.shape
            w = Writer(s1, s0, greyscale=True, bitdepth=1)
            if not img.dtype == np.uint16:
                img = img.astype(np.uint8)
            w.write(f, img)
    else:
        img = toUIntArray(img, dtype=dtype, **kwargs)
        if cmap is not None:
            assert img.ndim == 2, '<cmap> can only be used for grayscale images'
            img = applyColorMap(img, cmap)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return cv2.imwrite(path, img)
