"""Config Flow para Gestor Energético."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_GRID_SENSOR,
    CONF_PROD_SENSOR,
    CONF_POWER_VALLE,
    CONF_POWER_PUNTA,
)

_LOGGER = logging.getLogger(__name__)

class GestorEnergeticoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestión de la configuración en UI."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Paso inicial de configuración."""
        errors = {}
        
        # Si ya se ha introducido input (el usuario pulsó Enviar)
        if user_input is not None:
            # Validaciones extra si fueran necesarias (ej. si los sensores existen)
            return self.async_create_entry(title="Gestor Energético", data=user_input)

        # Esquema del formulario
        data_schema = vol.Schema({
            vol.Required(CONF_GRID_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_PROD_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_POWER_VALLE, default=3.0): vol.Coerce(float),
            vol.Required(CONF_POWER_PUNTA, default=4.0): vol.Coerce(float),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
