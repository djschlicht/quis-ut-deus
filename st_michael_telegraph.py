#!/usr/bin/env python3
"""
The Automated Prayer Project: Chaplet of St. Michael
A spiritual successor to the cDc's Automated Prayer Project (Javaman, c. 2000)

Instead of the Rosary via UDP to random IPs, this cycles through the 
Chaplet of St. Michael via telegraph sounder (and optionally, ham radio).

"Per intercessiónem Sancti Michaëlis et cappéllæ Séraphim cœléstis..."

Hardware requirements:
    - Raspberry Pi (any model with GPIO)
    - Telegraph sounder
    - Transistor (2N2222) or relay module
    - External power supply (6-12V depending on sounder)
    - Flyback diode (1N4001 or similar) if using transistor

License: HESSLA (Hacktivismo Enhanced-Source Software License Agreement)
         This software may not be used to enable oppression, censorship,
         or human rights violations.

Who is like unto God?
"""

import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    # Morse timing at ~15 WPM (contemplative pace)
    # One "unit" in milliseconds
    UNIT_MS = 80
    
    # GPIO pin for sounder control (BCM numbering)
    GPIO_PIN = 17
    
    # Delay between prayers (seconds) - original APP used 30
    INTER_PRAYER_DELAY = 30
    
    # Set True when hardware is connected, False for console simulation
    HARDWARE_ENABLED = False
    
    # Print prayers to console as they're sent
    VERBOSE = True


# =============================================================================
# MORSE CODE
# =============================================================================

MORSE_CODE = {
    'A': '.-',     'B': '-...',   'C': '-.-.',   'D': '-..',
    'E': '.',      'F': '..-.',   'G': '--.',    'H': '....',
    'I': '..',     'J': '.---',   'K': '-.-',    'L': '.-..',
    'M': '--',     'N': '-.',     'O': '---',    'P': '.--.',
    'Q': '--.-',   'R': '.-.',    'S': '...',    'T': '-',
    'U': '..-',    'V': '...-',   'W': '.--',    'X': '-..-',
    'Y': '-.--',   'Z': '--..',
    '0': '-----',  '1': '.----',  '2': '..---',  '3': '...--',
    '4': '....-',  '5': '.....',  '6': '-....',  '7': '--...',
    '8': '---..',  '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.',  '(': '-.--.',  ')': '-.--.-',
    '&': '.-...',  ':': '---...', ';': '-.-.-.', '=': '-...-',
    '+': '.-.-.',  '-': '-....-', '_': '..--.-', '"': '.-..-.',
    '$': '...-..-','@': '.--.-.', ' ': ' ',  # space handled specially
    
    # Latin special characters - rendered as base letters
    # (Traditional Morse didn't have these, we simplify)
    'Á': '.-',     'É': '.',      'Í': '..',     'Ó': '---',
    'Ú': '..-',    'Æ': '.-.-',   'Œ': '---.',
}


def text_to_morse(text: str) -> list[tuple[str, str]]:
    """
    Convert text to morse code.
    Returns list of (character, morse_pattern) tuples.
    Unknown characters are skipped.
    """
    result = []
    for char in text.upper():
        if char in MORSE_CODE:
            result.append((char, MORSE_CODE[char]))
        elif char in 'ÀÂÄÃÅĀĂĄ':
            result.append((char, MORSE_CODE['A']))
        elif char in 'ÈÊËĒĔĖĘĚ':
            result.append((char, MORSE_CODE['E']))
        elif char in 'ÌÎÏĪĬĮĨ':
            result.append((char, MORSE_CODE['I']))
        elif char in 'ÒÔÖÕŌŎŐ':
            result.append((char, MORSE_CODE['O']))
        elif char in 'ÙÛÜŪŬŮŰŲ':
            result.append((char, MORSE_CODE['U']))
        # Skip unknown characters silently (punctuation we don't have, etc.)
    return result


# =============================================================================
# TELEGRAPH SOUNDER CONTROL
# =============================================================================

class Sounder:
    """
    Controls the telegraph sounder via GPIO or simulates in console.
    """
    
    def __init__(self, pin: int, hardware_enabled: bool = False):
        self.pin = pin
        self.hardware_enabled = hardware_enabled
        self.gpio = None
        
        if self.hardware_enabled:
            try:
                import RPi.GPIO as GPIO
                self.gpio = GPIO
                self.gpio.setmode(GPIO.BCM)
                self.gpio.setup(self.pin, GPIO.OUT)
                self.gpio.output(self.pin, GPIO.LOW)
                print(f"[SOUNDER] Initialized on GPIO {self.pin}")
            except ImportError:
                print("[SOUNDER] RPi.GPIO not available, falling back to simulation")
                self.hardware_enabled = False
            except Exception as e:
                print(f"[SOUNDER] GPIO setup failed: {e}, falling back to simulation")
                self.hardware_enabled = False
    
    def key_down(self):
        """Close the circuit - sounder clicks"""
        if self.hardware_enabled and self.gpio:
            self.gpio.output(self.pin, self.gpio.HIGH)
    
    def key_up(self):
        """Open the circuit - sounder releases"""
        if self.hardware_enabled and self.gpio:
            self.gpio.output(self.pin, self.gpio.LOW)
    
    def cleanup(self):
        """Release GPIO resources"""
        if self.hardware_enabled and self.gpio:
            self.gpio.cleanup()
    
    def dit(self, unit_ms: int):
        """Send a dit (dot) - 1 unit"""
        self.key_down()
        time.sleep(unit_ms / 1000)
        self.key_up()
    
    def dah(self, unit_ms: int):
        """Send a dah (dash) - 3 units"""
        self.key_down()
        time.sleep((unit_ms * 3) / 1000)
        self.key_up()


class MorseTransmitter:
    """
    Transmits text as Morse code through a Sounder.
    """
    
    def __init__(self, sounder: Sounder, unit_ms: int = 80, verbose: bool = True):
        self.sounder = sounder
        self.unit_ms = unit_ms
        self.verbose = verbose
    
    def send_text(self, text: str):
        """Send a complete text string as Morse code."""
        if self.verbose:
            print(f"\n[MORSE] {text[:70]}{'...' if len(text) > 70 else ''}")
        
        morse_sequence = text_to_morse(text)
        
        for i, (char, pattern) in enumerate(morse_sequence):
            if char == ' ':
                # Word space: 7 units (but we've already done 3 after last letter)
                # So add 4 more
                time.sleep((self.unit_ms * 4) / 1000)
                if self.verbose:
                    print(' ', end='', flush=True)
            else:
                self._send_character(pattern)
                if self.verbose:
                    print(char, end='', flush=True)
                
                # Inter-letter space: 3 units (but we've already done 1 after last element)
                # Check if next char is not a space
                if i + 1 < len(morse_sequence) and morse_sequence[i + 1][0] != ' ':
                    time.sleep((self.unit_ms * 2) / 1000)
        
        if self.verbose:
            print()  # newline at end
    
    def _send_character(self, pattern: str):
        """Send a single character's morse pattern."""
        for j, element in enumerate(pattern):
            if element == '.':
                self.sounder.dit(self.unit_ms)
            elif element == '-':
                self.sounder.dah(self.unit_ms)
            
            # Inter-element space: 1 unit (if not last element)
            if j < len(pattern) - 1:
                time.sleep(self.unit_ms / 1000)


# =============================================================================
# THE CHAPLET OF ST. MICHAEL - PRAYER TEXTS
# =============================================================================

@dataclass
class Salutation:
    """One of the nine salutations to the angelic choirs."""
    choir: str
    choir_latin: str
    prayer_english: str
    prayer_latin: str


# The Nine Choirs, from highest to lowest
SALUTATIONS = [
    Salutation(
        choir="Seraphim",
        choir_latin="Séraphim",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Seraphim, "
            "may the Lord make us worthy to burn with the fire of perfect charity. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Séraphim cœléstis, "
            "Dóminus nos dignos effíciat incéndi igne caritátis perféctæ. Amen."
        ),
    ),
    Salutation(
        choir="Cherubim",
        choir_latin="Chérubim",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Cherubim, "
            "may the Lord vouchsafe to grant us grace to leave the ways of wickedness "
            "to run in the paths of Christian perfection. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Chérubim cœléstis, "
            "Dóminus nobis grátiam relínquere vias peccáti det et in vias "
            "perfectiónis Christiánæ decúrrere. Amen."
        ),
    ),
    Salutation(
        choir="Thrones",
        choir_latin="Thronórum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Thrones, "
            "may the Lord infuse into our hearts a true and sincere spirit of humility. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Thronórum cœléstis, "
            "infúndat Dóminus córdibus nostris spíritum humilitátis verum sincerúmque. Amen."
        ),
    ),
    Salutation(
        choir="Dominations",
        choir_latin="Dominatiónum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Dominations, "
            "may the Lord give us grace to govern our senses and subdue our unruly passions. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Dominatiónum cœléstis, "
            "Dóminus nobis grátiam det sensus gubernáre et carnem petulántem superáre. Amen."
        ),
    ),
    Salutation(
        choir="Virtues",
        choir_latin="Virtútum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Virtues, "
            "may the Lord preserve us from evil and suffer us not to fall into temptation. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Virtútum cœléstis, "
            "Dóminus nos a malo et cadéndo in tentatiónem consérvet. Amen."
        ),
    ),
    Salutation(
        choir="Powers",
        choir_latin="Potestátum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Powers, "
            "may the Lord vouchsafe to protect our souls against the snares and temptations "
            "of the devil. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Potestátum cœléstis, "
            "Dóminus ánimas nostras contra insídias et tentatiónes diáboli deféndat. Amen."
        ),
    ),
    Salutation(
        choir="Principalities",
        choir_latin="Principatórum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Principalities, "
            "may God fill our souls with a true spirit of obedience. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Principatórum cœléstis, "
            "Dóminus ánimas nostras spíritu vero obœdiéntiæ ímpleat. Amen."
        ),
    ),
    Salutation(
        choir="Archangels",
        choir_latin="Archangelórum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Archangels, "
            "may the Lord give us perseverance in faith and in all good works, "
            "in order that we gain the glory of Paradise. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Archangelórum cœléstis, "
            "Dóminus nobis constántiam in fide et óminibus opéribus bonis det, "
            "ut glóriam paradísi obtineámus. Amen."
        ),
    ),
    Salutation(
        choir="Angels",
        choir_latin="Angelórum",
        prayer_english=(
            "By the intercession of Saint Michael and the celestial Choir of Angels, "
            "may the Lord grant us to be protected by them in this mortal life "
            "and conducted hereafter to eternal glory. Amen."
        ),
        prayer_latin=(
            "Per intercessiónem Sancti Michaëlis et cappéllæ Angelórum cœléstis, "
            "Dóminus nos ab eis in hac vita mortále conservári det "
            "et in vitam futúram perdúci. Amen."
        ),
    ),
]

# Opening prayer
OPENING_PRAYER = {
    "english": "O God, come to my assistance. O Lord, make haste to help me.",
    "latin": "Deus, in adiutórium meum inténde. Dómine, ad adiuvándum me festína.",
}

# Glory Be (said after opening)
GLORY_BE = {
    "english": (
        "Glory be to the Father, and to the Son, and to the Holy Spirit. "
        "As it was in the beginning, is now, and ever shall be, "
        "world without end. Amen."
    ),
    "latin": (
        "Glória Patri, et Fílio, et Spirítui Sancto. "
        "Sicut erat in princípio, et nunc, et semper, "
        "et in sǽcula sæculórum. Amen."
    ),
}

# The Our Father (1x after each salutation)
OUR_FATHER = {
    "english": (
        "Our Father, who art in heaven, hallowed be thy name. "
        "Thy kingdom come, thy will be done, on earth as it is in heaven. "
        "Give us this day our daily bread, and forgive us our trespasses, "
        "as we forgive those who trespass against us. "
        "And lead us not into temptation, but deliver us from evil. Amen."
    ),
    "latin": (
        "Pater noster, qui es in cælis, sanctificétur nomen tuum. "
        "Advéniat regnum tuum. Fiat volúntas tua, sicut in cælo et in terra. "
        "Panem nostrum quotidiánum da nobis hódie. "
        "Et dimítte nobis débita nostra, sicut et nos dimíttimus debitóribus nostris. "
        "Et ne nos indúcas in tentatiónem, sed líbera nos a malo. Amen."
    ),
}

# The Hail Mary (3x after each Our Father)
HAIL_MARY = {
    "english": (
        "Hail Mary, full of grace, the Lord is with thee. "
        "Blessed art thou among women, and blessed is the fruit of thy womb, Jesus. "
        "Holy Mary, Mother of God, pray for us sinners, "
        "now and at the hour of our death. Amen."
    ),
    "latin": (
        "Ave María, grátia plena, Dóminus tecum. "
        "Benedícta tu in muliéribus, et benedíctus fructus ventris tui, Iesus. "
        "Sancta María, Mater Dei, ora pro nobis peccatóribus, "
        "nunc et in hora mortis nostræ. Amen."
    ),
}

# Closing Our Fathers (4x - one for each archangel and guardian angel)
CLOSING_OUR_FATHERS = [
    {"dedicatee": "Saint Michael", "dedicatee_latin": "Sancti Michaëlis"},
    {"dedicatee": "Saint Gabriel", "dedicatee_latin": "Sancti Gabriélis"},
    {"dedicatee": "Saint Raphael", "dedicatee_latin": "Sancti Raphaëlis"},
    {"dedicatee": "Our Guardian Angel", "dedicatee_latin": "Angeli Custodis"},
]

# Closing prayer
CLOSING_PRAYER = {
    "english": (
        "O glorious Prince Saint Michael, chief and commander of the heavenly hosts, "
        "guardian of souls, vanquisher of rebel spirits, servant in the house of the Divine King, "
        "and our admirable conductor, thou who dost shine with excellence and superhuman virtue, "
        "vouchsafe to deliver us from all evil, who turn to thee with confidence, "
        "and enable us by thy gracious protection to serve God more and more faithfully every day. "
        "Pray for us, O glorious Saint Michael, Prince of the Church of Jesus Christ, "
        "that we may be made worthy of His promises."
    ),
    "latin": (
        "O Princeps glorióse sancte Míchaël, dux et præpósite cœléstium exercítuum, "
        "custos animárum, dómitor spirítuum rebéllum, serve in domo divíni Regis, "
        "et noster condúctor mirábilis, qui cum excelléntia et virtúte cœlésti fulges, "
        "líbera nos a malo, qui ad te cum confidéntia convértimus, "
        "et nos propítio præsídio tuo fac, quotídie Deum magis fidéliter sevíre. "
        "Ora pro nobis, O glorióse Sancte Míchaël, princeps ecclésiæ Jesu Christi, "
        "ut digni efficiámur promissiónibus eius."
    ),
}

# The final invocation
FINAL_INVOCATION = {
    "english": "Who is like unto God? Who can withstand the sword of Saint Michael?",
    "latin": "Quis ut Deus? Quis résistet Michaëlis gladió?",
}


# =============================================================================
# MAIN PRAYER CYCLE
# =============================================================================

class ChapletOfStMichael:
    """
    The complete Chaplet cycle.
    """
    
    def __init__(self, transmitter: MorseTransmitter, language: str = "latin",
                 inter_prayer_delay: int = 30):
        self.transmitter = transmitter
        self.language = language  # "latin", "english", or "alternating"
        self.inter_prayer_delay = inter_prayer_delay
        self.cycle_count = 0
    
    def get_text(self, prayer_dict: dict, salutation: Optional[Salutation] = None,
                 attr: Optional[str] = None) -> str:
        """Get prayer text in appropriate language."""
        if self.language == "alternating":
            # Alternate based on cycle count
            lang = "latin" if self.cycle_count % 2 == 0 else "english"
        else:
            lang = self.language
        
        if salutation and attr:
            return getattr(salutation, f"prayer_{lang}")
        return prayer_dict.get(lang, prayer_dict.get("latin"))
    
    def pray(self):
        """
        Execute one complete Chaplet cycle.
        
        Structure:
            1. Opening prayer
            2. Nine salutations (each followed by Our Father)
            3. Closing prayer
            4. Final invocation
        """
        self.cycle_count += 1
        
        print(f"\n{'='*60}")
        print(f"CHAPLET OF ST. MICHAEL - CYCLE {self.cycle_count}")
        print(f"Language: {self.language}")
        print(f"{'='*60}")
        
        # Opening
        print("\n[OPENING]")
        self.transmitter.send_text(self.get_text(OPENING_PRAYER))
        time.sleep(self.inter_prayer_delay)
        
        # Glory Be
        print("\n[GLORY BE]")
        self.transmitter.send_text(self.get_text(GLORY_BE))
        time.sleep(self.inter_prayer_delay)
        
        # Nine Salutations
        for i, salutation in enumerate(SALUTATIONS, 1):
            print(f"\n[SALUTATION {i}/9: {salutation.choir.upper()}]")
            
            # The salutation prayer
            if self.language == "alternating":
                lang = "latin" if self.cycle_count % 2 == 0 else "english"
            else:
                lang = self.language
            
            prayer = getattr(salutation, f"prayer_{lang}")
            self.transmitter.send_text(prayer)
            time.sleep(self.inter_prayer_delay)
            
            # Our Father (1x)
            print(f"\n[OUR FATHER]")
            self.transmitter.send_text(self.get_text(OUR_FATHER))
            time.sleep(self.inter_prayer_delay)
            
            # Hail Mary (3x)
            for hail_mary_num in range(1, 4):
                print(f"\n[HAIL MARY {hail_mary_num}/3]")
                self.transmitter.send_text(self.get_text(HAIL_MARY))
                time.sleep(self.inter_prayer_delay)
        
        # Four Our Fathers in honor of the Archangels and Guardian Angel
        for dedication in CLOSING_OUR_FATHERS:
            if self.language == "alternating":
                lang = "latin" if self.cycle_count % 2 == 0 else "english"
            else:
                lang = self.language
            
            if lang == "latin":
                dedicatee = dedication["dedicatee_latin"]
            else:
                dedicatee = dedication["dedicatee"]
            
            print(f"\n[OUR FATHER - In honor of {dedication['dedicatee']}]")
            self.transmitter.send_text(self.get_text(OUR_FATHER))
            time.sleep(self.inter_prayer_delay)
        
        # Closing prayer
        print("\n[CLOSING PRAYER]")
        self.transmitter.send_text(self.get_text(CLOSING_PRAYER))
        time.sleep(self.inter_prayer_delay)
        
        # Final invocation
        print("\n[FINAL INVOCATION]")
        self.transmitter.send_text(self.get_text(FINAL_INVOCATION))
        
        print(f"\n{'='*60}")
        print(f"CYCLE {self.cycle_count} COMPLETE")
        print(f"{'='*60}\n")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point. Runs the Chaplet in an infinite loop.
    
    "The program itself cycles through the [Chaplet], displaying a new 
    individual prayer once every thirty seconds. Each individual prayer 
    is then sent out..."
        - In the spirit of the original Automated Prayer Project
    """
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     THE AUTOMATED PRAYER PROJECT: CHAPLET OF ST. MICHAEL      ║
    ║                                                               ║
    ║     A telegraph sounder connected to a Raspberry Pi           ║
    ║     which transmits the output of a continuously running      ║
    ║     program. The program cycles through the Chaplet of        ║
    ║     St. Michael, sending a new prayer as Morse code           ║
    ║     once every thirty seconds.                                ║
    ║                                                               ║
    ║     In the spirit of the cDc's Automated Prayer Project       ║
    ║     (Javaman, c. 2000)                                        ║
    ║                                                               ║
    ║     HESSLA Licensed - Who is like unto God?                   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize hardware
    sounder = Sounder(
        pin=Config.GPIO_PIN,
        hardware_enabled=Config.HARDWARE_ENABLED
    )
    
    transmitter = MorseTransmitter(
        sounder=sounder,
        unit_ms=Config.UNIT_MS,
        verbose=Config.VERBOSE
    )
    
    chaplet = ChapletOfStMichael(
        transmitter=transmitter,
        language="latin",  # "latin", "english", or "alternating"
        inter_prayer_delay=Config.INTER_PRAYER_DELAY
    )
    
    try:
        # Pray without ceasing
        while True:
            chaplet.pray()
            
            # Brief pause between cycles
            print(f"\n[PAUSE] Resting before next cycle...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Closing with final invocation...")
        transmitter.send_text("QUIS UT DEUS")
        
    finally:
        sounder.cleanup()
        print("\n[SHUTDOWN] Sounder released. Pax vobiscum.")


if __name__ == "__main__":
    main()
