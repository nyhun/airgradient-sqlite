# airgradient-sqlite
A minimal, lightweight implementation for logging Airgradient sensor readings.

Ideal for setting up a server on a Raspberry Pi.

Firmware/server assumes single airgradient sensor in the house.
(Code should be easily extendable to multiple device setup, by logging device ID to DB as well)

For firmware, [C02_PM_SHT_OLED_WIFI.ino](https://github.com/airgradienthq/arduino/blob/1.4.2/examples/C02_PM_SHT_OLED_WIFI/C02_PM_SHT_OLED_WIFI.ino) was used as a starting point.

## Setup

The Arduino IDE is recommended for flashing firmware on Airgradient.

For small-scale home deployments, using `uvicorn` to serve the application should work fine.

### Firmware
1. **Install ESP8266 Board Manager:**
   - Tested with version 3.1.2
   - Go to **Preferences** → **Additional Boards Manager URL** and add:  
     `http://arduino.esp8266.com/stable/package_esp8266com_index.json`

2. **Install Required Libraries:**
   - `WifiManager by tzapu, tablatronix` (Tested with version 2.0.17)
   - `ESP8266 and ESP32 OLED driver for SSD1306 displays by ThingPulse, Fabrice Weinberg` (Tested with version 4.6.1)
   - `AirGradient Air Quality Sensor by Airgradient` (Tested with version 1.4.2)

3. **Configuration:**
   - Set the sensor you are using in the code.
   - Choose whether you want to connect the sensor to WiFi.
   - You can also switch PM2.5 from µg/m³ to US AQI and Celsius to Fahrenheit.

4. **Upload Firmware:**
   - Select `LOLIN(WEMOS) D1 R2 Mini` from **Tools > Board > ESP8266**.
   
   **Note:** As of February 14th, 2025, on Windows 10/11, you might need to revert the CH340 driver to an older version due to a known issue with the default driver.  
   [More info](https://stackoverflow.com/questions/76146837/a-fatal-esptool-py-error-occurred-cannot-configure-port-permissionerror13-a)

### Server
1. **Install Python3.**

2. **Install Dependencies:**
   Run the following command to install required dependencies:
   ```bash
   pip install -r requirements.txt
3. **Start server**
   Run the following command to start the server:
   ```bash
   uvicorn app:app