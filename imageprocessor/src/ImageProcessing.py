import threading
import os
import base64

import rawpy
import numpy as np
from PIL import Image
import flet as ft

from directory_management import generate_temp_dir


TEMP_DIR = generate_temp_dir()


class Parameter:
    exposure = 1
    contrast = 0
    highlights = 0
    shadows = 0
    black_levels = 0
    saturation = 0

    def __init__(self, exposure=0, contrast=0, highlights=0, shadows=0, black_levels=0, saturation=0):
        self.exposure = exposure
        self.contrast = contrast
        self.highlights = highlights
        self.shadows = shadows
        self.black_levels = black_levels
        self.saturation = saturation


class RawImage:
    def __init__(self, file_path):
        self.file_path = file_path
        with rawpy.imread(file_path) as raw_file:
            self.raw_image = raw_file.postprocess(
                use_camera_wb=True,
                output_bps=16,
                no_auto_bright=True,
                gamma=(1, 1)
            )
        self.raw_image = self.raw_image.astype(np.float32) / 65535.0

    @staticmethod
    def adjust_exposure(image, stops):
        return image * (2 ** stops)

    @staticmethod
    def adjust_contrast(image, contrast, pivot=0.416):
        contrast = contrast / 100 + 1
        return (image - pivot) * contrast + pivot

    def render_image(self, params):
        # exposure
        image = self.adjust_exposure(self.raw_image, params.exposure)
        # contrast
        image = self.adjust_contrast(image, params.contrast)
        # highlights, shadows
        # black_levels
        # saturation
        return image

    @staticmethod
    def srgb_gamma_correction(image):
        mask = image <= 0.0031308
        corrected = np.empty_like(image)
        corrected[mask] = 12.92 * image[mask]
        corrected[~mask] = 1.055 * (image[~mask] ** (1 / 2.4)) - 0.055
        return corrected


    @staticmethod
    def save_image(image, path, bit_depth=8):
        if path.lower().endswith(('.png', '.tif', '.tiff')) and bit_depth == 16:
            data_type = np.uint16
            scale = 65535
        else:
            data_type = np.uint8
            scale = 255
        image = RawImage.srgb_gamma_correction(image)
        image = np.clip(image, 0, 1)
        image = (image * scale).astype(data_type)
        Image.fromarray(image, mode='RGB').save(path)


class EmptyImage(RawImage):
    def __init__(self):
        self.raw_image = np.zeros((256, 256, 3), dtype=np.float32)

class ImageProcessorThread(threading.Thread):
    page = None
    image_object = None
    params = None
    image_container = None

    def __init__(self):
        super().__init__()
        self.event = threading.Event()
        self.daemon = True  # Ensure the thread exits when the main program exits
        self.start()

    def run(self):
        global need_update_image
        while True:
            self.event.wait()  # Wait for the event to be set
            while need_update_image:
                need_update_image = False
                image = self.image_object.render_image(self.params)
                temp_path = os.path.join(TEMP_DIR, 'temp.tif')
                RawImage.save_image(image, temp_path)
                with open(temp_path, 'rb') as f:
                    base64_str = base64.b64encode(f.read()).decode('utf-8')
                if self.image_container.content is None:
                    self.image_container.content = ft.Image(src_base64=base64_str)
                else:
                    self.image_container.content.src_base64 = base64_str
                self.page.update()
            self.event.clear()  # Clear the event after processing

    def process_image(self, image_object: RawImage, params, image_container):
        self.image_object = image_object
        self.params = params
        self.image_container = image_container
        global need_update_image
        need_update_image = True
        self.event.set()  # Set the event to start processing


def create_thumbnail(image_path, thumbnail_path):
    with rawpy.imread(image_path) as raw:
        img = raw.postprocess(
            use_camera_wb=True,
            output_bps=8,
            half_size=True
        )
        img = Image.fromarray(img)
        long_edge = 512
        img.thumbnail((long_edge, long_edge))
        img.save(thumbnail_path)
