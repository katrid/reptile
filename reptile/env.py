import re
import textwrap
import datetime
from jinja2 import Environment


class EnvironmentSettings:
    env = Environment()
    env.cache = None
    env.globals['str'] = str
    env.globals['datetime'] = datetime.datetime
    env.globals['date'] = datetime.date
    env.globals['time'] = datetime.time
    env.globals['re'] = re
    env.globals['textwrap'] = textwrap
    error_text = '-'
