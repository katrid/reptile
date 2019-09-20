from .core import Connection


class OdbcConnection(Connection):
    _connection = None

    @property
    def connection(self):
        import pyodbc
        if self._connection is None:
            self._connection = pyodbc.connect(self.connection_string)
        return self._connection

    def execute(self, sql, *args, **kwargs):
        conn = self.connection
        cur = conn.cursor()
        cur.execute(sql, *args, **kwargs)
        return cur.fetchall()
