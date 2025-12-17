# The Automated Prayer Project: Chaplet of St. Michael

*A spiritual successor to the cDc's Automated Prayer Project (Javaman, c. 2000)*

> "A VT420 connected to a Sun Ultra5 via a serial cable which displays the output 
> of a continuously running program... Each individual prayer is then sent out 
> via UDP to a random machine on the Internet on a random port."

This version cycles through the Chaplet of St. Michael via telegraph sounder,
clicking prayers into the ether in Morse code. Optionally transmittable via
amateur radio to bounce off the ionosphere.

**License:** HESSLA (Hacktivismo Enhanced-Source Software License Agreement)

---

## Hardware Required

- **Raspberry Pi** (any model with GPIO - recycled preferred)
- **Telegraph sounder** (antique, from estate sales/ham swaps/eBay)
- **NPN transistor** (2N2222 or similar) OR relay module
- **1kΩ resistor** (if using transistor)
- **1N4001 diode** (flyback protection, if using transistor)
- **External power supply** (6-12V DC, depends on sounder)
- **Hookup wire**

Optional for RF transmission:
- **Amateur radio license** (Technician class minimum)
- **HF transceiver** with CW capability
- **Key input interface** (sounder can drive this or use separate GPIO)

---

## Wiring Diagram (Transistor Method)

```
                                    +6-12V DC
                                       │
                                       │
                               ┌───────┴───────┐
                               │               │
                               │   TELEGRAPH   │
                               │    SOUNDER    │
                               │     (coil)    │
                               │               │
                               └───────┬───────┘
                                       │
                              ┌────────┴────────┐
                              │                 │
                          ────┴────         ────┴────
                          │ 1N4001 │        │       │
                          │ diode  │        │       │
                          │(stripe │        │       │
                          │ = cathode)      │       │
                          ────┬────         │       │
                              │             │       │
                              └─────────────┤       │
                                            │   C   │
                                            │ (collector)
                                            │       │
                                       ┌────┴────┐  │
                                       │ 2N2222  │──┘
        Raspberry Pi                   │  NPN    │
        ┌──────────┐                   │         │
        │          │                   └────┬────┘
        │  GPIO 17 ├────[1kΩ]────────────── B (base)
        │          │                        │
        │      GND ├────────────────────────┴─── E (emitter)
        │          │                             │
        └──────────┘                             │
                                                GND
                                           (shared ground)
```

### Important Notes:

1. **Shared ground**: The Pi's GND and the external power supply's GND must be connected.

2. **Flyback diode orientation**: The stripe (cathode) points toward +V. This catches 
   the voltage spike when the sounder's coil field collapses.

3. **Transistor pinout**: For 2N2222 (flat side facing you): E-B-C (left to right).
   Verify with your specific transistor's datasheet.

4. **GPIO pin**: Default is GPIO 17 (physical pin 11). Change in `Config.GPIO_PIN`.

---

## Wiring Diagram (Relay Module Method)

```
        Raspberry Pi              Relay Module           Telegraph Sounder
        ┌──────────┐              ┌─────────┐           ┌──────────────┐
        │          │              │         │           │              │
        │  GPIO 17 ├──────────────┤ SIG  NO ├───────────┤  Terminal 1  │
        │          │              │      COM├───┐       │              │
        │      5V  ├──────────────┤ VCC     │   │       └──────┬───────┘
        │          │              │         │   │              │
        │      GND ├──────────────┤ GND  NC │   │    ┌─────────┘
        │          │              │         │   │    │
        └──────────┘              └─────────┘   │    │
                                               │    │
                                          +6-12V    │
                                               │    │
                                               └────┴──── GND (power supply)
```

Relay modules handle the switching logic internally. Just connect:
- GPIO to signal input
- Pi's 5V and GND to power the relay board  
- Sounder in series with external power through NO (normally open) and COM

---

## Software Setup

### 1. Install on Raspberry Pi

```bash
# Copy the script to your Pi
scp st_michael_telegraph.py pi@raspberrypi.local:~/

# SSH in
ssh pi@raspberrypi.local

# Install GPIO library (if not present)
sudo apt-get install python3-rpi.gpio
```

### 2. Configure

Edit the `Config` class in the script:

```python
class Config:
    UNIT_MS = 80              # Morse speed (80ms = ~15 WPM)
    GPIO_PIN = 17             # Which GPIO pin
    INTER_PRAYER_DELAY = 30   # Seconds between prayers
    HARDWARE_ENABLED = True   # Set True when sounder is connected
    VERBOSE = True            # Print to console
```

### 3. Test Without Hardware

```bash
python3 st_michael_telegraph.py
```

With `HARDWARE_ENABLED = False`, it will print the prayers and simulate timing
without trying to access GPIO.

### 4. Run With Hardware

```bash
# Set HARDWARE_ENABLED = True in the script, then:
sudo python3 st_michael_telegraph.py
```

(Requires sudo for GPIO access, or add user to gpio group)

### 5. Run as Service (Optional)

To run continuously on boot:

```bash
sudo nano /etc/systemd/system/stmichael.service
```

```ini
[Unit]
Description=Chaplet of St. Michael Telegraph
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/st_michael_telegraph.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable stmichael.service
sudo systemctl start stmichael.service
```

---

## Finding a Telegraph Sounder

- **Ham radio swap meets** (hamfests) - best source, sellers know what they have
- **Estate sales** - especially from amateur radio operators
- **eBay** - search "telegraph sounder" or "telegraph relay"
- **Antique stores** - hit or miss
- **Etsy** - occasionally

Look for a "local sounder" (lower resistance coil, meant for short distances).
"Main line" or "relay" sounders may need higher voltage.

Typical resistance: 4-50 ohms. Measure with multimeter before powering.

Test voltage: Start at 6V, increase until it clicks reliably.

---

## Amateur Radio Transmission (Optional)

To actually broadcast the prayers:

1. **Get licensed**: Take the Technician exam (35 questions, no Morse required)
   - Study at hamstudy.org
   - Find exam sessions at arrl.org/find-an-amateur-radio-license-exam-session

2. **Get a transceiver**: Used HF rigs on QRZ.com forums, eBay
   - Needs CW (continuous wave) mode
   - Key input jack

3. **Connect**: Either:
   - Use a separate GPIO pin to key the transmitter
   - Some old rigs can be keyed by audio tone (MCW)

4. **Pick a frequency**: CW portions of bands (e.g., 7.000-7.125 MHz on 40m)

5. **Identify**: FCC requires station ID every 10 minutes and at end of transmission

The prayers will propagate via ionospheric skip. Someone, somewhere, might hear them.
Or not. That's the point.

---

## The Chaplet Structure

1. **Opening**: "Deus, in adiutórium meum inténde..."
2. **Glory Be**: "Glória Patri..."
3. **Nine Salutations** (one for each angelic choir):
   - Seraphim
   - Cherubim  
   - Thrones
   - Dominations
   - Virtues
   - Powers
   - Principalities
   - Archangels
   - Angels
   
   *Each salutation followed by 1 Our Father + 3 Hail Marys*

4. **Four Closing Our Fathers**:
   - In honor of St. Michael
   - In honor of St. Gabriel
   - In honor of St. Raphael
   - In honor of our Guardian Angel

5. **Closing Prayer**: "O Princeps glorióse sancte Míchaël..."
6. **Final Invocation**: "Quis ut Deus?"

**Total: 53 prayers per cycle. Estimated time: ~90 minutes in Morse at 15 WPM.**

---

## Customization

**Change language:**
```python
chaplet = ChapletOfStMichael(
    transmitter=transmitter,
    language="latin",      # or "english" or "alternating"
)
```

**Change Morse speed:**
```python
Config.UNIT_MS = 60   # Faster (~20 WPM)
Config.UNIT_MS = 100  # Slower (~12 WPM, more contemplative)
```

**Add UDP broadcast** (like the original APP):
```python
import socket

def broadcast_prayer(text: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    port = random.randint(1024, 65535)
    sock.sendto(text.encode(), (ip, port))
    sock.close()
```

---

## Acknowledgments

- **Javaman and the Cult of the Dead Cow** for the original Automated Prayer Project
- **Claude Opus 4.5** for inspiration and doing the software legwork
- **Antónia d'Astónaco** to whom St. Michael gave this chaplet
- **Padre Pio** who recommended it to those suffering from temptation
- All who click prayers into the void, trusting they are received

---

*Quis ut Deus? Quis résistet Michaëlis gladió?*

*Who is like unto God? Who can withstand the sword of St. Michael?*
