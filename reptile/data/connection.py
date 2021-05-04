from reptile.engine import ReportObject


class BaseConnection(ReportObject):
    connection_string: str = None
    param_marker = '%s'

    def execute(self, sql):
        raise NotImplemented()


