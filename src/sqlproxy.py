from functools import *
from itertools import *
from typing import Optional

import mysql.connector


def save_database(cursor):
    cursor.execute('SELECT DATABASE();')
    last_database = cursor.fetchall()[0][0]

    return last_database


def use_database(cursor, database):
    cursor.execute('USE {};'.format(database))


def restore_database(cursor, database):
    cursor.execute('USE {};'.format(database))


def decode_bytes(value):
    if isinstance(value, str):
        return value

    if isinstance(value, bytearray) or isinstance(value, bytes):
        return value.decode('utf-8')

    return value


class TableRow:
    def __init__(self):
        self.attributes = []
        self.values = []


class TableAttribute:
    def __init__(self):
        self.name = ''
        self.type = ''
        self.can_have_null = False
        self.is_primary_key = False
        self.is_foreign_key = False
        self.fk_table = None
        self.fk_attribute = None
        self.fk_values: list = []

    def get_fk_values(self, cursor):
        if not self.is_foreign_key:
            return None

        last_database = save_database(cursor)

        cursor.execute('SELECT DISTINCT {0} FROM {1};'.format(self.fk_attribute, self.fk_table))
        results = cursor.fetchall()

        restore_database(cursor, last_database)
        return [row[0] for row in results]


class SQLTableCache:
    RESULT_OK = 'RESULT_OK'

    def __init__(self, cursor, database, table):
        self.table = table
        self.database = database

        last_database = save_database(cursor)

        # Switch database
        use_database(cursor, database)

        # Get attributes
        cursor.execute('DESCRIBE {};'.format(table))
        self.attributes: list = cursor.fetchall()

        # Get tuples
        cursor.execute('SELECT * FROM {};'.format(table))
        self.tuples: list = cursor.fetchall()

        # Get foreign key info
        cursor.execute('USE INFORMATION_SCHEMA;')
        cursor.execute(
            'SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME '
            'FROM KEY_COLUMN_USAGE '
            'WHERE TABLE_SCHEMA = "{0}" '
            'AND TABLE_NAME = "{1}" '
            'AND REFERENCED_COLUMN_NAME IS NOT NULL;'.format(database, table)
        )
        self.fk_info = cursor.fetchall()
        cursor.execute('USE {};'.format(self.database))

        # Decode DESCRIBE attribute types

        for i in range(0, len(self.attributes)):
            self.attributes[i] = tuple([decode_bytes(col) for col in self.attributes[i]])

        restore_database(cursor, last_database)
        return

    def get_attr_info(self, attr) -> Optional[TableAttribute]:
        attr_row = None

        if isinstance(attr, int):
            attr_row = self.attributes[attr]
        else:
            for row in self.attributes:
                if row[0] == attr:
                    attr_row = row
                    break
        if attr_row is None:
            return None

        is_fk = False
        fk_table = ''
        fk_attr = ''

        for row in self.fk_info:
            if row[0] == attr_row[0]:
                is_fk = True
                fk_table = row[1]
                fk_attr = row[2]
                break

        info = TableAttribute()
        info.name = attr_row[0]
        info.type = attr_row[1]
        info.can_have_null = attr_row[2] == 'YES'
        info.is_primary_key = attr_row[3] == 'PRI'
        info.is_foreign_key = is_fk
        info.fk_table = fk_table
        info.fk_attribute = fk_attr
        return info

    def get_row(self, index):
        if index not in range(0, len(self.tuples)):
            return None

        row = TableRow()
        row.attributes = [row[0] for row in self.attributes]
        row.values = self.tuples[index]

        return row

    def get_next_pk(self):
        pk_list = []
        pk_type = []
        pk_index = []

        for i in range(0, len(self.attributes)):
            if self.attributes[i][3] == 'PRI':
                pk_list.append(self.attributes[i][0])
                pk_type.append(self.attributes[i][1])
                pk_index.append(i)

        if len(pk_list) != 1:
            return None  # Can't auto-generate composite PKs

        if pk_type[0] != 'int':
            return None  # Can't auto-generate non-int PKs

        return max([int(row[pk_index[0]]) for row in self.tuples]) + 1


class MySQLTableProxy:
    RESULT_OK = 'RESULT_OK'

    def __init__(self, cursor, database, table):
        self.cursor = cursor
        self.database = database
        self.table = table
        self.__cache = SQLTableCache(cursor, database, self.table)

    def get_cache(self):
        if self.__cache is None:
            self.__cache = SQLTableCache(self.cursor, self.database, self.table)

        return self.__cache

    def invalidate_cache(self):
        self.__cache = None

    def get_attr_info(self, attr):
        sqlcache = self.get_cache()
        return sqlcache.get_attr_info(attr)

    def get_row(self, index):
        sqlcache = self.get_cache()
        return sqlcache.get_row(index)

    def get_next_pk(self):
        sqlcache = self.get_cache()
        return sqlcache.get_next_pk()

    def delete_row(self, index):
        sqlcache = self.get_cache()
        row = sqlcache.get_row(index)

        if row is None:
            return False

        attr_count = len(row.attributes)

        statement = 'DELETE FROM {}'.format(self.table)
        statement += ' WHERE '
        for i in range(0, attr_count):
            statement += '{0} = %s '.format(row.attributes[i])

            if i + 1 < attr_count:
                statement += 'AND '

        statement += ';'

        self.invalidate_cache()

        last_database = save_database(self.cursor)
        use_database(self.cursor, self.database)

        result = SQLTableCache.RESULT_OK
        try:
            self.cursor.execute(statement, tuple(row.values))
        except mysql.connector.Error as e:
            print('Failed to execute statement')
            result = str(e)

        restore_database(self.cursor, last_database)

        return result

    def add_row(self, row: TableRow):
        if row is None or len(row.values) != len(row.attributes):
            return False

        attr_count = len(row.attributes)

        statement = 'INSERT INTO {} '.format(self.table)

        statement += '('
        for i in range(0, attr_count):
            statement += row.attributes[i]

            if i + 1 < attr_count:
                statement += ', '

        statement += ')'

        statement += ' VALUES ('
        for i in range(0, attr_count):
            statement += '%s'

            if i + 1 < attr_count:
                statement += ', '

        statement += ');'

        self.invalidate_cache()

        last_database = save_database(self.cursor)
        use_database(self.cursor, self.database)

        result = SQLTableCache.RESULT_OK
        try:
            self.cursor.execute(statement, tuple(row.values))
        except mysql.connector.Error as e:
            print('Failed to execute statement')
            result = str(e)

        restore_database(self.cursor, last_database)
        return result

    def edit_row(self, index, row: TableRow):
        sqlcache = self.get_cache()
        last_row = sqlcache.get_row(index)

        if last_row is None:
            return False

        if row is None or len(row.values) != len(row.attributes):
            return False

        attr_count = len(row.attributes)

        statement = 'UPDATE {} SET '.format(self.table)

        for i in range(0, attr_count):
            statement += '{} = %s'.format(row.attributes[i])

            if i + 1 < attr_count:
                statement += ', '

        statement += ' WHERE '
        for i in range(0, attr_count):
            statement += '{} = %s'.format(last_row.attributes[i])

            if i + 1 < attr_count:
                statement += ' AND '

        statement += ';'

        self.invalidate_cache()

        last_database = save_database(self.cursor)
        use_database(self.cursor, self.database)

        result = SQLTableCache.RESULT_OK
        try:
            params = row.values.copy()
            params.extend(last_row.values)
            self.cursor.execute(statement, tuple(params))
        except mysql.connector.Error as e:
            print('Failed to execute statement')
            result = str(e)

        restore_database(self.cursor, last_database)
        return result
