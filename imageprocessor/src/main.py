import os
import shutil

import flet as ft
from PIL import Image

from config import *
from ImageProcessing import RawImage, EmptyImage, ImageProcessorThread, Parameter, create_thumbnail
import directory_management
from data import Database
import ai_integration

# Create persist and temp dirs
PERSIST_DIR = directory_management.create_persist_dir()
TEMP_DIR = directory_management.create_temp_dir()

# Global Variable
need_update_image = False
image_processor_thread = ImageProcessorThread()


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


def create_param_object(exposure_slider, contrast_slider, highlights_slider, shadows_slider, black_levels_slider, saturation_slider):
    return Parameter(
        exposure=2**exposure_slider.value,
        contrast=contrast_slider.value,
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
    response = ai_integration.api_call(prompt_text_box.value, params)
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


database = Database()
def main(page):
    # library
    image_paths = {}
    # edit
    global image_object, current_image_id
    image_object = EmptyImage()
    current_image_id = 0
    params = Parameter()
    photo_area = None
    # slider and value box
    exposure_slider = None
    contrast_slider = None
    highlights_slider = None
    shadows_slider = None
    black_levels_slider = None
    exposure_slider_value = None
    contrast_slider_value = None
    highlights_slider_value = None
    shadows_slider_value = None
    black_levels_slider_value = None

    def export_button_click(e, image_id):
        image_path = image_paths[image_id]
        # TODO: check if raw image exists, pop up alert if not
        params_sql = database.execute('SELECT exposure, contrast, highlights, shadows, black_levels, saturation FROM images WHERE id = ?', (image_id,)).fetchone()
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
        database.set_config('last_opened', '"None"')
        e.page.update()

    def open_edit_tab(page, image_id):
        global image_object, current_image_id
        current_image_id = image_id
        image_path = database.execute('SELECT path FROM images WHERE id = ?', (image_id,)).fetchone()
        if image_path is None:
            # TODO: alert
            return
        image_path = image_path[0]
        image_object = RawImage(image_path)
        exposure, contrast, highlights, shadows, black_levels, saturation = database.execute(
            'SELECT exposure, contrast, highlights, shadows, black_levels, saturation FROM images WHERE id = ?',
            (image_id,)).fetchone()
        params = Parameter(
            exposure=exposure,
            contrast=contrast,
            highlights=highlights,
            shadows=shadows,
            black_levels=black_levels,
            saturation=saturation
        )

        exposure_slider.value = exposure
        contrast_slider.value = contrast
        highlights_slider.value = highlights
        shadows_slider.value = shadows
        black_levels_slider.value = black_levels
        saturation_slider.value = saturation
        exposure_slider_value.value = str(exposure)
        contrast_slider_value.value = str(contrast)
        highlights_slider_value.value = str(highlights)
        shadows_slider_value.value = str(shadows)
        black_levels_slider_value.value = str(black_levels)
        saturation_slider_value.value = str(saturation)

        page.go('/edit')
        database.set_config('last_opened', image_id)
        processed_image = image_processor_thread.process_image(image_object, params, photo_area)
        return image_object, processed_image

    def onchange_parameter(e, current_param_name, value_text_box, params, img_container, round_=None):
        value_text_box.value = str(round(e.control.value, round_))
        params.__setattr__(current_param_name, e.control.value)
        image_processor_thread.process_image(image_object, params, img_container)
        e.page.update()

    def on_change_end_parameter(e, current_param_name, params, round_=None):
        value = str(round(e.control.value, round_))
        params.__setattr__(current_param_name, e.control.value)
        database.update(table='images', column=[current_param_name], value=[value], condition=f'id = {current_image_id}')

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
            on_change=lambda e: onchange_parameter(
                e, 'exposure', exposure_slider_value,
                **change_parameter_text_common_params, round_=2
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'exposure', params, round_=2)
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
            on_change=lambda e: onchange_parameter(
                e, 'contrast', contrast_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'contrast', params)
        )
        contrast_slider_value = ft.Text('0', height=height)

        highlights_text = ft.Text('Highlights', height=height)
        highlights_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(
                e, 'highlights', highlights_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'highlights', params)
        )
        highlights_slider_value = ft.Text('0', height=height)

        shadows_text = ft.Text('Shadows', height=height)
        shadows_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(
                e, 'shadows', shadows_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'shadows', params)
        )
        shadows_slider_value = ft.Text('0', height=height)

        black_levels_text = ft.Text('Black Levels', height=height)
        black_levels_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(
                e, 'black_levels', black_levels_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'black_levels', params)
        )
        black_levels_slider_value = ft.Text('0', height=height)

        saturation_text = ft.Text('Saturation', height=height)
        saturation_slider = ft.Slider(
            **common_params,
            on_change=lambda e: onchange_parameter(
                e, 'saturation', saturation_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'saturation', params)
        )
        saturation_slider_value = ft.Text('0', height=height)

        # Create columns
        name_column = ft.Column(
            [exposure_text, contrast_text, highlights_text, shadows_text, black_levels_text,
             saturation_text],
            width=90,
            alignment=ft.MainAxisAlignment.START
        )
        slider_column = ft.Column(
            [exposure_slider, contrast_slider, highlights_slider, shadows_slider,
             black_levels_slider, saturation_slider],
        )
        value_column = ft.Column(
            [exposure_slider_value, contrast_slider_value, highlights_slider_value,
             shadows_slider_value, black_levels_slider_value, saturation_slider_value],
            width=40,
        )

        parameter_area = ft.Row(
            [name_column, slider_column, value_column],
        )
        return (
            parameter_area,
            exposure_slider, contrast_slider, highlights_slider, shadows_slider,
            black_levels_slider,saturation_slider,
            exposure_slider_value, contrast_slider_value, highlights_slider_value,
            shadows_slider_value, black_levels_slider_value, saturation_slider_value
        )

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

    def go_from_edit_to_library(e):
        page.go("/library")
        database.set_config('last_opened', '"None"')
    # App bar
    library_page_button = ft.ElevatedButton(
        text='Library',
        on_click=go_from_edit_to_library
    )
    edit_page_export_button = ft.TextButton(
        text='Export',
        on_click=lambda e: Image.open(os.path.join(TEMP_DIR, 'temp.tif')).save(image_object.file_path+'.jpeg')
    )
    # Photo area
    image_object, photo_area = create_photo_area(
        page,
        None,
        params=params
    )
    # Parameter area
    (parameter_area,
     exposure_slider, contrast_slider, highlights_slider, shadows_slider, black_levels_slider, saturation_slider,
     exposure_slider_value, contrast_slider_value, highlights_slider_value,
     shadows_slider_value, black_levels_slider_value, saturation_slider_value
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
            ft.Row([library_page_button, edit_page_export_button]),
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
        input_file_picker, import_button,
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
    last_opened = database.get_config('last_opened')
    if last_opened:
        last_opened = last_opened[0][0]
        if last_opened != 'None':
            current_image_id = int(last_opened)
            image_object, _ = open_edit_tab(page, current_image_id)
    page.update()

ft.app(target=main)
shutil.rmtree(TEMP_DIR)
