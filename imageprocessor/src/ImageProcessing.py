import threading
import os
import base64

import rawpy
import numpy as np
from PIL import Image
import cv2
import flet as ft

from directory_management import generate_temp_dir


TEMP_DIR = generate_temp_dir()


class Parameter:
    """
    A class to store parameters for image adjustments such as exposure, contrast,
    highlights, shadows, and black levels.
    """
    exposure = 0
    contrast = 0
    highlights = 0
    shadows = 0
    black_levels = 0

    def __init__(self, exposure=0, contrast=0, highlights=0, shadows=0, black_levels=0):
        """
        Initializes the parameters with default values or user-provided values.

        :param exposure: Exposure adjustment in stops.
        :param contrast: Contrast adjustment value.
        :param highlights: Highlights adjustment value.
        :param shadows: Shadows adjustment value.
        :param black_levels: Black levels adjustment value.
        """
        self.exposure = exposure
        self.contrast = contrast
        self.highlights = highlights
        self.shadows = shadows
        self.black_levels = black_levels

    def reset_parameters(self):
        """
        Resets all parameters to their default values (0).
        """
        self.exposure = 0
        self.contrast = 0
        self.highlights = 0
        self.shadows = 0
        self.black_levels = 0


class RawImage:
    """
    A class that handles the processing of raw image files, including adjustments
    such as exposure, contrast, highlights, shadows, and black levels.
    """
    def __init__(self, file_path):
        """
        Loads and processes the raw image from the specified file path.

        :param file_path: Path to the raw image file to be processed.
        """
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
        """
        Adjusts the exposure of the image by a certain number of stops.

        :param image: The raw image to be adjusted.
        :param stops: The number of exposure stops to adjust by.
        :return: The exposure-adjusted image.
        """
        return image * (2 ** stops)

    @staticmethod
    def adjust_contrast(image, contrast, pivot=0.416):
        """
        Adjusts the contrast of the image.

        :param image: The raw image to be adjusted.
        :param contrast: The contrast adjustment value.
        :param pivot: The pivot point for contrast adjustment, default is 0.416.
        :return: The contrast-adjusted image.
        """
        contrast = contrast / 800 + 1
        return (image - pivot) * contrast + pivot

    @staticmethod
    def shadow_highlights_correction(
            img,
            shadow_amount_percent, shadow_tone_percent, shadow_radius,
            highlight_amount_percent, highlight_tone_percent, highlight_radius,
            color_percent
    ):
        # Copied from https://gist.github.com/HViktorTsoi/8e8b0468a9fb07842669aa368382a7df
        """
        Image Shadow / Highlight Correction. The same function as it in Photoshop / GIMP
        :param img: input RGB image numpy array of shape (height, width, 3)
        :param shadow_amount_percent [0.0 ~ 1.0]: Controls (separately for the highlight and shadow values in the image) how much of a correction to make.
        :param shadow_tone_percent [0.0 ~ 1.0]: Controls the range of tones in the shadows or highlights that are modified.
        :param shadow_radius [>0]: Controls the size of the local neighborhood around each pixel
        :param highlight_amount_percent [0.0 ~ 1.0]: Controls (separately for the highlight and shadow values in the image) how much of a correction to make.
        :param highlight_tone_percent [0.0 ~ 1.0]: Controls the range of tones in the shadows or highlights that are modified.
        :param highlight_radius [>0]: Controls the size of the local neighborhood around each pixel
        :param color_percent [-1.0 ~ 1.0]:
        :return:
        """
        img *= 255
        img = np.clip(img, 0, 255)
        shadow_tone = shadow_tone_percent * 255
        highlight_tone = 255 - highlight_tone_percent * 255

        shadow_gain = 1 + shadow_amount_percent * 6
        highlight_gain = 1 + highlight_amount_percent * 6

        # extract RGB channel
        height, width = img.shape[:2]
        img = img.astype(np.float32)
        img_R, img_G, img_B = img[..., 2].reshape(-1), img[..., 1].reshape(-1), img[..., 0].reshape(-1)

        # The entire correction process is carried out in YUV space,
        # adjust highlights/shadows in Y space, and adjust colors in UV space
        # convert to Y channel (grey intensity) and UV channel (color)
        img_Y = .3 * img_R + .59 * img_G + .11 * img_B
        img_U = -img_R * .168736 - img_G * .331264 + img_B * .5
        img_V = img_R * .5 - img_G * .418688 - img_B * .081312

        # extract shadow / highlight
        shadow_map = 255 - img_Y * 255 / shadow_tone
        shadow_map[np.where(img_Y >= shadow_tone)] = 0
        highlight_map = 255 - (255 - img_Y) * 255 / (255 - highlight_tone)
        highlight_map[np.where(img_Y <= highlight_tone)] = 0

        # // Gaussian blur on tone map, for smoother transition
        if shadow_amount_percent * shadow_radius > 0:
            # shadow_map = cv2.GaussianBlur(shadow_map.reshape(height, width), ksize=(shadow_radius, shadow_radius), sigmaX=0).reshape(-1)
            shadow_map = cv2.blur(shadow_map.reshape(height, width), ksize=(shadow_radius, shadow_radius)).reshape(-1)

        if highlight_amount_percent * highlight_radius > 0:
            # highlight_map = cv2.GaussianBlur(highlight_map.reshape(height, width), ksize=(highlight_radius, highlight_radius), sigmaX=0).reshape(-1)
            highlight_map = cv2.blur(highlight_map.reshape(height, width),
                                     ksize=(highlight_radius, highlight_radius)).reshape(-1)

        # Tone LUT
        t = np.arange(256)
        LUT_shadow = (1 - np.power(1 - t * (1 / 255), shadow_gain)) * 255
        LUT_shadow = np.maximum(0, np.minimum(255, np.int_(LUT_shadow + .5)))
        LUT_highlight = np.power(t * (1 / 255), highlight_gain) * 255
        LUT_highlight = np.maximum(0, np.minimum(255, np.int_(LUT_highlight + .5)))

        # adjust tone
        shadow_map = shadow_map * (1 / 255)
        highlight_map = highlight_map * (1 / 255)

        iH = (1 - shadow_map) * img_Y + shadow_map * LUT_shadow[np.int_(img_Y)]
        iH = (1 - highlight_map) * iH + highlight_map * LUT_highlight[np.int_(iH)]
        img_Y = iH

        # adjust color
        if color_percent != 0:
            # color LUT
            if color_percent > 0:
                LUT = (1 - np.sqrt(np.arange(32768)) * (1 / 128)) * color_percent + 1
            else:
                LUT = np.sqrt(np.arange(32768)) * (1 / 128) * color_percent + 1

            # adjust color saturation adaptively according to highlights/shadows
            color_gain = LUT[np.int_(img_U ** 2 + img_V ** 2 + .5)]
            w = 1 - np.minimum(2 - (shadow_map + highlight_map), 1)
            img_U = w * img_U + (1 - w) * img_U * color_gain
            img_V = w * img_V + (1 - w) * img_V * color_gain

        # re convert to RGB channel
        output_R = np.int_(img_Y + 1.402 * img_V + .5)
        output_G = np.int_(img_Y - .34414 * img_U - .71414 * img_V + .5)
        output_B = np.int_(img_Y + 1.772 * img_U + .5)

        output = np.vstack([output_B, output_G, output_R]).T.reshape(height, width, 3)
        output = np.minimum(output, 255)
        return output / 255.

    @staticmethod
    def adjust_black_levels(image, black_levels):
        """
        Adjusts the black levels of the image.

        :param image: The raw image to be adjusted.
        :param black_levels: The black levels adjustment value.
        :return: The black-level-adjusted image.
        """
        black_levels = (black_levels / 100) / 2
        range_ = 1 - black_levels
        return image * range_ + black_levels

    def render_image(self, params):
        """
        Renders the image by applying the given parameters for exposure, contrast,
        black levels, highlights, and shadows.

        :param params: The parameters object containing the adjustments to apply.
        :return: The final rendered image.
        """
        # exposure
        image = self.adjust_exposure(self.raw_image, params.exposure)
        # contrast
        image = self.adjust_contrast(image, params.contrast)
        # black_levels
        image = self.adjust_black_levels(image, params.black_levels)
        # highlights, shadows
        image = self.shadow_highlights_correction(
            image,
            shadow_amount_percent=params.shadows/100, shadow_tone_percent=0.5, shadow_radius=5,
            highlight_amount_percent=params.highlights/100, highlight_tone_percent=0.5, highlight_radius=5,
            color_percent=0
        )
        return image

    @staticmethod
    def srgb_gamma_correction(image):
        """
        Applies gamma correction to convert the image gamma from linear to sRGB.

        :param image: The linear image to be gamma corrected.
        :return: The gamma-corrected image.
        """
        mask = image <= 0.0031308
        corrected = np.empty_like(image)
        corrected[mask] = 12.92 * image[mask]
        corrected[~mask] = 1.055 * (image[~mask] ** (1 / 2.4)) - 0.055
        return corrected


    @staticmethod
    def save_image(image, path, bit_depth=8):
        """
        Saves the image to a specified path.

        :param image: The image to save.
        :param path: The destination path for the image.
        :param bit_depth: The bit depth to save the image in (8 or 16).
        """
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
    """
    A subclass of RawImage representing an empty image.

    This class initializes an empty 256x256 RGB image filled with zeros (black image) as a placeholder or default image.
    """
    def __init__(self):
        """
        Initializes an empty 256x256 RGB image with all pixel values set to zero (black).
        """
        self.raw_image = np.zeros((256, 256, 3), dtype=np.float32)

class ImageProcessorThread(threading.Thread):
    """
    A singleton thread class responsible for processing images asynchronously.

    This thread processes images in the background and ensures that only one instance is active at any time.
    It performs image rendering, saving, and encoding tasks, and manages the state of an image container.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
        Ensures that only a single instance of ImageProcessorThread is created (singleton pattern).

        :return: The singleton instance of ImageProcessorThread.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ImageProcessorThread, cls).__new__(cls)
                    cls._instance._initialize()  # Ensure attributes are initialized once
        return cls._instance

    def _initialize(self):
        """
        Initializes the attributes of the thread instance. This ensures that the thread is ready to process images.

        The thread runs as a daemon and starts automatically.
        """
        if self._instance is not None:
            super().__init__()
            self.event = threading.Event()
            self.daemon = True
            self.page = None
            self.image_object = None
            self.params = None
            self.image_container = None
            self.generate_original = False
            self.need_update_image = False
            self.start()

            self._initialized = True  # Prevent re-initialization

    def run(self):
        """
        The main loop that continuously checks if image processing is needed.

        This method waits for the event to be set and processes the image if necessary. It performs the rendering,
        saving, encoding, and updating the image container, then triggers the page update.
        """
        while True:
            self.event.wait()  # Wait for the event to be set
            while self.need_update_image:
                self.need_update_image = False
                image = self.image_object.render_image(self.params)
                target_path = os.path.join(TEMP_DIR, 'temp.tif')
                RawImage.save_image(image, target_path)

                with open(target_path, 'rb') as file:
                    encoded_string = base64.b64encode(file.read()).decode('utf-8')

                if self.image_container.content is None:
                    self.image_container.content = ft.Image(
                        src_base64=encoded_string, key='temp'
                    )
                else:
                    self.image_container.content.src_base64 = encoded_string

                self.page.update()

                if self.generate_original:
                    original_params = Parameter()
                    original_image = self.image_object.render_image(original_params)
                    original_target = os.path.join(TEMP_DIR, 'original.tif')
                    RawImage.save_image(original_image, original_target)

            self.event.clear()  # Clear the event after processing

    def process_image(self, image_object: RawImage, params, image_container, generate_original=False):
        """
        Triggers the image processing by setting the necessary parameters and triggering the event.

        :param image_object: The raw image to be processed.
        :param params: Parameters used for rendering the image.
        :param image_container: The container where the processed image will be placed.
        :param generate_original: Flag indicating whether to generate the original image as well.
        """
        self.image_object = image_object
        self.params = params
        self.image_container = image_container
        self.generate_original = generate_original
        self.need_update_image = True
        self.event.set()  # Trigger image processing


def create_thumbnail(image_path, thumbnail_path):
    """
    Creates a thumbnail of a raw image and saves it to the specified path.

    This function reads a raw image file, processes it to create a smaller version, and saves it as a thumbnail.

    :param image_path: Path to the raw image file.
    :param thumbnail_path: Path where the thumbnail image will be saved.
    """
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
