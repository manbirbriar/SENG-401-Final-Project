import pytest
import sys
sys.path.append('imageprocessor/src')

from data import Database 

@pytest.fixture(scope="function")
def db():
    # Setup: create a new Database instance before each test
    db_instance = Database()
    yield db_instance
    # Teardown: clean up after the test
    db_instance.close()

def test_singleton(db):
    # Test that only one instance of Database is created
    db1 = Database()
    db2 = Database()
    
    # Assert that both instances are the same (Singleton behavior)
    assert db1 is db2, "Different instances of Database were created, Singleton pattern violated."

def test_database_initialization(db):
    # Test the database initialization (tables should exist)
    assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images';").fetchone() is not None
    assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CONFIG';").fetchone() is not None

def test_insert_image(db):
    # Test inserting a new image into the database
    image_path = "test_image_1.jpg"
    db.insert('images', {'path': image_path}, dict_=True)
    result = db.execute("SELECT path FROM images WHERE path = ?", (image_path,)).fetchone()
    assert result is not None
    assert result[0] == image_path

def test_delete_image(db):
    # Test deleting an image from the database
    image_path = "test_image_3.jpg"
    db.insert('images', {'path': image_path}, dict_=True)
    db.delete('images', 'path = ?', (image_path,))
    
    result = db.execute("SELECT path FROM images WHERE path = ?", (image_path,)).fetchone()
    assert result is None  # The image should be deleted

def test_update_image_exposure(db):
    # Test updating the exposure value of an image
    image_path = "test_image_4.jpg"
    db.insert('images', {'path': image_path, 'exposure': 0.5}, dict_=True)
    
    # Update the exposure
    db.update('images', ['exposure'], [1.5], 'path = ?', (image_path,))
    
    result = db.execute("SELECT exposure FROM images WHERE path = ?", (image_path,)).fetchone()
    assert result is not None
    assert result[0] == 1.5

def test_import_image(db):
    # Test importing images into the database
    paths = ["test_image_5.jpg", "test_image_6.jpg"]
    ids, new_images = db.import_image(paths)
    
    assert ids is not None
    assert len(ids) == len(new_images)
    assert set(new_images) == set(paths)  # Imported images should match paths



