from .core import Connection


class OdbcConnection(Connection):
    _connection = None

    @property
    def connection(self):
        import pyodbc
        if self._connection is None:
            self._connection = pyodbc.connect(self.connectionString)
        return self._connection

    def execute(self, sql):
        conn = self.connection
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()
