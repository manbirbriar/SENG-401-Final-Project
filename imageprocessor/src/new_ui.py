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


class ImageProcessorThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.event = threading.Event()
        self.page = None
        self.raw_path = None
        self.params = None
        self.image_container = None
        self.daemon = True  # Ensure the thread exits when the main program exits
        self.start()

    def run(self):
        while True:
            self.event.wait()  # Wait for the event to be set
            print('start')
            update_image(self.page, self.raw_path, self.params, self.image_container)
            self.page.update()
            print('end')
            self.event.clear()  # Clear the event after processing

    def process_image(self, raw_path, params, image_control):
        print('process_image')
        self.raw_path = raw_path
        self.params = params
        self.image_container = image_control
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


def update_image(page, raw_path, params: Parameter, image_control):
    with rawpy.imread(raw_path) as image:
        rgb_linear = image.postprocess(
            output_bps=8,
            no_auto_bright=True,
            use_camera_wb=True,
            bright=params.exposure,
            gamma=(1, 1)
        )
    # save image with PIL
    # image = rgb_linear.astype(np.float32) / 65535.0
    # image = np.clip(image, 0, 1)
    # image = (image * 255).astype(np.uint8)
    image = Image.fromarray(rgb_linear, mode='RGB')
    temp_path = os.path.join(TEMP_DIR, 'temp.tif')
    # Save the image to the temporary file
    image.save(temp_path, format='TIFF')
    with open(temp_path, 'rb') as f:
        base64_str = base64.b64encode(f.read()).decode('utf-8')
    image_control.content = ft.Image(
        src_base64=base64_str,
        fit=ft.ImageFit.CONTAIN
    )
    page.update()


def create_photo_area(page, raw_path, params):
    img_container = ft.Container(
        width=page.width,
        height=page.height
    )
    image_processor_thread.process_image(raw_path, params, img_container)
    return img_container


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


def onchange_parameter(e, current_param, text, raw_path, params, img_container, round_=None):
    text.value = str(round(e.control.value, round_))
    params.__setattr__(current_param, e.control.value)
    image_processor_thread.process_image(raw_path, params, img_container)
    e.page.update()


def create_parameter_sliders(page, raw_path, img_container, params):
    height = 30
    print(img_container)
    change_parameter_text_common_params = {
        'raw_path': raw_path,
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
    photo_area = create_photo_area(
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
     ) = create_parameter_sliders(page, raw_path, photo_area, params)

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
