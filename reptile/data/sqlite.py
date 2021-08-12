from .connection import BaseConnection
from .datasource import SqlDataSource


class SqliteConnection(BaseConnection):
    def __init__(self, dbname=None, db=None):
        self._dbname = dbname
        self._conn = db

    def cursor(self):
        return self._conn.cursor()

    def create_datasource(self, name=None, sql=None):
        return SqlDataSource(name, sql=sql, connection=self)
