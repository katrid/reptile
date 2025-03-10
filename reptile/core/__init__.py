from .base import *
from .reports import *
from reptile import EnvironmentSettings
from reptile.utils.text import format_mask


EnvironmentSettings.env.globals['format_mask'] = format_mask
