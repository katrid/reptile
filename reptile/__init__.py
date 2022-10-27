from jinja2 import Environment


class EnvironmentSettings:
    env = Environment()
    env.cache = None
    env.globals['str'] = str
    error_text = '-'

