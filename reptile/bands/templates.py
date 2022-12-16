from decimal import Decimal
import datetime

from jinja2 import pass_context

from .widgets import Text
import reptile


@pass_context
def finalize(context, val):
    this = context.parent.get('this')
    if val and isinstance(this, Text):
        if disp := this.display_format:
            if isinstance(val, (Decimal, float)) and disp.kind == 'Numeric':
                return f'{{:{disp.format}}}'.format(val)
            if isinstance(val, (datetime.date, datetime.datetime)) and disp.kind == 'DateTime':
                return val.strftime(disp.format)
    if val is None:
        return ''
    if isinstance(val, Decimal):
        return '%.2f' % val
    if isinstance(val, float):
        return '%.2f' % val
    return val


reptile.EnvironmentSettings.env.finalize = finalize
