import os
import sqlite3

from directory_management import generate_persist_dir

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(generate_persist_dir(), 'images.db'), check_same_thread=False)
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

    def update(self, table, column: list, value: list, condition, commit=True):
        self.cursor.execute(f'UPDATE {table} SET {", ".join([f"{column[i]} = {value[i]}" for i in range(len(column))])} WHERE {condition}')
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
            return
        self.insert('images', [{'path': _} for _ in new_images], list_=True, dict_=True)
        placeholders = ', '.join('?' for _ in new_images)
        ids = self.select('images', ['id'], f'path IN ({placeholders})', tuple(new_images))
        ids = [_[0] for _ in ids]
        ids.sort()
        return ids, new_images

    def get_params(self, image_id):
        return self.select('images', ['exposure', 'contrast', 'white_levels', 'highlights', 'shadows', 'black_levels', 'saturation'], 'id = ?', (image_id,))
