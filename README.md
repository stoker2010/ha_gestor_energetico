# Gestor Energético Integral 20TD 🇪🇸

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/stoker2010/ha_gestor_energetico?style=for-the-badge&color=blue)](https://github.com/stoker2010/ha_gestor_energetico/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://github.com/stoker2010/ha_gestor_energetico)
[![License](https://img.shields.io/github/license/stoker2010/ha_gestor_energetico?style=for-the-badge)](LICENSE)

> **La solución definitiva para gestionar placas solares y tarifas eléctricas en España.**

**Gestor Energético** es una integración "Todo en Uno" para Home Assistant diseñada para hogares españoles con tarifa 20TD y autoconsumo. Unifica la detección de tramos horarios, el cálculo de Balance Neto Horario y, lo más importante, te dice exactamente **cuánta energía te sobra** para aprovechar hasta el último vatio.

[English description below]

---

## ✨ Características Principales

* 🇪🇸 **Control Total Tarifa 20TD**: Detecta automáticamente periodos Punta, Llano y Valle, incluyendo festivos nacionales y fines de semana.
* ⚖️ **Balance Neto Horario (Real y Estimado)**: Calcula en tiempo real tu saldo energético con la comercializadora. ¡No regales energía!
* 🧠 **IA de Predicción**: Estima cómo terminará la hora actual basándose en tu consumo instantáneo.
* 🔋 **Gestión de Excedentes (Killer Feature)**: Calcula la **Intensidad Excedente (Amperios a 240V)**. Ideal para encender termos, controlar inversores (Deye, Victron) o cargar el coche eléctrico ajustando la potencia al milímetro para terminar la hora en 0 consumido.
* 📊 **Estadísticas Diarias**: Sensores listos para usar en tu panel de Energía (Excedentes, Consumo Hogar, Importación).

---

## ⚙️ Requisitos Previos

1.  Tener instalada la integración oficial **[Workday](https://www.home-assistant.io/integrations/workday/)** configurada para España (`ES`).
2.  **Sensor de Red (Grid)**: Debe ser **Positivo (+) para Excedentes** (Venta) y **Negativo (-) para Consumo** (Compra).
3.  **Sensor de Producción Solar**: Siempre positivo.

---

## 🚀 Instalación

### Opción 1: HACS (Recomendado)

1.  Abre HACS > Integraciones > Menú (3 puntos) > **Repositorios Personalizados**.
2.  Añade la URL: `https://github.com/stoker2010/ha_gestor_energetico`
3.  Categoría: **Integration**.
4.  Busca "Gestor Energético" y pulsa **Descargar**.
5.  **Reinicia** Home Assistant.

### Opción 2: Manual

1.  Descarga la última *release* desde GitHub.
2.  Copia la carpeta `custom_components/ha_gestor_energetico` dentro de tu carpeta `custom_components`.
3.  Reinicia Home Assistant.

---

## 🛠️ Configuración

Esta integración se configura 100% desde la interfaz de usuario (UI). No necesitas editar YAML.

1.  Ve a **Ajustes** > **Dispositivos y Servicios**.
2.  Pulsa **Añadir Integración** y busca **"Gestor Energético"**.
3.  Sigue el asistente:
    * **Sensor Grid**: Tu medidor de compañía o pinza en la acometida.
    * **Sensor Producción**: Tu inversor solar.
    * **Potencias**: Introduce tu potencia contratada para Valle y Punta/Llano.

---

## 📊 Entidades Disponibles

Una vez configurado, tendrás estos sensores disponibles:

### 1. Gestión y Tarifas
| Entidad | Icono | Descripción |
| :--- | :---: | :--- |
| `sensor.tramo_horario` | 🕒 | Indica el periodo actual: **Punta, Llano o Valle**. |

### 2. Balance Neto y Excedentes (El Cerebro)
| Entidad | Unidad | Descripción |
| :--- | :---: | :--- |
| `sensor.balance_neto_horario_real` | `Wh` | Tu "hucha" de energía de la hora actual. Se reinicia a xx:00. |
| `sensor.balance_neto_horario_estimacion` | `Wh` | Predicción de cómo acabará la hora si mantienes el consumo actual. |
| `sensor.intensidad_excedente` | `A` | **Intensidad disponible a 240V**. Úsala para encender cargas. Se actualiza cada 60s buscando el objetivo "Balance 0". |

### 3. Contadores Diarios
| Entidad | Descripción |
| :--- | :--- |
| `sensor.consumo_hogar_diario` | Consumo real de tu casa (Red + Solar). |
| `sensor.energia_importada_diaria` | Energía comprada de la red. |
| `sensor.energia_excedente_diaria` | Energía inyectada a la red. |

---

## 💡 Ejemplos de Automatización

### 🔥 Encender Termo con Excedentes
Aprovecha el sensor de intensidad para encender cargas resistivas solo cuando "te sobre" amperaje real considerando el balance neto.

```yaml
alias: "Gestor Excedentes: Termo"
trigger:
  - platform: numeric_state
    entity_id: sensor.intensidad_excedente
    above: 5.0  # Si sobran más de 5 Amperios (aprox 1200W)
action:
  - service: switch.turn_on
    target:
      entity_id: switch.termo_agua
