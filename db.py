import sqlite3
import logging
from sqlite3 import Error
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("database")


class DB:
    """
    Singleton class for managing a SQLite database connection.

    This class ensures that only one instance of the database connection is created.

    Usage:
    db_instance = DB.get_instance()
    """

    __instance = None

    def __new__(cls):
        """
        Overrides the default __new__ method to implement the singleton pattern.

        :return: The singleton instance of the DB class.
        :rtype: DB
        """
        if cls.__instance is None:
            cls.__instance = super(DB, cls).__new__(cls)
            cls.__instance.connection = None

            try:
                # Attempt to connect to the SQLite database
                cls.__instance.connection = sqlite3.connect(f'data/data.db')
                print('Connection to SQLite DB successful')
            except Error as e:
                print(f'The error "{e}" occurred')

        return cls.__instance

    @staticmethod
    def get_instance():
        """
        Static method to retrieve the singleton instance of the DB class.

        :return: The singleton instance of the DB class.
        :rtype: DB
        """
        if DB.__instance is None:
            DB.__instance = DB()

        return DB.__instance

    @staticmethod
    def create_connection(path):
        """
        Static method to create a SQLite database connection.

        :param path: The path to the SQLite database file.
        :type path: str

        :return: The SQLite database connection.
        :rtype: sqlite3.Connection or None
        """
        connection = None

        try:
            # Attempt to connect to the SQLite database
            connection = sqlite3.connect(path)
            print('Connection to SQLite DB successful')
        except Error as e:
            print(f'The error "{e}" occurred')

        return connection

    def get_connection(self, reset=None):
        """
        Retrieves the existing SQLite database connection or creates a new one if needed.

        :param reset: If set to True, forces the creation of a new connection.
        :type reset: bool or None

        :return: The SQLite database connection.
        :rtype: sqlite3.Connection or None
        """
        # if reset is not None or self.connection is None:
            # self.connection = None
            # self.connection = self.create_connection(f'data/data.db')
        return self.create_connection(f'data/data.db')
        # else:
        #     return self.connection


class Access:
    """
    Class for handling basic CRUD operations on a SQLite database table.

    Usage:
    access_instance = Access('table_name')
    """

    def __init__(self, table: str):
        """
        Initializes a new instance of the Access class.

        :param table: The name of the database table to operate on.
        :type table: str
        """
        self.table = table

    def insert(self, columns, values):
        """
        Inserts a new row into the database table.

        :param columns: The list of column names to insert data into.
        :type columns: List[str]
        :param values: The list of values corresponding to the columns.
        :type values: List[Union[str, int, float, None]]

        :return: None
        """
        conn = DB.get_instance().get_connection()
        cursor = conn.cursor()

        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in values])
        query = f'INSERT INTO {self.table} ({columns_str}) VALUES ({placeholders})'

        try:
            cursor.execute(query, values)
            conn.commit()
            log.info('Data inserted successfully!')
        except sqlite3.Error as e:
            log.error(f'Error inserting data: {e}')

    def select(self, columns=None, condition=None) -> List[list]:
        """
        Retrieves data from the database table based on specified columns and conditions.

        :param columns: The list of column names to retrieve. If None, retrieves all columns.
        :type columns: Optional[List[str]]
        :param condition: The condition to filter rows. If None, retrieves all rows.
        :type condition: Optional[str]

        :return: A list of rows matching the query.
        :rtype: List[list]
        """
        conn = DB.get_instance().get_connection()
        cursor = conn.cursor()

        if columns:
            columns_str = ', '.join(columns)
        else:
            columns_str = '*'

        query = f'SELECT {columns_str} FROM {self.table}'

        if condition:
            query += f' WHERE {condition}'

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

        except sqlite3.Error as e:
            log.info(f'Error selecting data: {e}')

    def update(self, update_columns, new_values, condition):
        """
        Updates rows in the database table based on a specified condition.

        :param update_columns: The list of column names to update.
        :type update_columns: List[str]
        :param new_values: The list of new values corresponding to the update columns.
        :type new_values: List[Union[str, int, float, None]]
        :param condition: The condition to filter rows for the update.
        :type condition: str

        :return: None
        """
        conn = DB.get_instance().get_connection()
        cursor = conn.cursor()

        set_clause = ', '.join([f'{col} = ?' for col in update_columns])
        query = f'UPDATE {self.table} SET {set_clause} WHERE {condition}'

        try:
            cursor.execute(query, new_values)
            conn.commit()
            log.info('Data updated successfully!')

        except sqlite3.Error as e:
            log.info(f'Error updating data: {e}')

    def delete(self, condition):
        """
        Deletes rows from the database table based on a specified condition.

        :param condition: The condition to filter rows for deletion.
        :type condition: str

        :return: None
        """
        conn = DB.get_instance().get_connection()
        cursor = conn.cursor()

        query = f'DELETE FROM {self.table} WHERE {condition}'

        try:
            cursor.execute(query)
            conn.commit()

        except sqlite3.Error as e:
            log.info(f'Error deleting data: {e}')

    def exists(self, column: str, value: str):
        """
        Checks if a value exists in a specific column of the database table.

        :param column: The column to check for the value.
        :type column: str
        :param value: The value to check for existence.
        :type value: str

        :return: True if the value exists, False otherwise.
        :rtype: bool
        """
        conn = DB.get_instance().get_connection()
        c = conn.cursor()

        query = f'SELECT COUNT(1) FROM {self.table} WHERE {column}=?'
        c.execute(query, (value,))

        if c.fetchone()[0] == 1:
            return True
        else:
            return False

    def unique_pk(self):
        """
        Generates a unique primary key value by temporarily inserting a dummy row.

        :return: The next unique primary key value.
        :rtype: int or None
        """
        conn = DB.get_instance().get_connection()
        c = conn.cursor()

        try:
            c.execute(f'INSERT INTO {self.table} (name, income) VALUES ("DUMMY", 9999)')
            next_value = c.lastrowid
            conn.rollback()

            return next_value
        except sqlite3.Error as e:
            log.info(f"Error: {e}")


def create_tables():
    USER_TABLE: str = (
        'create table IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT not null, '
        'password TEXT not null, firstName TEXT not null, lastName TEXT not null)')
    PAGE_TABLE: str = (
        'create table IF NOT EXISTS pages (page_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT not null UNIQUE, '
        'markdown TEXT not null, date DATE not null, editor TEXT not null, category TEXT not null)')

    conn = DB.get_instance().get_connection()

    c = conn.cursor()

    c.execute(USER_TABLE)
    c.execute(PAGE_TABLE)

    conn.commit()
