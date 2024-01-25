import os
import sqlite3
import logging
from sqlite3 import Error
from typing import List
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('ROOT_FOLDER') + 'logs/app.log'),
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
                log.info('Connection to SQLite DB successful')
            except Error as e:
                log.info(f'The error "{e}" occurred')

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
            log.info('Connection to SQLite DB successful')
        except Error as e:
            log.info(f'The error "{e}" occurred')

        return connection

    def get_connection(self, reset=True):
        """
        Retrieves the existing SQLite database connection or creates a new one if needed.

        :param reset: If set to True, forces the creation of a new connection.
        :type reset: bool or None

        :return: The SQLite database connection.
        :rtype: sqlite3.Connection or None
        """
        if reset is not None or self.connection is None:
            self.__instance.connection = None
            self.__instance.connection = self.create_connection(f'data/data.db')
            return self.__instance.connection
        else:
            return self.__instance.connection


# TODO: Sanitize User Input
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

        query = f'INSERT INTO {self.table} ({", ".join(columns)}) VALUES ({", ".join([":param_" + str(i) for i in range(len(values))])})'

        params = {f'param_{i}': value for i, value in enumerate(values)}

        try:
            conn.execute(query, params)
            log.info('Data inserted successfully!')
        except Exception as e:
            log.info(f'Error inserting data: {e}')

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

        set_clause = ', '.join([f'{col} = :param_{i}' for i, col in enumerate(update_columns)])

        query = f'UPDATE {self.table} SET {set_clause} WHERE {condition}'

        params = {f'param_{i}': value for i, value in enumerate(new_values)}

        try:
            conn.execute(query, params)
            log.info('Data updated successfully!')
        except Exception as e:
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

        query = f'SELECT COUNT(1) FROM {self.table} WHERE {column} = :param_value'

        # Bind parameter to the query
        params = {'param_value': value}

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if cursor.fetchone()[0] == 1:
                return True
            else:
                return False
        except Exception as e:
            log.info(f'Error checking existence: {e}')
            return False


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
