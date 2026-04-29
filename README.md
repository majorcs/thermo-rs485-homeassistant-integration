[![Tests](https://github.com/majorcs/thermo-rs485-homeassistant-integration/actions/workflows/tests.yml/badge.svg)](https://github.com/majorcs/thermo-rs485-homeassistant-integration/actions/workflows/tests.yml)
[![Hassfest](https://github.com/majorcs/thermo-rs485-homeassistant-integration/actions/workflows/hassfest.yml/badge.svg)](https://github.com/majorcs/thermo-rs485-homeassistant-integration/actions/workflows/hassfest.yml)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

# Thermo RS485

Home Assistant integration for RS-485 Modbus Temperature & Humidity sensors.

## Features

- **Temperature** sensor (°C, signed, 0.1 °C resolution)
- **Humidity** sensor (%RH, 0.1 % resolution)
- **Modbus TCP** and **Modbus RTU (Serial)** transport support
- Multiple devices on the same bus / in the same HA instance
- Fully configured through the Home Assistant UI — no YAML required
- Writable configuration registers exposed as entities:
  - Device address
  - Baud rate code
  - Temperature correction offset
  - Humidity correction offset
- Configurable scan interval (default: 30 seconds)

## Installation

### HACS (recommended)

1. Open **HACS → Integrations** in Home Assistant.
2. Click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/majorcs/thermo-rs485-homeassistant-integration` as type **Integration**.
4. Search for **Thermo RS485** and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and search for **Thermo RS485**.

### Manual

Download or clone this repository and copy `custom_components/thermo_rs485` into your
Home Assistant `custom_components/` directory, then restart.

## Configuration

During setup you will be asked to choose a protocol:

**Modbus TCP**
- IP address or hostname
- Port (default: 502)
- Slave ID (default: 1)
- Scan interval in seconds (default: 30)

**Modbus RTU (Serial)**
- Serial port path (e.g. `/dev/ttyUSB0`)
- Baud rate (default: 9600)
- Data bits (default: 8)
- Parity (default: None)
- Stop bits (default: 1)
- Slave ID (default: 1)
- Scan interval in seconds (default: 30)

## License

MIT
