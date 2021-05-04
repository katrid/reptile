import pyodbc

from .connection import BaseConnection


class OdbcConnection(BaseConnection):
    _connection = None
    param_marker = '?'

    @property
    def connection(self):
        if self._connection is None:
            self._connection = pyodbc.connect(self.connection_string)
        return self._connection

    def execute(self, sql, *args, **kwargs):
        conn = self.connection
        cur = conn.cursor()
        cur.execute(sql, *args, **kwargs)
        return cur.fetchall()
