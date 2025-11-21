"""Sensores para Gestor Energético."""
import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfEnergy, UnitOfElectricCurrent
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from .const import (
    DOMAIN,
    CONF_GRID_SENSOR,
    CONF_PROD_SENSOR,
    CONF_POWER_VALLE,
    CONF_POWER_PUNTA,
    TARIFF_PUNTA,
    TARIFF_LLANO,
    TARIFF_VALLE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Configura los sensores."""
    config = entry.data
    grid_entity = config[CONF_GRID_SENSOR]
    prod_entity = config[CONF_PROD_SENSOR]
    p_valle = config[CONF_POWER_VALLE]
    p_punta = config[CONF_POWER_PUNTA]

    sensors = [
        TarifaSensor(hass, p_valle, p_punta),
        BalanceNetoRealSensor(hass, grid_entity),
        BalanceNetoEstimadoSensor(hass, grid_entity),
        IntensidadExcedenteSensor(hass, grid_entity),
        ConsumoHogarDiarioSensor(hass, grid_entity, prod_entity),
        EnergiaImportadaDiariaSensor(hass, grid_entity),
        ExcedenteDiarioSensor(hass, grid_entity),
    ]
    async_add_entities(sensors)


class TarifaSensor(SensorEntity):
    """Sensor que indica el tramo horario actual (20TD)."""
    _attr_has_entity_name = True
    _attr_name = "Tramo Horario"
    _attr_icon = "mdi:clock-time-four-outline"

    def __init__(self, hass, p_valle, p_punta):
        self.hass = hass
        self._p_valle = p_valle
        self._p_punta = p_punta
        self._attr_unique_id = f"{DOMAIN}_tariff_period"
        self._state = None
        self._potencia_max = 0

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {
            "potencia_contratada": self._potencia_max,
            "region": "ES"
        }

    async def async_added_to_hass(self):
        """Actualizar cada minuto."""
        self.async_on_remove(
            async_track_time_interval(self.hass, self._update_tariff, timedelta(minutes=1))
        )
        await self._update_tariff(dt_util.now())

    async def _update_tariff(self, now):
        """Lógica 20TD España."""
        is_holiday = False
        workday_sensor = self.hass.states.get("binary_sensor.workday_sensor")
        if workday_sensor and workday_sensor.state == "off":
            is_holiday = True

        hour = now.hour
        weekday = now.weekday() # 0=Lunes, 6=Domingo

        # Fines de semana o festivos -> VALLE
        if weekday >= 5 or is_holiday:
            self._state = TARIFF_VALLE
            self._potencia_max = self._p_valle
        else:
            # Laborables
            if 0 <= hour < 8:
                self._state = TARIFF_VALLE
                self._potencia_max = self._p_valle
            elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):
                self._state = TARIFF_LLANO
                self._potencia_max = self._p_punta
            else:
                self._state = TARIFF_PUNTA
                self._potencia_max = self._p_punta
        
        self.async_write_ha_state()


class BalanceNetoRealSensor(RestoreEntity, SensorEntity):
    """Calcula el Balance Neto Horario (Real) acumulado en la hora actual."""
    _attr_name = "Balance Neto Horario (Real)"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_unique_id = f"{DOMAIN}_net_balance_real"
    _attr_icon = "mdi:scale-balance"

    def __init__(self, hass, grid_entity):
        self.hass = hass
        self._grid_entity = grid_entity
        self._attr_native_value = 0.0
        self._last_update = None
        self._last_power = 0.0

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # Restaurar estado si existe
        if (last_state := await self.async_get_last_state()) and last_state.state not in (None, "unknown", "unavailable"):
             try:
                self._attr_native_value = float(last_state.state)
             except ValueError:
                self._attr_native_value = 0.0
        
        self._last_update = dt_util.now()
        
        # Escuchar cambios en el sensor Grid
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._grid_entity], self._on_grid_change)
        )
        # Chequeo cada segundo para reset de hora
        self.async_on_remove(
            async_track_time_interval(self.hass, self._check_hour_reset, timedelta(seconds=1))
        )

    async def _check_hour_reset(self, now):
        """Si cambia la hora, reset a 0."""
        if self._last_update and now.hour != self._last_update.hour:
            self._attr_native_value = 0.0
            self._last_update = now
            self.async_write_ha_state()

    async def _on_grid_change(self, event):
        """Calcular integral (Energía = Potencia * Tiempo)."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in ("unknown", "unavailable"):
            return

        try:
            # Grid: Positivo = Excedente (Venta), Negativo = Consumo (Compra)
            current_power = float(new_state.state)
        except ValueError:
            return

        now = dt_util.now()
        if self._last_update:
            time_diff = (now - self._last_update).total_seconds() / 3600.0 # Horas
            # Regla del trapecio simple para la integral
            energy_increment = ((self._last_power + current_power) / 2) * time_diff
            self._attr_native_value += energy_increment

        self._last_power = current_power
        self._last_update = now
        self.async_write_ha_state()


class BalanceNetoEstimadoSensor(SensorEntity):
    """Estima cómo terminará la hora actual."""
    _attr_name = "Balance Neto Horario (Estimación)"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_unique_id = f"{DOMAIN}_net_balance_estimated"
    _attr_icon = "mdi:chart-line"

    def __init__(self, hass, grid_entity):
        self.hass = hass
        self._grid_entity = grid_entity

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_time_interval(self.hass, self._update_estimation, timedelta(seconds=10))
        )

    async def _update_estimation(self, now):
        real_balance_sensor = f"sensor.balance_neto_horario_real" # Asumimos naming convention
        # Buscar el sensor hermano "Real"
        # NOTA: En una integración real es mejor buscar por unique_id o pasar la instancia, 
        # pero por simplicidad usaremos el state machine.
        
        # Buscamos nuestra propia instancia 'real' en hass.data o por entity_id standard si ha sido creado
        # Para evitar complejidad, leemos el grid directo.
        
        grid_state = self.hass.states.get(self._grid_entity)
        real_balance_state = self.hass.states.get("sensor.balance_neto_horario_real") # Nombre default generado

        if not grid_state or not real_balance_state:
            return

        try:
            current_grid_w = float(grid_state.state) # +Venta, -Compra
            current_accumulated_wh = float(real_balance_state.state)
        except (ValueError, TypeError):
            return

        # Tiempo restante de la hora
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seconds_left = (next_hour - now).total_seconds()
        hours_left = seconds_left / 3600.0

        # Estimación = Acumulado + (Potencia_Actual * Tiempo_Restante)
        estimated_end = current_accumulated_wh + (current_grid_w * hours_left)
        
        self._attr_native_value = round(estimated_end, 2)
        self.async_write_ha_state()


class IntensidadExcedenteSensor(SensorEntity):
    """
    Amperios disponibles (a 240V) para encender cargas y terminar la hora en 0 Wh.
    Actualización cada 60 segundos.
    """
    _attr_name = "Intensidad Excedente"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_unique_id = f"{DOMAIN}_surplus_current"
    _attr_icon = "mdi:flash-outline"

    def __init__(self, hass, grid_entity):
        self.hass = hass
        self._grid_entity = grid_entity

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_time_interval(self.hass, self._calculate_surplus, timedelta(seconds=60))
        )

    async def _calculate_surplus(self, now):
        grid_state = self.hass.states.get(self._grid_entity)
        real_balance_state = self.hass.states.get("sensor.balance_neto_horario_real")

        if not grid_state or not real_balance_state:
            self._attr_native_value = 0.0
            return

        try:
            P_grid = float(grid_state.state) # +Venta, -Compra
            B_acc = float(real_balance_state.state) # Balance acumulado
        except (ValueError, TypeError):
            self._attr_native_value = 0.0
            return

        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seconds_left = (next_hour - now).total_seconds()
        
        if seconds_left < 60:
            # Evitar división por cero al final de la hora, asumimos 0
            self._attr_native_value = 0.0 
            self.async_write_ha_state()
            return

        hours_left = seconds_left / 3600.0

        # Fórmula: Queremos Balance Final = 0
        # 0 = B_acc + (P_grid - P_load) * hours_left
        # P_load = P_grid + (B_acc / hours_left)
        
        power_available_to_add = P_grid + (B_acc / hours_left)
        
        # Convertir W a Amperios (240V)
        amps_available = power_available_to_add / 240.0

        self._attr_native_value = round(amps_available, 2)
        self.async_write_ha_state()


class BaseDailySensor(RestoreEntity, SensorEntity):
    """Clase base para sensores diarios con reset a media noche."""
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    
    def __init__(self, hass, grid_entity):
        self.hass = hass
        self._grid_entity = grid_entity
        self._attr_native_value = 0.0
        self._last_update = None
        self._last_power_calc = 0.0

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and last_state.state not in (None, "unknown"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = 0.0
        
        self._last_update = dt_util.now()
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._grid_entity], self._on_change)
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._check_daily_reset, timedelta(minutes=1))
        )

    async def _check_daily_reset(self, now):
        if self._last_update and now.day != self._last_update.day:
            self._attr_native_value = 0.0
            self._last_update = now
            self.async_write_ha_state()

    async def _on_change(self, event):
        raise NotImplementedError


class ConsumoHogarDiarioSensor(BaseDailySensor):
    """Calcula Consumo Hogar = Produccion - Grid."""
    _attr_name = "Consumo Hogar Diario"
    _attr_unique_id = f"{DOMAIN}_daily_home_consumption"

    def __init__(self, hass, grid_entity, prod_entity):
        super().__init__(hass, grid_entity)
        self._prod_entity = prod_entity

    async def _on_change(self, event):
        # Necesitamos leer ambos sensores
        grid_state = self.hass.states.get(self._grid_entity)
        prod_state = self.hass.states.get(self._prod_entity)
        if not grid_state or not prod_state: return

        try:
            g_val = float(grid_state.state)
            p_val = float(prod_state.state)
        except: return

        # Consumo = Producción - Grid
        # Grid: +Venta, -Compra.
        # Ej: Prod 3000, Grid +1000 (Sobra) -> Consumo 2000.
        # Ej: Prod 0, Grid -500 (Falta) -> Consumo 0 - (-500) = 500.
        current_consumption_w = p_val - g_val
        
        if current_consumption_w < 0: current_consumption_w = 0 # Fisica imposible consumo negativo

        now = dt_util.now()
        time_diff = (now - self._last_update).total_seconds() / 3600.0
        energy = ((self._last_power_calc + current_consumption_w) / 2) * time_diff
        
        if energy > 0:
            self._attr_native_value += energy

        self._last_power_calc = current_consumption_w
        self._last_update = now
        self.async_write_ha_state()


class EnergiaImportadaDiariaSensor(BaseDailySensor):
    """Energía tomada de la red (Solo cuando Grid es negativo)."""
    _attr_name = "Energía Importada Diaria"
    _attr_unique_id = f"{DOMAIN}_daily_imported"

    async def _on_change(self, event):
        new_state = event.data.get("new_state")
        if not new_state: return
        try: val = float(new_state.state)
        except: return

        # Si Grid es negativo, estamos importando.
        # Queremos valor positivo de energía.
        current_import_w = abs(val) if val < 0 else 0.0

        now = dt_util.now()
        time_diff = (now - self._last_update).total_seconds() / 3600.0
        energy = ((self._last_power_calc + current_import_w) / 2) * time_diff

        if energy > 0:
            self._attr_native_value += energy

        self._last_power_calc = current_import_w
        self._last_update = now
        self.async_write_ha_state()


class ExcedenteDiarioSensor(BaseDailySensor):
    """Energía inyectada a la red (Solo cuando Grid es positivo)."""
    _attr_name = "Energía Excedente Diaria"
    _attr_unique_id = f"{DOMAIN}_daily_surplus"

    async def _on_change(self, event):
        new_state = event.data.get("new_state")
        if not new_state: return
        try: val = float(new_state.state)
        except: return

        # Si Grid es positivo, estamos exportando.
        current_export_w = val if val > 0 else 0.0

        now = dt_util.now()
        time_diff = (now - self._last_update).total_seconds() / 3600.0
        energy = ((self._last_power_calc + current_export_w) / 2) * time_diff

        if energy > 0:
            self._attr_native_value += energy

        self._last_power_calc = current_export_w
        self._last_update = now
        self.async_write_ha_state()
