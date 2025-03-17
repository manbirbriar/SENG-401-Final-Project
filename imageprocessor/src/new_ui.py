import time

import flet as ft
import sqlite3
import os
import numpy as np
from PIL import Image

class Parameter:
    exposure = 0
    contrast = 0
    white_levels = 0
    highlights = 0
    shadows = 0
    black_levels = 0


def api_call(image_path: str, prompt: str, current_parameters: Parameter):
    # Placeholder for API call
    return {
        'success': 1,
        'feedback': f"The adjustments looks good, xxx can be modified to improve the image.",
        'new_parameters': current_parameters
    }

def main(page):
    page.title = "RAW Image Processor"
    # Window
    page.window.width = 1250
    page.window.height = 1000
    # page.window.min_height = 400
    # page.window.min_width = 1215
    page.window.top = 0
    page.window.left = 0

    # Top bar
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

    # Photo area
    photo_area = ft.Container(
        width=page.width,
        height=page.height,
        content=ft.Image(
            # src='assets/default.tif',
            src='/Users/ibobby/School/SENG401/SENG-401-Final-Project/sample_images/R62_4289.jpeg',
            # src='/Users/ibobby/School/SENG401/SENG-401-Final-Project/sample_images/R62_0323.jpeg',
            fit=ft.ImageFit.CONTAIN,
        )
    )
    # Edit area
    prompt_text_box = ft.TextField(
        label='Prompt',
        multiline=True,
        # width=200
    )
    feedback_text_box = ft.Text()

    submit_button = ft.TextButton(text='Submit')
    compare_button = ft.TextButton(text='Compare')
    apply_button = ft.TextButton(text='Apply')
    control_button_area = ft.Row(
        [submit_button, compare_button, apply_button],
        alignment=ft.MainAxisAlignment.CENTER
    )
    control_area = ft.Column(
        [prompt_text_box, feedback_text_box, control_button_area]
    )
    parameter_area = ft.Column(
        [],
        scroll=ft.ScrollMode.ALWAYS
    )
    edit_area = ft.Column(
        [control_area, parameter_area],
        width=400
    )
    main_area = ft.Row(
        [photo_area, edit_area],
        vertical_alignment=ft.CrossAxisAlignment.START
    )
    page.add(main_area)
    page.update()

ft.app(target=main)

# conn.close()