# Gestor Energético 20TD 🇪🇸

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub version](https://img.shields.io/github/v/release/stoker2010/ha_gestor_energetico?style=for-the-badge&color=blue)](https://github.com/stoker2010/ha_gestor_energetico/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://github.com/stoker2010/ha_gestor_energetico)

**Gestor Energético** is the ultimate solution for Spanish households (20TD Tariff) with Solar PV. It unifies tariff management, Net Metering (Balance Neto), and surplus optimization into a single, powerful integration.

**Gestor Energético** es la solución definitiva para hogares en España (Tarifa 20TD) con placas solares. Unifica la gestión de tarifas, el Balance Neto Horario y la optimización de excedentes en una integración potente y sencilla.

---

## ✨ Key Features / Características

| Feature | Description |
| :--- | :--- |
| **🇪🇸 20TD Tariff Control** | Automatic detection of Punta, Llano, and Valle periods, including holidays and weekends. |
| **⚖️ Net Metering (Balance Neto)** | Real-time calculation of the "Balance Neto Horario". Don't waste a watt! |
| **🔮 AI Prediction** | Estimates how the current hour will end based on instant consumption. |
| **⚡ Smart Load Control** | **Unique Feature:** Calculates `sensor.intensidad_excedente` (Amps at 240V) to automate loads (Deye, heaters, EV) perfectly targeting 0W balance. |
| **📊 Daily Stats** | Aggregates for Surplus, Home Consumption, and Grid Import. |

---

## 🚀 Installation / Instalación

### 1. Pre-requisites / Pre-requisitos
* **Workday Integration:** You must have the official [Workday integration](https://www.home-assistant.io/integrations/workday/) installed and configured for `ES` (Spain) in Home Assistant.
* **Sensors:** You need a Grid Power sensor (Positive=Export, Negative=Import) and a PV Production sensor.

### 2. HACS (Recommended)
1.  Go to HACS > Integrations > Custom Repositories.
2.  Add URL: `https://github.com/stoker2010/ha_gestor_energetico`
3.  Category: **Integration**.
4.  Click **Download** and restart Home Assistant.

### 3. Configuration / Configuración
1.  Go to **Settings > Devices & Services > Add Integration**.
2.  Search for **"Gestor Energético"**.
3.  Follow the Setup Wizard:
    * **Grid Sensor:** Select your grid power meter (W).
    * **Production Sensor:** Select your solar inverter power sensor (W).
    * **Potencia Valle:** Your contracted power for P3 (kW).
    * **Potencia Punta/Llano:** Your contracted power for P1/P2 (kW).

---

## 📊 Sensors Created / Sensores Creados

### Management / Gestión
* `sensor.tramo_horario`: Shows current period (**Punta, Llano, Valle**) and contracted power attribute.

### Net Balance / Balance Neto
* `sensor.balance_neto_horario_real`: Accumulated Wh for the current hour. Resets at xx:00.
* `sensor.balance_neto_horario_estimacion`: Projected value for end-of-hour.
* `sensor.intensidad_excedente`: **The Killer Feature**. Amps available (at 240V) to turn on *now* to finish the hour at 0 balance. Updates every 60s.

### Daily Stats / Estadísticas Diarias
* `sensor.energia_excedente_diaria`: Total energy exported today (Wh).
* `sensor.consumo_hogar_diario`: Total house consumption calculated from Grid & PV (Wh).
* `sensor.energia_importada_diaria`: Total energy bought from grid today (Wh).

---

## 💡 Automation Example / Ejemplo de Automatización

**Control a Heater based on Surplus Amps / Controlar termo según Excedentes**

```yaml
alias: "Auto-Start Heater on Surplus"
trigger:
  - platform: numeric_state
    entity_id: sensor.intensidad_excedente
    above: 5.0 # If we have more than 5 Amps (~1200W) spare
action:
  - service: switch.turn_on
    target:
      entity_id: switch.heater
