import time
import shutil
import flet as ft
import numpy
import rawpy
import sqlite3
import os
import numpy as np
from PIL import Image
import threading
import base64
from google import genai
import json

from setuptools.extension import Library

APP_NAME = 'AI RAW Image Processor'
GOOGLE_AI_STUDIO_API_KEY = ""
RAW_EXTENSIONS = [
    'dng',  # Apple, Casio, DJI, DxO, Google, GoPro, Hasselblad, Huawei, Leica, LG, Light, Motorola, Nokia, OnePlus, OPPO, Parrot, Pentax, Pixii, Ricoh, Samsung, Sigma, Skydio, Sony, Xiaomi, Yuneec, Zeiss
    'tif',  # Canon, Mamiya, Phase One
    'crw', 'cr2', 'cr3',  # Canon
    'raw',  # Contax, Kodak, Leica, Panasonic
    'erf',  # Epson
    'raf',  # Fujifilm
    'gpr',  # GoPro
    '3fr', 'fff',  # Hasselblad
    'arw',  # Hasselblad, Sony
    'dcr', 'kdc',  # Kodak
    'mrw',  # Konica Minolta
    'mos',  # Leaf, Mamiya
    'iiq',  # Leaf, Mamiya, Phase One
    'rwl',  # Leica
    'mef', 'mfw',  # Mamiya
    'nef', 'nrw', 'nefx',  # Nikon
    'orf',  # OM Digital Solutions, Olympus
    'rw2',  # Panasonic
    'pef',  # Pentax
    'srw',  # Samsung
    'x3f',  # Sigma
]

# Create persist and temp dirs
sys_win = os.name == 'nt'
if sys_win:  # Windows
    PERSIST_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_NAME)
else:  # macOS/Linux
    PERSIST_DIR = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
TEMP_DIR = os.path.join(PERSIST_DIR, 'temp')
for i in (PERSIST_DIR, TEMP_DIR, os.path.join(PERSIST_DIR, 'thumbnails')):
    if not os.path.exists(i):
        os.makedirs(i)


# Global Variable
need_update_image = False
client = genai.Client(api_key=GOOGLE_AI_STUDIO_API_KEY)


# Class
class RawImage:
    def __init__(self, file_path):
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
        Image.fromarray(image, mode='RGB').save(path)


class EmptyImage(RawImage):
    def __init__(self):
        self.raw_image = numpy.zeros((256, 256, 3), dtype=numpy.float32)


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

    def __init__(self, exposure=0, contrast=0, white_levels=0, highlights=0, shadows=0, black_levels=0, saturation=0):
        self.exposure = exposure
        self.contrast = contrast
        self.white_levels = white_levels
        self.highlights = highlights
        self.shadows = shadows
        self.black_levels = black_levels
        self.saturation = saturation



def api_call(prompt: str, current_parameters: Parameter):
    # Placeholder for API call
    # Define a structured prompt
    prompt = f"""Analyze this image: I want {prompt}; Current parameters are {{exposure: {current_parameters.exposure}, contrast: {current_parameters.contrast}, highlights: {current_parameters.highlights}}} and return a JSON object with the following fields:
    {{
      "improvement_suggestions": "A couple of sentences on how to improve the image.",
      "contrast_adjustment": "An integer between -100 and 100 indicating the recommended contrast adjustment.",
      "highlight_adjustment": "An integer between -100 and 100 indicating the recommended highlight adjustment.",
      "exposure_adjustment": "An float number between -5 and 5 indicating the recommended stops of exposure adjustment."
    }}
    Ensure the response is valid JSON and nothing else.
    """
    Image.open(os.path.join(TEMP_DIR, 'temp.tif')).save(os.path.join(TEMP_DIR, 'temp.jpeg'))
    image = Image.open(os.path.join(TEMP_DIR, 'temp.jpeg'))
    # Generate structured response
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[image, prompt]
    )
    response = response.text.removeprefix('```json\n').removesuffix('\n```')
    response = json.loads(response)
    parameter = Parameter(
        exposure=response['exposure_adjustment'],
        contrast=response['contrast_adjustment'],
        highlights=response['highlight_adjustment'],
    )
    return {
        'success': 1,
        'feedback': response['improvement_suggestions'],
        'new_parameters': parameter
    }


def create_photo_area(page, raw_path, params):
    img_container = ft.Container(
        width=page.width,
        height=page.height
    )
    if raw_path is None:
        image_object = EmptyImage()
    else:
        image_object = RawImage(raw_path)
        image_processor_thread.process_image(image_object, params, img_container)
    return image_object, img_container


def create_control_area(page):
    status_description_box = ft.Text(value='Status:')
    status_text_box = ft.Text(value='Ready')
    status_container = ft.Row(
        controls=[
            status_description_box,
            status_text_box
        ]
    )
    prompt_text_box = ft.TextField(
        label='Prompt',
        multiline=True,
        # width=200
    )
    feedback_text_box = ft.Text()
    submit_button = ft.TextButton(text='Submit')
    compare_button = ft.TextButton(text='Compare')
    apply_button = ft.TextButton(text='Apply')
    return status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, apply_button


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


def submit_button_click(
        e, prompt_text_box, params, status_text_box, feedback_text_box,
        exposure_slider, contrast_slider, highlights_slider,
        exposure_slider_value, contrast_slider_value, highlights_slider_value,
        image_object, img_container
):
    # Call API
    status_text_box.value = 'Sending image to Google AI Studio'
    e.page.update()
    response = api_call(prompt_text_box.value, params)
    if response['success']:
        feedback_text_box.value = response['feedback']
        new_params = response['new_parameters']
        status_text_box.value = 'Success'
        exposure_slider.value = new_params.exposure
        exposure_slider_value.value = new_params.exposure
        contrast_slider.value = new_params.contrast
        contrast_slider_value.value = new_params.contrast
        highlights_slider.value = new_params.highlights
        highlights_slider_value.value = new_params.highlights
        image_processor_thread.process_image(image_object, new_params, img_container)
    else:
        status_text_box.value = 'Failed'
        feedback_text_box.value = 'Failed to process the image.'
    e.page.update()


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(PERSIST_DIR, 'images.db'), check_same_thread=False)
        self.cursor = self.conn.cursor()

    def execute(self, query, replacement=None):
        if replacement is None:
            return self.cursor.execute(query)
        else:
            return self.cursor.execute(query, replacement)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    # TODO: use placeholders for the following methods
    # TODO: add a parameter for commit
    def insert(self, table, values, list_=False, dict_=False):
        if not dict_:
            self.cursor.execute(f'INSERT INTO {table} VALUES (?)', values)
        elif not list_ and dict_:
            columns = ', '.join(values.keys())
            placeholder = ', '.join(['?' for _ in range(len(values))])
            self.cursor.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholder})', tuple(values.values()))
        elif list_ and dict_:
            columns = ', '.join(values[0].keys())
            placeholder = ', '.join(['?' for _ in range(len(values[0]))])
            self.cursor.executemany(f'INSERT INTO {table} ({columns}) VALUES ({placeholder})', tuple([tuple(_.values()) for _ in values]))
        self.commit()
        return self.cursor.lastrowid

    def delete(self, table, condition, replacement=None):
        if replacement is None:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}')
        else:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}', replacement)
        self.commit()

    def drop(self, table):
        self.cursor.execute(f'DROP TABLE {table}')
        self.commit()

    def select(self, table, columns: list, condition=None, replacement=None):
        if condition is not None:
            if replacement is not None:
                return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}', replacement).fetchall()
            else:
                return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}').fetchall()
        else:
            return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table}').fetchall()

    def update(self, table, column: list, value: list, condition):
        self.cursor.execute(f'UPDATE {table} SET {", ".join([f"{column[i]} = {value[i]}" for i in range(len(column))])} WHERE {condition}')
        self.commit()

    # custom
    def import_image(self, paths):
        new_images = []
        for path in paths:
            exist = self.select('images', ['path'], 'path = ?', (path,))
            if not exist:
                new_images.append(path)
        if not new_images:
            return
        self.insert('images', [{'path': _} for _ in new_images], list_=True, dict_=True)
        placeholders = ', '.join('?' for _ in new_images)
        ids = self.select('images', ['id'], f'path IN ({placeholders})', tuple(new_images))
        ids = [_[0] for _ in ids]
        ids.sort()
        return ids, new_images

    def get_params(self, image_id):
        return self.select('images', ['exposure', 'contrast', 'white_levels', 'highlights', 'shadows', 'black_levels', 'saturation'], 'id = ?', (image_id,))


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


database = Database()
def main(page):
    # library
    image_paths = {}
    displaying_image = {}
    # edit
    global image_object
    image_object = EmptyImage()
    image_path = ''
    params = Parameter()
    photo_area = None

    def export_button_click(e, image_id):
        image_path = image_paths[image_id]
        # TODO: check if raw image exists, pop up alert if not
        params_sql = database.execute('SELECT exposure, contrast, white_levels, highlights, shadows, black_levels, saturation FROM images WHERE id = ?', (image_id,)).fetchone()
        params = Parameter(*params_sql)
        image_object = RawImage(image_path)
        image = image_object.render_image(params)
        image_object.save_image(image, image_path+'.jpg')
        e.page.update()

    def delete_button_click(e, image_id):
        os.remove(os.path.join(PERSIST_DIR, 'thumbnails', str(image_id) + '.jpg'))
        database.delete('images', 'id = ?', (image_id,))
        # remove from library view
        image_id = str(image_id)
        for control in image_grid.controls:
            if control.key == image_id:
                image_grid.controls.remove(control)
                break
        e.page.update()

    def create_image_selector_in_library(image_id):
        thumbnail_path = os.path.join(PERSIST_DIR, 'thumbnails', str(image_id) + '.jpg')
        edit_button = ft.ElevatedButton(
            text='Edit',
            on_click=lambda e: open_edit_tab(page, image_id)
        )
        export_button = ft.TextButton(
            text='Export',
            on_click=lambda e: export_button_click(e, image_id),
        )
        delete_button = ft.TextButton(
            text='Delete',
            on_click=lambda e: delete_button_click(e, image_id)
        )
        return ft.Column(
            key=str(image_id),
            controls=[
                ft.Image(src=thumbnail_path, width=200, height=200),
                ft.Row(
                    controls=[
                        edit_button,
                        export_button,
                        delete_button
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def file_selected(e):
        if not e.files:
            return
        file_path = [_.path for _ in e.files]
        # save to database
        ids, new_images = database.import_image(file_path)
        for new_image_path, id_ in zip(new_images, ids):
            # create thumbnails
            create_thumbnail(new_image_path, os.path.join(PERSIST_DIR, 'thumbnails', str(id_) + '.jpg'))
            # add to image_paths
            image_paths[id_] = new_image_path
            # add image to library page
            image_grid.controls.append(create_image_selector_in_library(id_))
        # switch to library page
        page.go('/library')
        e.page.update()

    def open_edit_tab(page, image_id):
        global image_object
        image_path = database.execute('SELECT path FROM images WHERE id = ?', (image_id,)).fetchone()
        if image_path is None:
            # TODO: alert
            return
        image_path = image_path[0]
        image_object = RawImage(image_path)
        exposure, contrast, white_levels, highlights, shadows, black_levels, saturation = database.execute(
            'SELECT exposure, contrast, white_levels, highlights, shadows, black_levels, saturation FROM images WHERE id = ?',
            (image_id,)).fetchone()
        params = Parameter(
            exposure=exposure,
            contrast=contrast,
            white_levels=white_levels,
            highlights=highlights,
            shadows=shadows,
            black_levels=black_levels,
        )
        page.go('/edit')
        processed_image = image_processor_thread.process_image(image_object, params, photo_area)
        return image_object, processed_image

    def onchange_parameter(e, current_param, text, params, img_container, round_=None):
        text.value = str(round(e.control.value, round_))
        params.__setattr__(current_param, e.control.value)
        image_processor_thread.process_image(image_object, params, img_container)
        e.page.update()

    def create_parameter_sliders(img_container):
        height = 30
        change_parameter_text_common_params = {
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
            on_change=lambda e: onchange_parameter(e, 'exposure', exposure_slider_value,
                                                   **change_parameter_text_common_params, round_=2),
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
            on_change=lambda e: onchange_parameter(e, 'contrast', contrast_slider_value,
                                                   **change_parameter_text_common_params)
        )
        contrast_slider_value = ft.Text('0', height=height)

        white_levels_text = ft.Text('White Levels', height=height)
        white_levels_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(e, 'white_levels', white_levels_slider_value,
                                                   **change_parameter_text_common_params)
        )
        white_levels_slider_value = ft.Text('0', height=height)

        highlights_text = ft.Text('Highlights', height=height)
        highlights_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(e, 'highlights', highlights_slider_value,
                                                   **change_parameter_text_common_params)
        )
        highlights_slider_value = ft.Text('0', height=height)

        shadows_text = ft.Text('Shadows', height=height)
        shadows_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(e, 'shadows', shadows_slider_value,
                                                   **change_parameter_text_common_params)
        )
        shadows_slider_value = ft.Text('0', height=height)

        black_levels_text = ft.Text('Black Levels', height=height)
        black_levels_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(e, 'black_levels', black_levels_slider_value,
                                                   **change_parameter_text_common_params)
        )
        black_levels_slider_value = ft.Text('0', height=height)

        saturation_text = ft.Text('Saturation', height=height)
        saturation_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(e, 'saturation', saturation_slider_value,
                                                   **change_parameter_text_common_params)
        )
        saturation_slider_value = ft.Text('0', height=height)

        # Create columns
        name_column = ft.Column(
            [exposure_text, contrast_text, white_levels_text, highlights_text, shadows_text, black_levels_text,
             saturation_text],
            width=90,
            alignment=ft.MainAxisAlignment.START
        )
        slider_column = ft.Column(
            [exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider,
             black_levels_slider, saturation_slider],
        )
        value_column = ft.Column(
            [exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value,
             shadows_slider_value, black_levels_slider_value, saturation_slider_value],
            width=40,
        )

        parameter_area = ft.Row(
            [name_column, slider_column, value_column],
        )
        return (
            parameter_area,
            exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider,
            black_levels_slider,
            exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value,
            shadows_slider_value, black_levels_slider_value
        )

    # Database
    # database.drop('images')
    database.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            exposure FLOAT DEFAULT 0,
            contrast INTEGER DEFAULT 0,
            white_levels INTEGER DEFAULT 0,
            highlights INTEGER DEFAULT 0,
            shadows INTEGER DEFAULT 0,
            black_levels INTEGER DEFAULT 0,
            saturation INTEGER DEFAULT 0
        )
    ''')
    database.execute('''
        CREATE TABLE IF NOT EXISTS CONFIG (
        key TEXT NOT NULL PRIMARY KEY,
        value TEXT
        )
    ''')
    database.commit()

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
    library_page_button = ft.ElevatedButton(
        text='Library',
        on_click=lambda e: page.go("/library")
    )
    # Photo area
    image_object, photo_area = create_photo_area(
        page,
        None,
        params=params
    )
    # Parameter area
    (parameter_area,
     exposure_slider, contrast_slider, white_levels_slider, highlights_slider, shadows_slider, black_levels_slider,
     exposure_slider_value, contrast_slider_value, white_levels_slider_value, highlights_slider_value,
     shadows_slider_value, black_levels_slider_value
     ) = create_parameter_sliders(photo_area)

    # Control area
    status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, apply_button = create_control_area(page)
    submit_button.on_click = lambda e: submit_button_click(
        e,
        prompt_text_box, params, status_text_box, feedback_text_box,
        exposure_slider, contrast_slider, highlights_slider,
        exposure_slider_value, contrast_slider_value, highlights_slider_value,
        image_object, photo_area
    )
    control_button_area = ft.Row(
        [submit_button, compare_button, apply_button],
        alignment=ft.MainAxisAlignment.CENTER
    )
    control_area = ft.Column(
        [status_container, prompt_text_box, feedback_text_box, control_button_area]
    )

    # Edit area
    edit_area = ft.Column(
        [control_area, parameter_area],
        width=400
    )
    # Main area
    edit_page = ft.Column(
        controls=[
            library_page_button,
            ft.Row(
                [photo_area, edit_area],
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        ]
    )
    # Library
    input_file_picker = ft.FilePicker(
        on_result=file_selected,
    )
    import_button = ft.TextButton(
        text='Import Image',
        on_click=lambda e: input_file_picker.pick_files(allow_multiple=True, allowed_extensions=RAW_EXTENSIONS)
    )
    image_grid = ft.GridView(
        expand=1,
        runs_count=5,
        max_extent=250,
        child_aspect_ratio=1.0,
        spacing=5,
        run_spacing=5,
    )
    images_to_load = database.select('images', ['id', 'path'],)
    for i in images_to_load:
        image_paths[i[0]] = i[1]
        image_grid.controls.append(create_image_selector_in_library(i[0]))
    library_page = ft.Column([
        import_button, input_file_picker,
        image_grid
    ])
    # image_grid.controls.append()
    def route_change(route):
        page.views.clear()
        page.views.append(ft.View("/library", [library_page]))
        if page.route == '/edit':
            page.views.append(ft.View("/edit", [edit_page]))
        page.update()
    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go('/library')
    last_opened = database.execute('SELECT value FROM CONFIG WHERE key = "last_opened"').fetchone()
    if last_opened is not None:
        last_opened_id = last_opened[0]
        image_object, _ = open_edit_tab(page, last_opened_id)
    page.update()

ft.app(target=main)
shutil.rmtree(TEMP_DIR)
