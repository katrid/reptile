import re
from decimal import Decimal
import textwrap
import datetime
from jinja2 import Environment
from reptile.utils.text import format_mask, format_number, _format_number, display_format


def default_format(value):
    if isinstance(value, (Decimal, float)):
        return _format_number(
            value, EnvironmentSettings.DecimalSettings.decimal_pos,
            EnvironmentSettings.DecimalSettings.thousand_sep,
            EnvironmentSettings.DecimalSettings.decimal_sep
        )
    return str(value)


class EnvironmentSettings:
    env = Environment()
    env.cache = None
    env.globals['str'] = str
    env.globals['datetime'] = datetime.datetime
    env.globals['date'] = datetime.date
    env.globals['time'] = datetime.time
    env.globals['re'] = re
    env.globals['textwrap'] = textwrap
    env.filters['display_format'] = display_format
    error_text = '-'

    class DecimalSettings:
        decimal_pos = 2
        thousand_sep = ','
        decimal_sep = '.'
