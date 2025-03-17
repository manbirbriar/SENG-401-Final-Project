import flet as ft
import sqlite3
import os
import numpy as np
from PIL import Image

# Database setup
DB_FILE = "images.db"

def init_db():
    """Initialize database and create table if not exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_image(path):
    """Insert image path into the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO images (path) VALUES (?)", (path,))
    conn.commit()
    conn.close()

def get_images():
    """Retrieve all stored image paths."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM images")
    images = [row[0] for row in cursor.fetchall()]
    conn.close()
    return images

# Image Processing Functions
def adjust_exposure_by_stop(image: np.ndarray, stops: float) -> np.ndarray:
    """Adjust exposure by given number of stops."""
    return np.clip(image * (2.0 ** stops), 0, 1)

def adjust_contrast(image: np.ndarray, contrast: float, pivot: float = 0.416) -> np.ndarray:
    """Adjust contrast."""
    return np.clip((image - pivot) * (1 + contrast) + pivot, 0, 1)

# Global variables
current_image = None

def main(page: ft.Page):
    page.title = "Image Processing App"
    page.padding = 20

    global current_image

    # Initialize database
    init_db()

    # UI components
    uploaded_image = ft.Image(width=400, height=400, border_radius=10, fit=ft.ImageFit.CONTAIN)

    # Sliders
    exposure_slider = ft.Slider(min=-100, max=100, value=0, label="Exposure")
    contrast_slider = ft.Slider(min=-100, max=100, value=0, label="Contrast")

    def reset_sliders():
        """Reset all sliders to default value (0)."""
        exposure_slider.value = 0
        contrast_slider.value = 0
        page.update()

    def upload_image(e: ft.FilePickerResultEvent):
        """Handles image upload, saves path to database, and resets sliders."""
        global current_image
        if e.files:
            file_path = e.files[0].path
            insert_image(file_path)  # Store in database
            current_image = file_path  # Set as active image
            uploaded_image.src = file_path
            page.update()
            reset_sliders()

    def apply_edits(e):
        """Applies exposure and contrast adjustments to the image."""
        global current_image
        if current_image:
            image = Image.open(current_image).convert("RGB")
            np_image = np.array(image) / 255.0  # Normalize to [0, 1]

            # Apply exposure adjustment
            exposure_stops = exposure_slider.value / 100.0
            adjusted_image = adjust_exposure_by_stop(np_image, exposure_stops)

            # Apply contrast adjustment
            contrast_value = contrast_slider.value / 100.0
            adjusted_image = adjust_contrast(adjusted_image, contrast_value)

            # Convert back to image format and save
            updated_image = Image.fromarray((adjusted_image * 255).astype(np.uint8))
            updated_image.save(current_image)  # Overwrite with edits

            # Update UI
            uploaded_image.src = current_image
            page.update()
            print(np_image)
            print(exposure_stops)
            print(contrast_value)

    file_picker = ft.FilePicker(on_result=upload_image)
    page.overlay.append(file_picker)

    upload_button = ft.ElevatedButton("Upload Image", on_click=lambda _: file_picker.pick_files(allow_multiple=False))
    compare_button = ft.ElevatedButton("Compare")
    library_button = ft.ElevatedButton("Library", on_click=lambda _: page.go("/gallery"))
    submit_button = ft.ElevatedButton("Submit & Apply", on_click=apply_edits)

    def editor_view():
        uploaded_image.src = current_image if current_image else None
        return ft.Row(
            [
                ft.Column(
                    [
                        uploaded_image,
                        upload_button,
                        exposure_slider,
                        contrast_slider,
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Column(
                    [
                        compare_button,
                        library_button,
                        submit_button,
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            expand=True,
        )

    page.views.append(ft.View("/", [editor_view()]))

    def gallery_view(page):
        grid = ft.GridView(expand=True, max_extent=150, child_aspect_ratio=1, spacing=10, run_spacing=10)

        def select_image(image_path):
            global current_image
            current_image = image_path
            uploaded_image.src = image_path
            page.update()
            reset_sliders()
            page.go("/")

        for img_path in get_images():  # Get stored images from database
            if os.path.exists(img_path):  # Ensure file still exists
                img_container = ft.GestureDetector(
                    content=ft.Image(src=img_path, width=150, height=150, fit=ft.ImageFit.CONTAIN),
                    on_tap=lambda e, img_path=img_path: select_image(img_path)
                )
                grid.controls.append(img_container)

        back_button = ft.ElevatedButton("Back", on_click=lambda _: page.go("/"))
        page.views.append(ft.View("/gallery", [back_button, grid]))

    def route_change(route):
        page.views.clear()
        if page.route == "/gallery":
            gallery_view(page)
        else:
            page.views.append(ft.View("/", [editor_view()]))
        page.update()

    page.on_route_change = route_change
    page.go(page.route)

ft.app(target=main, view=ft.WEB_BROWSER)
