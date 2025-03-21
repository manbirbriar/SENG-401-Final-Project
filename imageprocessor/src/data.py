import os
import sqlite3

from directory_management import generate_persist_dir

class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()  # Initialize only once
        return cls._instance

    def _initialize(self):
        self.conn = sqlite3.connect(os.path.join(generate_persist_dir(), 'images.db'), check_same_thread=False)
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
        if replacement is None:
            return self.cursor.execute(query)
        else:
            return self.cursor.execute(query, replacement)

    def commit(self):
        self.conn.commit()

    def insert(self, table, values, list_=False, dict_=False, commit=True):
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
        if commit:
            self.commit()
        return self.cursor.lastrowid

    def delete(self, table, condition, replacement=None, commit=True):
        if replacement is None:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}')
        else:
            self.cursor.execute(f'DELETE FROM {table} WHERE {condition}', replacement)
        if commit:
            self.commit()

    def drop(self, table, commit=True):
        self.cursor.execute(f'DROP TABLE {table}')
        if commit:
            self.commit()

    def select(self, table, columns: list, condition=None, replacement=None):
        if condition is not None:
            if replacement is not None:
                return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}', replacement).fetchall()
            else:
                return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table} WHERE {condition}').fetchall()
        else:
            return self.cursor.execute(f'SELECT {", ".join(columns)} FROM {table}').fetchall()

    def update(self, table, column: list, value: list, condition, replacement=None, commit=True):
        if replacement is None:
            self.cursor.execute(f'UPDATE {table} SET {", ".join([f"{column[i]} = {value[i]}" for i in range(len(column))])} WHERE {condition}')
        else:
            self.cursor.execute(f'UPDATE {table} SET {", ".join([f"{column[i]} = {value[i]}" for i in range(len(column))])} WHERE {condition}', replacement)
        if commit:
            self.commit()

    # custom
    def import_image(self, paths):
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
        return self.select('images', ['exposure', 'contrast', 'highlights', 'shadows', 'black_levels'], 'id = ?', (image_id,))

    def set_config(self, key, value):
        exists = self.select('config', ['value'], 'key = ?', (key,))
        if exists:
            self.update('config', ['value'], [value], f'key = "{key}"')
        else:
            self.insert('config', {'key': key, 'value': value}, dict_=True)

    def get_config(self, key):
        return self.select('config', ['value'], f'key = "{key}"')

    def close(self):
        self.conn.close()
        Database._instance = None
