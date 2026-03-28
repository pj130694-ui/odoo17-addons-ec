# product_import_service contains a plain Python mixin (no Odoo model);
# it is imported directly by import_log, not registered here.
from . import gs_product_tracking
from . import res_config_settings
from . import import_log
