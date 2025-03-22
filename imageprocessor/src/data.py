import os
import sqlite3
from directory_management import generate_persist_dir

class Database:
    """
    Singleton class for managing a SQLite database connection and operations.

    This class implements a strict singleton pattern so that only one instance
    of the Database is created during the application's lifecycle. It handles
    basic CRUD operations and database schema initialization.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Override __new__ to implement the singleton pattern.

        If an instance does not exist, create one and initialize it.
        Otherwise, return the existing instance.

        Returns:
            Database: The singleton instance of the Database class.
        """
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()  # Initialize only once
        return cls._instance

    def _initialize(self):
        """
        Initialize the database connection and schema.

        This method sets up the SQLite connection, creates the cursor, and
        initializes the necessary tables (images and CONFIG) if they do not exist.
        """
        self.conn = sqlite3.connect(
            os.path.join(generate_persist_dir(), 'images.db'),
            check_same_thread=False
        )
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    exposure FLOAT DEFAULT 0,
                    contrast INTEGER DEFAULT 0,
                    highlights INTEGER DEFAULT 0,
                    shadows INTEGER DEFAULT 0,
                    black_levels INTEGER DEFAULT 0
                )
            ''')
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS CONFIG (
                    key TEXT NOT NULL PRIMARY KEY,
                    value TEXT
                )
            ''')
        self.conn.commit()

    def execute(self, query, replacement=None):
        """
        Execute an SQL query with optional parameter replacements.

        Args:
            query (str): The SQL query to be executed.
            replacement (tuple, optional): Optional tuple of parameters to safely
                replace placeholders in the query.

        Returns:
            sqlite3.Cursor: The cursor after executing the query.
        """
        if replacement is None:
            return self.cursor.execute(query)
        else:
            return self.cursor.execute(query, replacement)

    def commit(self):
        """
        Commit the current transaction to the database.

        This method should be called after performing operations that modify the database.
        """
        self.conn.commit()

    def insert(self, table, values, list_=False, dict_=False, commit=True):
        """
        Insert data into a table.

        The method supports inserting data provided as a single value tuple,
        a dictionary mapping columns to values, or a list of such dictionaries.

        Args:
            table (str): The table name where data will be inserted.
            values: The values to insert (format depends on list_ and dict_ flags).
            list_ (bool): If True, `values` is expected to be a list of values/dictionaries.
            dict_ (bool): If True, `values` is expected to be a dictionary (or list of dictionaries)
                          mapping column names to their respective values.
            commit (bool): Whether to commit the transaction after inserting.

        Returns:
            int: The last row ID inserted.
        """
        if not dict_:
            self.cursor.execute(f'INSERT INTO {table} VALUES (?)', values)
        elif not list_ and dict_:
            columns = ', '.join(values.keys())
            placeholder = ', '.join(['?' for _ in range(len(values))])
            self.cursor.execute(
                f'INSERT INTO {table} ({columns}) VALUES ({placeholder})',
                tuple(values.values())
            )
        elif list_ and dict_:
            columns = ', '.join(values[0].keys())
            placeholder = ', '.join(['?' for _ in range(len(values[0]))])
            self.cursor.executemany(
                f'INSERT INTO {table} ({columns}) VALUES ({placeholder})',
                tuple([tuple(item.values()) for item in values])
            )
        if commit:
            self.commit()
        return self.cursor.lastrowid

    def delete(self, table, condition, replacement=None, commit=True):
        """
        Delete records from a table based on a condition.

        Args:
            table (str): The table name from which to delete records.
            condition (str): The SQL condition (WHERE clause) to identify which records to delete.
            replacement (tuple, optional): Optional tuple of parameters to safely replace placeholders in the condition.
            commit (bool): Whether to commit the transaction after deletion.
        """
        if replacement is None:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}')
        else:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}', replacement)
        if commit:
            self.commit()

    def drop(self, table, commit=True):
        """
        Drop an entire table from the database.

        Args:
            table (str): The table name to be dropped.
            commit (bool): Whether to commit the transaction after dropping the table.
        """
        self.cursor.execute(f'DROP TABLE {table}')
        if commit:
            self.commit()

    def select(self, table, columns: list, condition=None, replacement=None):
        """
        Retrieve records from a table.

        Args:
            table (str): The table name from which to select data.
            columns (list): List of column names to retrieve.
            condition (str, optional): SQL condition (WHERE clause) to filter the results.
            replacement (tuple, optional): Optional tuple of parameters to safely replace placeholders in the condition.

        Returns:
            list: A list of tuples representing the selected rows.
        """
        if condition is not None:
            if replacement is not None:
                return self.cursor.execute(
                    f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}',
                    replacement
                ).fetchall()
            else:
                return self.cursor.execute(
                    f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}'
                ).fetchall()
        else:
            return self.cursor.execute(
                f'SELECT {", ".join(columns)} FROM {table}'
            ).fetchall()

    def update(self, table, column: list, value: list, condition, replacement=None, commit=True):
        """
        Update records in a table based on a condition.

        Args:
            table (str): The table name where records will be updated.
            column (list): List of column names to update.
            value (list): List of values corresponding to the columns.
            condition (str): SQL condition (WHERE clause) to identify which records to update.
            replacement (tuple, optional): Optional tuple of parameters to safely replace placeholders in the condition.
            commit (bool): Whether to commit the transaction after updating.
        """
        set_clause = ", ".join([f"{column[i]} = {value[i]}" for i in range(len(column))])
        if replacement is None:
            self.cursor.execute(
                f'UPDATE {table} SET {set_clause} WHERE {condition}'
            )
        else:
            self.cursor.execute(
                f'UPDATE {table} SET {set_clause} WHERE {condition}', replacement
            )
        if commit:
            self.commit()

    def import_image(self, paths):
        """
        Import images into the database if they do not already exist.

        For each path provided, the method checks if the image exists in the database.
        If not, it inserts the new image path into the 'images' table.

        Args:
            paths (list): A list of image paths to be imported.

        Returns:
            tuple or None: A tuple containing a sorted list of new image IDs and the new image paths,
                           or None if no new images were imported.
        """
        new_images = []
        for path in paths:
            exist = self.select('images', ['path'], 'path = ?', (path,))
            if not exist:
                new_images.append(path)
        if not new_images:
            return None
        self.insert('images', [{'path': _} for _ in new_images], list_=True, dict_=True)
        placeholders = ', '.join('?' for _ in new_images)
        ids = self.select('images', ['id'], f'path IN ({placeholders})', tuple(new_images))
        ids = [_[0] for _ in ids]
        ids.sort()
        return ids, new_images

    def get_params(self, image_id):
        """
        Retrieve image parameters for a given image ID.

        Args:
            image_id (int): The ID of the image whose parameters are to be retrieved.

        Returns:
            list: A list containing the exposure, contrast, highlights, shadows, and black_levels parameters.
        """
        return self.select(
            'images',
            ['exposure', 'contrast', 'highlights', 'shadows', 'black_levels'],
            'id = ?',
            (image_id,)
        )

    def set_config(self, key, value):
        """
        Set or update a configuration value in the CONFIG table.

        If the configuration with the specified key exists, its value is updated.
        Otherwise, a new configuration entry is inserted.

        Args:
            key (str): The configuration key.
            value (str): The value to set for the given key.
        """
        exists = self.select('config', ['value'], 'key = ?', (key,))
        if exists:
            self.update('config', ['value'], [value], f'key = "{key}"')
        else:
            self.insert('config', {'key': key, 'value': value}, dict_=True)

    def get_config(self, key):
        """
        Retrieve the configuration value for a given key.

        Args:
            key (str): The configuration key.

        Returns:
            list: A list containing the configuration value.
        """
        return self.select('config', ['value'], f'key = "{key}"')

    def close(self):
        """
        Close the database connection and reset the singleton instance.

        This method closes the connection to the SQLite database and sets the
        singleton instance to None, allowing for re-instantiation if needed.
        """
        self.conn.close()
        Database._instance = None
