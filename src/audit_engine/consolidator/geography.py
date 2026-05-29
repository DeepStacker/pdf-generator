from __future__ import annotations

# ---------------------------------------------------------------------------
# India: State → Zone mapping
# ---------------------------------------------------------------------------

STATE_TO_ZONE: dict[str, str] = {
    # North
    "jammu & kashmir": "North",
    "jammu and kashmir": "North",
    "himachal pradesh": "North",
    "punjab": "North",
    "chandigarh": "North",
    "haryana": "North",
    "uttarakhand": "North",
    "uttar pradesh": "North",
    "delhi": "North",
    "new delhi": "North",
    "rajasthan": "North",
    # South
    "andhra pradesh": "South",
    "a.p": "South",
    "a.p.": "South",
    "telangana": "South",
    "karnataka": "South",
    "kerala": "South",
    "tamil nadu": "South",
    "tamilnadu": "South",
    "puducherry": "South",
    "pondicherry": "South",
    "andaman & nicobar": "South",
    "andaman and nicobar islands": "South",
    "lakshadweep": "South",
    # East
    "west bengal": "East",
    "odisha": "East",
    "orissa": "East",
    "bihar": "East",
    "jharkhand": "East",
    "assam": "East",
    "sikkim": "East",
    "arunachal pradesh": "East",
    "nagaland": "East",
    "manipur": "East",
    "mizoram": "East",
    "tripura": "East",
    "meghalaya": "East",
    # West
    "maharashtra": "West",
    "gujarat": "West",
    "goa": "West",
    "dadra & nagar haveli": "West",
    "daman & diu": "West",
    "dadra and nagar haveli and daman and diu": "West",
    # Central
    "madhya pradesh": "Central",
    "chhattisgarh": "Central",
}

# ---------------------------------------------------------------------------
# India: City → State mapping (major cities used in audit reports)
# ---------------------------------------------------------------------------

CITY_TO_STATE: dict[str, str] = {
    # Andhra Pradesh
    "visakhapatnam": "Andhra Pradesh",
    "vizag": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh",
    "guntur": "Andhra Pradesh",
    "nellore": "Andhra Pradesh",
    "kurnool": "Andhra Pradesh",
    "vijayanagaram": "Andhra Pradesh",
    "vizianagaram": "Andhra Pradesh",
    "viziayanagaram": "Andhra Pradesh",
    "anantapur": "Andhra Pradesh",
    "ongole": "Andhra Pradesh",
    "kakinada": "Andhra Pradesh",
    "rajahmundry": "Andhra Pradesh",
    "tirupati": "Andhra Pradesh",
    "eluru": "Andhra Pradesh",
    # Bihar
    "patna": "Bihar",
    "gaya": "Bihar",
    "muzaffarpur": "Bihar",
    "bhagalpur": "Bihar",
    "purnia": "Bihar",
    "purnea": "Bihar",
    "darbhanga": "Bihar",
    "begusarai": "Bihar",
    "munger": "Bihar",
    "madhepura": "Bihar",
    "bokaro": "Bihar",
    "hajipur": "Bihar",
    "siwan": "Bihar",
    "sasaram": "Bihar",
    "chhapra": "Bihar",
    "samastipur": "Bihar",
    "katihar": "Bihar",
    # Delhi
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "north delhi": "Delhi",
    "south delhi": "Delhi",
    "east delhi": "Delhi",
    "west delhi": "Delhi",
    "central delhi": "Delhi",
    "new delhi": "Delhi",
    # Gujarat
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "vadodara": "Gujarat",
    "baroda": "Gujarat",
    "rajkot": "Gujarat",
    "bhavnagar": "Gujarat",
    "jamnagar": "Gujarat",
    "gandhinagar": "Gujarat",
    "anand": "Gujarat",
    "navsari": "Gujarat",
    "mehsana": "Gujarat",
    "valsad": "Gujarat",
    "bhuj": "Gujarat",
    # Haryana
    "faridabad": "Haryana",
    "gurugram": "Haryana",
    "gurgaon": "Haryana",
    "panipat": "Haryana",
    "ambala": "Haryana",
    "karnal": "Haryana",
    "hisar": "Haryana",
    "rohtak": "Haryana",
    "sonipat": "Haryana",
    "yamunanagar": "Haryana",
    "panchkula": "Haryana",
    "bhiwani": "Haryana",
    "rewari": "Haryana",
    "ferozpur": "Haryana",
    "hanumangarh": "Rajasthan",  # Actually Rajasthan, but check
    "menhdawal": "Uttar Pradesh",
    "naugarh": "Uttar Pradesh",
    # Jammu & Kashmir
    "srinagar": "Jammu & Kashmir",
    "jammu": "Jammu & Kashmir",
    # Karnataka
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "mysore": "Karnataka",
    "mysuru": "Karnataka",
    "hubli": "Karnataka",
    "mangalore": "Karnataka",
    "mangaluru": "Karnataka",
    "belgaum": "Karnataka",
    "davanagere": "Karnataka",
    "bellary": "Karnataka",
    "gulbarga": "Karnataka",
    "shimoga": "Karnataka",
    # Kerala
    "ernakulam": "Kerala",
    "kochi": "Kerala",
    "cochin": "Kerala",
    "thiruvananthapuram": "Kerala",
    "trivandrum": "Kerala",
    "kozhikode": "Kerala",
    "calicut": "Kerala",
    "kollam": "Kerala",
    "alappuzha": "Kerala",
    "thrissur": "Kerala",
    "palakkad": "Kerala",
    "kannur": "Kerala",
    "madurai": "Tamil Nadu",  # Actually TN
    # Madhya Pradesh
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    "ujjain": "Madhya Pradesh",
    # Maharashtra
    "mumbai": "Maharashtra",
    "bombay": "Maharashtra",
    "pune": "Maharashtra",
    "nagpur": "Maharashtra",
    "thane": "Maharashtra",
    "nashik": "Maharashtra",
    "aurangabad": "Maharashtra",
    "solapur": "Maharashtra",
    "kolhapur": "Maharashtra",
    "navi mumbai": "Maharashtra",
    "vasai": "Maharashtra",
    "virar": "Maharashtra",
    "kalyan": "Maharashtra",
    "dombivli": "Maharashtra",
    "ulhasnagar": "Maharashtra",
    # Odisha
    "bhubaneswar": "Odisha",
    "bhubaneshwar": "Odisha",
    "cuttack": "Odisha",
    "balasore": "Odisha",
    "baleswar": "Odisha",
    "rourkela": "Odisha",
    "sambalpur": "Odisha",
    "puri": "Odisha",
    "berhampur": "Odisha",
    "brahmapur": "Odisha",
    # Punjab
    "chandigarh": "Punjab",
    "ludhiana": "Punjab",
    "amritsar": "Punjab",
    "jalandhar": "Punjab",
    "pathankot": "Punjab",
    "bathinda": "Punjab",
    "mohali": "Punjab",
    # Rajasthan
    "jaipur": "Rajasthan",
    "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan",
    "kota": "Rajasthan",
    "bikaner": "Rajasthan",
    "ajmer": "Rajasthan",
    "bhilwara": "Rajasthan",
    "alwar": "Rajasthan",
    "sikar": "Rajasthan",
    # Tamil Nadu
    "chennai": "Tamil Nadu",
    "madras": "Tamil Nadu",
    "coimbatore": "Tamil Nadu",
    "tiruchirappalli": "Tamil Nadu",
    "trichy": "Tamil Nadu",
    "salem": "Tamil Nadu",
    "tirunelveli": "Tamil Nadu",
    "vellore": "Tamil Nadu",
    "erode": "Tamil Nadu",
    "thoothukudi": "Tamil Nadu",
    # Telangana
    "hyderabad": "Telangana",
    "secunderabad": "Telangana",
    "warangal": "Telangana",
    "nizamabad": "Telangana",
    "karimnagar": "Telangana",
    # Uttar Pradesh
    "lucknow": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh",
    "noida": "Uttar Pradesh",
    "meerut": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh",
    "bareilly": "Uttar Pradesh",
    "moradabad": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh",
    "saharanpur": "Uttar Pradesh",
    "jhansi": "Uttar Pradesh",
    "mathura": "Uttar Pradesh",
    "ayodhya": "Uttar Pradesh",
    "faizabad": "Uttar Pradesh",
    # West Bengal
    "kolkata": "West Bengal",
    "calcutta": "West Bengal",
    "howrah": "West Bengal",
    "durgapur": "West Bengal",
    "asansol": "West Bengal",
    "siliguri": "West Bengal",
    "malda": "West Bengal",
    "english bazar": "West Bengal",
    "malda": "West Bengal",
    "englishbazar": "West Bengal",
    "bardhaman": "West Bengal",
    "kharagpur": "West Bengal",
    "haldia": "West Bengal",
    "kalyani": "West Bengal",
    # Jharkhand
    "ranchi": "Jharkhand",
    "jamshedpur": "Jharkhand",
    "dhanbad": "Jharkhand",
    "bokaro steel city": "Jharkhand",
    "deoghar": "Jharkhand",
    # Assam
    "guwahati": "Assam",
    "dispur": "Assam",
    "silchar": "Assam",
    "dibrugarh": "Assam",
    "jorhat": "Assam",
    "nagaon": "Assam",
    "tezpur": "Assam",
    # Chhattisgarh
    "raipur": "Chhattisgarh",
    "bhilai": "Chhattisgarh",
    "bilaspur": "Chhattisgarh",
    "korba": "Chhattisgarh",
    # Uttarakhand
    "dehradun": "Uttarakhand",
    "haridwar": "Uttarakhand",
    "rishikesh": "Uttarakhand",
    "nainital": "Uttarakhand",
    "haldwani": "Uttarakhand",
    # Goa
    "panaji": "Goa",
    "panjim": "Goa",
    "margao": "Goa",
    "vasco da gama": "Goa",
    # Himachal Pradesh
    "shimla": "Himachal Pradesh",
    "dharamshala": "Himachal Pradesh",
    "dharamsala": "Himachal Pradesh",
    "manali": "Himachal Pradesh",
    "kullu": "Himachal Pradesh",
    "solan": "Himachal Pradesh",
    # Tripura
    "agartala": "Tripura",
    # Meghalaya
    "shillong": "Meghalaya",
    # Nagaland
    "kohima": "Nagaland",
    "dimapur": "Nagaland",
    # Manipur
    "imphal": "Manipur",
    # Mizoram
    "aizawl": "Mizoram",
    # Arunachal Pradesh
    "itanagar": "Arunachal Pradesh",
    # Sikkim
    "gangtok": "Sikkim",
}

# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

_STATE_CACHE: dict[str, str] = {}
_ZONE_CACHE: dict[str, str] = {}


def normalize_location(name: str | None) -> str | None:
    """Normalize a location/city/state name for lookup."""
    if name is None:
        return None
    n = str(name).strip().lower()
    n = n.replace("\n", " ").replace("\r", "")
    n = " ".join(n.split())  # collapse whitespace
    return n if n else None


def city_to_state(city: str | None) -> str | None:
    """Derive State from City name."""
    key = normalize_location(city)
    if not key:
        return None
    if key in _STATE_CACHE:
        return _STATE_CACHE[key]

    # Direct lookup
    if key in CITY_TO_STATE:
        _STATE_CACHE[key] = CITY_TO_STATE[key]
        return CITY_TO_STATE[key]

    # Split on separators and try each segment
    # Handles: "City1/City2", "City1+City2", "City1-City2"
    import re as _re
    segments = _re.split(r"[/+,&\-]", key)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # Try full segment
        if seg in CITY_TO_STATE:
            _STATE_CACHE[key] = CITY_TO_STATE[seg]
            return CITY_TO_STATE[seg]
        # Try first word of segment
        first_word = seg.split()[0] if seg.split() else seg
        if first_word in CITY_TO_STATE:
            _STATE_CACHE[key] = CITY_TO_STATE[first_word]
            return CITY_TO_STATE[first_word]

    # Not found
    _STATE_CACHE[key] = None
    return None


def state_to_zone(state: str | None) -> str | None:
    """Derive Zone from State name."""
    key = normalize_location(state)
    if not key:
        return None
    if key in _ZONE_CACHE:
        return _ZONE_CACHE[key]

    if key in STATE_TO_ZONE:
        _ZONE_CACHE[key] = STATE_TO_ZONE[key]
        return STATE_TO_ZONE[key]

    _ZONE_CACHE[key] = None
    return None


def location_to_state_and_zone(location: str | None) -> tuple[str | None, str | None]:
    """Derive (State, Zone) from a location/city name."""
    state = city_to_state(location)
    zone = state_to_zone(state) if state else None
    return state, zone
