import time
import shutil
import flet as ft
import rawpy
import sqlite3
import os
import numpy as np
from PIL import Image
import threading
import tempfile
import base64


APP_NAME = 'AI RAW Image Processor'

# Create persist and temp dirs
sys_win = os.name == 'nt'
if sys_win:  # Windows
    PERSIST_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_NAME)
else:  # macOS/Linux
    PERSIST_DIR = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
TEMP_DIR = os.path.join(PERSIST_DIR, 'temp')
for i in (PERSIST_DIR, TEMP_DIR):
    if not os.path.exists(i):
        os.makedirs(i)


# Global Variable
need_update_image = False


# Class
class RawImage:
    def __init__(self, file_path):
        self.raw_file = rawpy.imread(file_path)
        self.raw_image = self.raw_file.postprocess(
            use_camera_wb=True,
            output_bps=16,
            no_auto_bright=True,
            gamma=(1, 1)
        )
        self.raw_image = self.raw_image.astype(np.float32) / 65535.0

    @staticmethod
    def adjust_exposure(image, stops):
        return image * (2 ** stops)

    def render_image(self, params):
        # exposure
        image = self.adjust_exposure(self.raw_image, params.exposure)
        # contrast
        # highlights, shadows
        # white_levels, black_levels
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
        print(image)
        Image.fromarray(image, mode='RGB').save(path)


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
                self.image_object.save_image(image, temp_path)
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

# Usage example
image_processor_thread = ImageProcessorThread()



class Parameter:
    exposure = 1
    contrast = 0
    white_levels = 0
    highlights = 0
    shadows = 0
    black_levels = 0
    saturation = 0

    def __init__(self, exposure, contrast, white_levels, highlights, shadows, black_levels, saturation):
        self.exposure = exposure
        self.contrast = contrast
        self.white_levels = white_levels
        self.highlights = highlights
        self.shadows = shadows
        self.black_levels = black_levels
        self.saturation = saturation



def api_call(image_path: str, prompt: str, current_parameters: Parameter):
    # Placeholder for API call
    return {
        'success': 1,
        'feedback': f"The adjustments looks good, xxx can be modified to improve the image.",
        'new_parameters': current_parameters
    }


def create_appbar(page):
    # TODO: Add highlight for the current page
    library_page_button = ft.TextButton(
        text='Library'
    )
    edit_page_button = ft.TextButton(
        text='Edit'
    )
    page.appbar = ft.AppBar(
        title=ft.Text('RAW Image Processor'),
        actions=[
            library_page_button,
            edit_page_button
        ],
        title_spacing=10
    )
    return library_page_button, edit_page_button


def create_photo_area(page, raw_path, params):
    img_container = ft.Container(
        width=page.width,
        height=page.height
    )
    image_object = RawImage(raw_path)
    image_processor_thread.process_image(image_object, params, img_container)
    return image_object, img_container


def create_control_area(page):
    prompt_text_box = ft.TextField(
        label='Prompt',
        multiline=True,
        # width=200
    )
    feedback_text_box = ft.Text()

    submit_button = ft.TextButton(text='Submit')
    compare_button = ft.TextButton(text='Compare')
    apply_button = ft.TextButton(text='Apply')
    return prompt_text_box, feedback_text_box, submit_button, compare_button, apply_button


def onchange_parameter(e, current_param, text, image_object, params, img_container, round_=None):
    text.value = str(round(e.control.value, round_))
    params.__setattr__(current_param, e.control.value)
    image_processor_thread.process_image(image_object, params, img_container)
    e.page.update()


def create_parameter_sliders(page, image_object, img_container, params):
    height = 30
    change_parameter_text_common_params = {
        'image_object': image_object,
        'img_container': img_container,
        'params': params
    }

    exposure_text = ft.Text('Exposure', height=height)
    exposure_slider_value = ft.Text('0', height=height)
    exposure_slider = ft.Slider(
        label='Exposure',
        min=-5,
        max=5,
        value=0,
        height=height,
        on_change=lambda e: onchange_parameter(e, 'exposure', exposure_slider_value, **change_parameter_text_common_params, round_=2),
    )

    common_params = {
        'min': -100,
        'max': 100,
        'value': 0,
        'height': height
    }
    contrast_text = ft.Text('Contrast', height=height)
    contrast_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'contrast', contrast_slider_value, **change_parameter_text_common_params)
    )
    contrast_slider_value = ft.Text('0', height=height)

    white_levels_text = ft.Text('White Levels', height=height)
    white_levels_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'white_levels', white_levels_slider_value, **change_parameter_text_common_params)
    )
    white_levels_slider_value = ft.Text('0', height=height)

    highlights_text = ft.Text('Highlights', height=height)
    highlights_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'highlights', highlights_slider_value, **change_parameter_text_common_params)
    )
    highlights_slider_value = ft.Text('0', height=height)

    shadows_text = ft.Text('Shadows', height=height)
    shadows_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'shadows', shadows_slider_value, **change_parameter_text_common_params)
    )
    shadows_slider_value = ft.Text('0', height=height)

    black_levels_text = ft.Text('Black Levels', height=height)
    black_levels_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'black_levels', black_levels_slider_value, **change_parameter_text_common_params)
    )
    black_levels_slider_value = ft.Text('0', height=height)

    saturation_text = ft.Text('Saturation', height=height)
    saturation_slider = ft.Slider(
        **common_params,
        on_change=lambda e: onchange_parameter(e, 'saturation', saturation_slider_value, **change_parameter_text_common_params)
    )
    saturation_slider_value = ft.Text('0', height=height)

    # Create columns
    name_column = ft.Column(
        [exposure_text, contrast_text, white_levels_text, highlights_text, shadows_text, black_levels_text, saturation_text],
        width=90,
        alignment=ft.MainAxisAlignment.START
    )
    slider_column = ft.Column(
        [exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider, black_levels_slider, saturation_slider],
    )
    value_column = ft.Column(
        [exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value, shadows_slider_value, black_levels_slider_value, saturation_slider_value],
        width=40,
    )

    parameter_area = ft.Row(
        [name_column, slider_column, value_column],
    )
    return (
        parameter_area,
        exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider, black_levels_slider,
        exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value, shadows_slider_value, black_levels_slider_value
    )


def create_param_object(exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider, black_levels_slider, saturation_slider):
    return Parameter(
        exposure=2**exposure_slider.value,
        contrast=contrast_slider.value,
        white_levels=white_levels_slider.value,
        highlights=highlights_slider.value,
        shadows=shadows_slider.value,
        black_levels=black_levels_slider.value,
        saturation=saturation_slider.value
    )


def main(page):
    # temp
    raw_path = '/Users/ibobby/School/SENG401/SENG-401-Final-Project/sample_images/R62_0323.CR3'
    # app name
    page.title = APP_NAME
    # setup thread
    image_processor_thread.page = page
    # Window
    page.window.width = 1250
    page.window.height = 1000
    # page.window.min_height = 400
    # page.window.min_width = 1215
    page.window.top = 0
    page.window.left = 0

    # App bar
    appbar_library_button, appbar_edit_button = create_appbar(page)

    params = Parameter(1, 0, 0, 0, 0, 0, 0)
    # Photo area
    image_object, photo_area = create_photo_area(
        page,
        raw_path,
        params=params
    )

    # Control area
    prompt_text_box, feedback_text_box, submit_button, compare_button, apply_button = create_control_area(page)
    control_button_area = ft.Row(
        [submit_button, compare_button, apply_button],
        alignment=ft.MainAxisAlignment.CENTER
    )
    control_area = ft.Column(
        [prompt_text_box, feedback_text_box, control_button_area]
    )

    # Parameter area
    (parameter_area,
    exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider, black_levels_slider,
    exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value, shadows_slider_value, black_levels_slider_value
     ) = create_parameter_sliders(page, image_object, photo_area, params)

    # Edit area
    edit_area = ft.Column(
        [control_area, parameter_area],
        width=400
    )
    # Main area
    main_area = ft.Row(
        [photo_area, edit_area],
        vertical_alignment=ft.CrossAxisAlignment.START
    )
    page.add(main_area)
    page.update()

ft.app(target=main)
shutil.rmtree(TEMP_DIR)
# conn.close()
