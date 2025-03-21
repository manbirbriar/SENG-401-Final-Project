import base64
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
print(TEMP_DIR)

# Global Variable
image_processor_thread = ImageProcessorThread()


def create_photo_area(page, raw_path, params):
    """
    Creates a photo area on the page to display the image and triggers image processing.

    Depending on whether a raw image path is provided or not, this function creates an
    image object and processes it using the `ImageProcessorThread`.

    :param page: The page where the image will be displayed.
    :param raw_path: The path to the raw image file. If None, an empty image will be created.
    :param params: Parameters for processing the image.
    :return: A tuple containing the image object and the container for displaying the image.
    """
    img_container = ft.Container(
        width=page.width,
        height=page.height,
        expand=True,
    )
    if raw_path is None:
        image_object = EmptyImage()
    else:
        image_object = RawImage(raw_path)
        image_processor_thread.process_image(image_object, params, img_container)
    return image_object, img_container


def create_control_area(page):
    """
    Creates the control area with UI elements for user interaction.

    This function creates status display components, input fields, and buttons for submitting
    prompts, comparing images, and resetting settings.

    :param page: The page where the controls will be displayed.
    :return: A tuple containing various UI components such as status text, input fields, and buttons.
    """
    status_description_box = ft.Text(value='Status:')
    status_text_box = ft.Text(value='Ready')
    status_container = ft.Row(
        controls=[
            status_description_box,
            status_text_box
        ]
    )
    prompt_text_box = ft.TextField(
        label='Describe how you want to improve the image',
        multiline=True,
        # width=200
    )
    feedback_text_box = ft.Text()
    submit_button = ft.TextButton(text='Submit')
    compare_button = ft.TextButton(text='Compare', tooltip='Click to toggle the original image and the edited one')
    reset_button = ft.TextButton(text='Reset')
    return status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, reset_button


image_analyzer = ai_integration.ImageAnalyzer()
def submit_button_click(
        e, prompt_text_box, params, status_text_box, feedback_text_box,
        exposure_slider, contrast_slider, highlights_slider,
        exposure_slider_value, contrast_slider_value, highlights_slider_value,
        image_object, img_container
):
    """
    Handles the click event of the submit button by sending the image to the AI API and updating
    the UI with the results.

    This function sends the prompt and parameters to the image analysis API, processes the response,
    and updates the image settings (exposure, contrast, etc.) based on the returned parameters.
    The image is also reprocessed using the updated settings.

    :param e: The event triggered by the button click.
    :param prompt_text_box: The text box containing the prompt for image improvement.
    :param params: The parameters used for image processing.
    :param status_text_box: The status text box for showing status messages.
    :param feedback_text_box: The feedback text box for showing API feedback.
    :param exposure_slider: The slider for adjusting the exposure.
    :param contrast_slider: The slider for adjusting the contrast.
    :param highlights_slider: The slider for adjusting the highlights.
    :param exposure_slider_value: The current value of the exposure slider.
    :param contrast_slider_value: The current value of the contrast slider.
    :param highlights_slider_value: The current value of the highlights slider.
    :param image_object: The image object to be processed.
    :param img_container: The container for displaying the image.
    """
    # Call API
    status_text_box.value = 'Sending image to Google AI Studio'
    e.page.update()
    response = image_analyzer.api_call(prompt_text_box.value, params)
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
        contrast_slider.value = new_params.shadows
        contrast_slider_value.value = new_params.shadows
        highlights_slider.value = new_params.black_levels
        highlights_slider_value.value = new_params.black_levels
        database.update(table='images', column=['contrast'], value=[new_params.contrast], condition=f'id = {current_image_id}')
        database.update(table='images', column=['exposure'], value=[new_params.exposure], condition=f'id = {current_image_id}')
        database.update(table='images', column=['highlights'], value=[new_params.highlights], condition=f'id = {current_image_id}')
        database.update(table='images', column=['shadows'], value=[new_params.shadows], condition=f'id = {current_image_id}')
        database.update(table='images', column=['black_levels'], value=[new_params.black_levels], condition=f'id = {current_image_id}')
        image_processor_thread.process_image(image_object, new_params, img_container)
    else:
        status_text_box.value = 'Failed'
        feedback_text_box.value = response['feedback']
    e.page.update()

def open_url(url):
    """
    Opens a URL in the default web browser, with platform-specific handling.

    On Windows, it uses the `start` command, and on macOS/Linux, it uses the `open` command.

    :param url: The URL to be opened in the web browser.
    """
    if os.name == 'nt':
        os.system(f'start {url}')
    else:
        os.system(f'open {url}')

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

    # Import Export
    def file_selected(e):
        """
        Handles the file selection process, imports selected image(s), creates thumbnails, and adds them
        to the database and the library page.

        Args:
            e (ft.FilePickerResult): The result from the file picker containing the selected files.
        """
        if not e.files:
            return
        file_path = [_.path for _ in e.files]
        # save to database
        _ = database.import_image(file_path)
        if _ is None:
            return
        ids, new_images = _
        for new_image_path, id_ in zip(new_images, ids):
            # create thumbnails
            create_thumbnail(new_image_path, os.path.join(PERSIST_DIR, 'thumbnails', str(id_) + '.jpg'))
            # add to image_paths
            image_paths[id_] = new_image_path
            # add image to library page
            image_grid.controls.append(create_image_selector_in_library(id_))
        database.set_config('last_opened', '"None"')
        e.page.update()


    def import_button_onclick(e):
        """
        Triggered when the 'Import Image' button is clicked. Opens a file picker to select images to import.
        """
        input_file_picker = ft.FilePicker(
            on_result=file_selected,
        )
        page.overlay.append(input_file_picker)
        page.update()
        input_file_picker.pick_files(allow_multiple=True, allowed_extensions=RAW_EXTENSIONS)
    import_button = ft.TextButton(
        text='Import Image',
        on_click=import_button_onclick
    )

    def export(e, image_id, image=None):
        """
        Handles the export of an image to the selected path. If no image is provided, the image is loaded
        from the database and rendered before exporting.

        Args:
            e (ft.FilePickerResult): The result from the file picker containing the selected path.
            image_id (int): The ID of the image to export.
            image (RawImage, optional): The image object to export. Defaults to None.
        """
        if e.path is None:
            return
        export_path = e.path
        if image is None:
            image_path = image_paths[image_id]
            # TODO: check if raw image exists, pop up alert if not
            params_sql = database.execute('SELECT exposure, contrast, highlights, shadows, black_levels FROM images WHERE id = ?', (image_id,)).fetchone()
            params = Parameter(*params_sql)
            image_object = RawImage(image_path)
            image = image_object.render_image(params)
            RawImage.save_image(image, export_path)
        else:
            image.save(export_path)
        e.page.update()

    def export_button_click(e, image_id, image=None):
        """
        Triggered when the 'Export' button is clicked. Opens a file picker to save the image to a specified path.

        Args:
            e (ft.Event): The event object triggered by the button click.
            image_id (int): The ID of the image to export.
            image (RawImage, optional): The image object to export. Defaults to None.
        """
        image_path = image_paths[image_id]
        file_name = os.path.basename(image_path)
        file_name, _ = os.path.splitext(file_name)
        output_file_picker = ft.FilePicker(
            on_result=lambda e1: export(e1, image_id, image)
        )
        e.page.overlay.append(output_file_picker)
        e.page.update()
        output_file_picker.save_file(
            file_name=f'{file_name}.jpeg'
        )

    def delete_button_click(e, image_id):
        """
        Handles the deletion of an image from both the database and the UI. Removes the thumbnail
        and deletes the image entry from the database.

        Args:
            e (ft.Event): The event object triggered by the button click.
            image_id (int): The ID of the image to delete.
        """
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
        """
        Creates an image selector with edit, export, and delete buttons for displaying images in the library.

        Args:
            image_id (int): The ID of the image to display.

        Returns:
            ft.Column: The column containing the image, edit, export, and delete buttons.
        """
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

    def open_edit_tab(page, image_id):
        """
        Opens the image edit tab and loads the image and its parameters from the database for editing.

        Args:
            page (ft.Page): The page object representing the web interface.
            image_id (int): The ID of the image to edit.

        Returns:
            RawImage: The image object that is being edited.
        """
        global image_object, current_image_id
        current_image_id = image_id
        image_path = database.execute('SELECT path FROM images WHERE id = ?', (image_id,)).fetchone()
        if image_path is None:
            # TODO: alert
            return
        image_path = image_path[0]
        image_object = RawImage(image_path)
        exposure, contrast, highlights, shadows, black_levels = database.execute(
            'SELECT exposure, contrast, highlights, shadows, black_levels FROM images WHERE id = ?',
            (image_id,)).fetchone()
        params = Parameter(
            exposure=exposure,
            contrast=contrast,
            highlights=highlights,
            shadows=shadows,
            black_levels=black_levels
        )

        exposure_slider.value = exposure
        contrast_slider.value = contrast
        highlights_slider.value = highlights
        shadows_slider.value = shadows
        black_levels_slider.value = black_levels
        exposure_slider_value.value = str(exposure)
        contrast_slider_value.value = str(contrast)
        highlights_slider_value.value = str(highlights)
        shadows_slider_value.value = str(shadows)
        black_levels_slider_value.value = str(black_levels)

        page.go('/edit')
        database.set_config('last_opened', image_id)
        image_processor_thread.process_image(image_object, params, photo_area, generate_original=True)
        return image_object

    def onchange_parameter(e, current_param_name, value_text_box, params, img_container, round_=None):
        """
        Updates the value of a parameter when the slider is adjusted and processes the image.

        Args:
            e (ft.SliderChangeEvent): The event object triggered by the slider change.
            current_param_name (str): The name of the parameter to update.
            value_text_box (ft.Text): The text box displaying the parameter value.
            params (Parameter): The parameters object containing image settings.
            img_container (ft.Image): The container for displaying the processed image.
            round_ (int, optional): The number of decimal places to round the value. Defaults to None.
        """
        value_text_box.value = str(round(e.control.value, round_))
        params.__setattr__(current_param_name, e.control.value)
        image_processor_thread.process_image(image_object, params, img_container)
        e.page.update()

    def on_change_end_parameter(e, current_param_name, params, round_=None):
        """
        Updates the database with the new parameter value when the slider change ends.

        Args:
            e (ft.SliderChangeEvent): The event object triggered by the slider change.
            current_param_name (str): The name of the parameter to update.
            params (Parameter): The parameters object containing image settings.
            round_ (int, optional): The number of decimal places to round the value. Defaults to None.
        """
        value = str(round(e.control.value, round_))
        params.__setattr__(current_param_name, e.control.value)
        database.update(table='images', column=[current_param_name], value=[value], condition=f'id = {current_image_id}')

    def create_parameter_sliders(img_container):
        """
        Creates the sliders for adjusting exposure, contrast, highlights, shadows, and black levels
        in the image editing interface.

        Args:
            img_container (ft.Image): The container for displaying the processed image.

        Returns:
            tuple: A tuple containing the parameter sliders.
        """
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
            'max': 100,
            'value': 0,
            'height': height
        }
        contrast_text = ft.Text('Contrast', height=height)
        contrast_slider = ft.Slider(
            **common_params,
            min=-100,
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
            min=0,
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
            min=0,
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
            min=-100,
            on_change=lambda e: onchange_parameter(
                e, 'black_levels', black_levels_slider_value,
                **change_parameter_text_common_params
            ),
            on_change_end=lambda e: on_change_end_parameter(e, 'black_levels', params)
        )
        black_levels_slider_value = ft.Text('0', height=height)

        # Create columns
        name_column = ft.Column(
            [exposure_text, contrast_text, highlights_text, shadows_text, black_levels_text],
            width=90,
            alignment=ft.MainAxisAlignment.START
        )
        slider_column = ft.Column(
            [exposure_slider, contrast_slider, highlights_slider, shadows_slider,
             black_levels_slider],
        )
        value_column = ft.Column(
            [exposure_slider_value, contrast_slider_value, highlights_slider_value,
             shadows_slider_value, black_levels_slider_value],
            width=40,
        )

        parameter_area = ft.Row(
            [name_column, slider_column, value_column],
        )
        return (
            parameter_area,
            exposure_slider, contrast_slider, highlights_slider, shadows_slider,
            black_levels_slider,
            exposure_slider_value, contrast_slider_value, highlights_slider_value,
            shadows_slider_value, black_levels_slider_value
        )

    def reset(e):
        """
        Resets all sliders and parameters to their default values, updates the database
        with reset values, and processes the image with the reset parameters.

        Args:
            e: The event object triggered by the reset action.
        """
        # Set slider value
        exposure_slider.value = 0
        contrast_slider.value = 0
        highlights_slider.value = 0
        shadows_slider.value = 0
        black_levels_slider.value = 0
        # Set slider text box value
        exposure_slider_value.value = '0'
        contrast_slider_value.value = '0'
        highlights_slider_value.value = '0'
        shadows_slider_value.value = '0'
        black_levels_slider_value.value = '0'
        # reset param object
        params.reset_parameters()
        # update database
        database.update(table='images', column=['contrast'], value=[0], condition=f'id = {current_image_id}')
        database.update(table='images', column=['exposure'], value=[0], condition=f'id = {current_image_id}')
        database.update(table='images', column=['highlights'], value=[0], condition=f'id = {current_image_id}')
        database.update(table='images', column=['shadows'], value=[0], condition=f'id = {current_image_id}')
        database.update(table='images', column=['black_levels'], value=[0], condition=f'id = {current_image_id}')
        page.update()
        image_processor_thread.process_image(image_object, params, photo_area)

    # app name
    page.title = APP_NAME
    # setup thread
    image_processor_thread.page = page
    # Window
    page.window.width = 1250
    page.window.height = 1000
    page.window.top = 0
    page.window.left = 0

    def go_from_edit_to_library(e):
        """
        Navigates from the edit page to the library page and updates the last opened image
        configuration in the database.

        Args:
            e: The event object triggered by the action of navigating to the library.
        """
        page.go("/library")
        database.set_config('last_opened', '"None"')

    def compare_button_click(e):
        """
        Toggles the comparison between the original image and the edited version by swapping
        the image source displayed in the photo area.

        Args:
            e: The event object triggered by the comparison button click.
        """
        if photo_area.content.key == 'original':
            photo_area.content.key = 'temp'
            with open(os.path.join(TEMP_DIR, 'temp.tif'), 'rb') as file:
                photo_area.content.src_base64 = base64.b64encode(file.read()).decode('utf-8')
        else:
            photo_area.content.key = 'original'
            with open(os.path.join(TEMP_DIR, 'original.tif'), 'rb') as file:
                photo_area.content.src_base64 = base64.b64encode(file.read()).decode('utf-8')
        e.page.update()

    library_page_button = ft.ElevatedButton(
        text='Library',
        on_click=go_from_edit_to_library
    )
    edit_page_export_button = ft.TextButton(
        text='Export',
        on_click=lambda e: export_button_click(e, current_image_id, Image.open(os.path.join(TEMP_DIR, 'temp.tif')))
    )
    # Photo area
    image_object, photo_area = create_photo_area(
        page,
        None,
        params=params
    )
    # Parameter area
    (parameter_area,
     exposure_slider, contrast_slider, highlights_slider, shadows_slider, black_levels_slider,
     exposure_slider_value, contrast_slider_value, highlights_slider_value,
     shadows_slider_value, black_levels_slider_value
     ) = create_parameter_sliders(photo_area)

    # Control area
    status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, reset_button = create_control_area(page)
    submit_button.on_click = lambda e: submit_button_click(
        e,
        prompt_text_box, params, status_text_box, feedback_text_box,
        exposure_slider, contrast_slider, highlights_slider,
        exposure_slider_value, contrast_slider_value, highlights_slider_value,
        image_object, photo_area
    )
    compare_button.on_click = compare_button_click
    reset_button.on_click = reset

    control_button_area = ft.Row(
        [submit_button, compare_button, reset_button],
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
        import_button,
        image_grid
    ])
    def route_change(route):
        """
        Handles route changes by updating the views for the page based on the selected route.

        Args:
            route: The new route path to navigate to.
        """
        page.views.clear()
        page.views.append(ft.View("/library", [library_page]))
        if page.route == '/edit':
            page.views.append(ft.View("/edit", [edit_page]))
        page.update()
    def view_pop(view):
        """
        Handles the pop event when a view is closed, navigating back to the previous route.

        Args:
            view: The view object being popped from the navigation stack.
        """
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go('/library')
    last_opened = database.get_config('last_opened')
    if last_opened:
        last_opened = last_opened[0][0]
        if last_opened != 'None' or last_opened != '"None"':
            current_image_id = int(last_opened)
            image_object = open_edit_tab(page, current_image_id)
    # first time open
    not_first_time_open = database.get_config('not_first_time_open')
    if not not_first_time_open:
        database.set_config('not_first_time_open', '1')
        def handle_close(e):
            # Close the dialog, open the tutorial if user selected.
            page.close(dlg_modal)
            if e.control.text == 'Yes':
                open_url('https://youtu.be/zhYNW-RsFqc')
            page.update()

        dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Do you want to watch the tutorial?"),
            actions=[
                ft.TextButton("Yes", on_click=handle_close),
                ft.TextButton("No", on_click=handle_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg_modal)
    page.update()

if __name__ == '__main__':
    ft.app(target=main)
    shutil.rmtree(TEMP_DIR)
