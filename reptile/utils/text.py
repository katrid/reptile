from decimal import Decimal
import datetime

MASK_MAP = ['9', '0', '#']


def format_mask(mask: str, value):
    if not value:
        return value
    if not isinstance(value, str):
        value = str(value)
    s = ''
    i = 0
    l = len(value)
    for m in mask:
        if m in MASK_MAP:
            s += value[i] if l > i else ' '
            i += 1
        else:
            s += m
    return s


def _format_number(value: str | float | Decimal, decimal_pos: int, thousand_sep: str, decimal_sep: str):
    value = float(value or 0)
    tg = f'{value:,.0f}'
    if thousand_sep != ',':
        tg = tg.replace(',', thousand_sep)
    return tg + decimal_sep + ('{:.' + f'{decimal_pos}' + 'f}').format(value)[-decimal_pos:]


def format_number(mask: str, value: str | float | Decimal, thousand_sep: str = '.', decimal_sep: str = ','):
    decimal_pos = 0
    if '.' in mask:
        _, decs = mask.split('.')
        decimal_pos = len(decs)
    return _format_number(value, decimal_pos, thousand_sep, decimal_sep)


def display_format(value, fmt):
    from reptile.env import EnvironmentSettings
    dec_settings = EnvironmentSettings.DecimalSettings
    kind, fmt = fmt
    v = value
    if kind == 'Numeric':
        if fmt.startswith('{'):
            value = value if value else 0
            v = fmt.format(float(value))
            if '.' in v and dec_settings.decimal_sep != '.':
                return v.replace('.', '%').replace(',', dec_settings.thousand_sep).replace('%', dec_settings.decimal_sep)
    elif kind == 'DateTime':
        if isinstance(value, str):
            value = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        elif value is None:
            return ''
        return value.strftime(fmt)
    return str(value)
