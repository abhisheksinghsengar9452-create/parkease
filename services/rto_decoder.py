"""Indian RTO State, District and Vehicle Category Decoder."""
from __future__ import annotations
import re

STATE_NAMES: dict[str, str] = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BH": "Bharat Series (Pan-India)",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman and Diu",
    "DL": "Delhi NCT",
    "DN": "Dadra and Nagar Haveli",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "UA": "Uttarakhand",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}

POPULAR_RTOS: dict[str, str] = {
    "DL01": "Mall Road (North Delhi)",
    "DL02": "Tilak Marg (New Delhi)",
    "DL03": "Sheikh Sarai (South Delhi)",
    "DL04": "Janakpuri (West Delhi)",
    "DL05": "Loni Road (North East Delhi)",
    "DL06": "Sarai Kale Khan (Central Delhi)",
    "DL07": "Mayur Vihar (East Delhi)",
    "DL08": "Wazirpur (North West Delhi)",
    "DL09": "Palam (South West Delhi)",
    "DL10": "Raja Garden (West Delhi)",
    "DL11": "Rohini (North West Delhi)",
    "DL12": "Vasant Vihar (South West Delhi)",
    "DL13": "Surajmal Vihar (East Delhi)",
    "DL14": "Sonipat Road (North West Delhi II)",
    "MH01": "Mumbai South (Tardeo)",
    "MH02": "Mumbai West (Andheri)",
    "MH03": "Mumbai East (Wadala)",
    "MH04": "Thane",
    "MH12": "Pune Central",
    "MH14": "Pimpri-Chinchwad",
    "KA01": "Bangalore Central (Koramangala)",
    "KA02": "Bangalore West (Rajajinagar)",
    "KA03": "Bangalore East (Indiranagar)",
    "KA04": "Bangalore North (Yeshwanthpur)",
    "KA05": "Bangalore South (Jayanagar)",
    "HR26": "Gurugram (North)",
    "HR51": "Faridabad",
    "UP14": "Ghaziabad",
    "UP16": "Gautam Buddha Nagar (Noida)",
    "UP32": "Lucknow",
    "RJ14": "Jaipur South",
    "GJ01": "Ahmedabad",
}


def decode_indian_plate(raw_plate: str | None) -> dict:
    if not raw_plate:
        return {"is_valid": False, "category": "Unknown", "state": "Unknown", "rto_office": "—", "series": "—"}

    cleaned = re.sub(r"[^A-Z0-9]", "", raw_plate.upper().strip())

    # 1. Bharat Series: YY BH #### XX (e.g. 22BH1234AA)
    bh_match = re.match(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$", cleaned)
    if bh_match:
        year, num, alpha = bh_match.groups()
        return {
            "is_valid": True,
            "plate": cleaned,
            "category": "Pan-India Bharat Series",
            "state": "Central Government / Defence / Pan-India (BH)",
            "registration_year": f"20{year}",
            "rto_office": "Ministry of Road Transport (MoRTH)",
            "plate_type": "Private / Defense Transferable",
            "series": f"BH-{alpha}",
            "is_commercial": False
        }

    # 2. Standard State Series: SS DD AA #### (e.g. DL 01 AB 1234, MH 12 DE 4567)
    std_match = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$", cleaned)
    if std_match:
        state_code, rto_num, series_alpha, num = std_match.groups()
        rto_key = f"{state_code}{rto_num.zfill(2)}"
        state_name = STATE_NAMES.get(state_code, f"State Code ({state_code})")
        rto_name = POPULAR_RTOS.get(rto_key, f"RTO District #{rto_num.zfill(2)}, {state_name}")

        is_commercial = any(ch in series_alpha for ch in ("T", "Y", "P", "V")) or (state_code == "DL" and "C" in series_alpha)
        is_ev = "EV" in series_alpha

        category = "Electric Vehicle" if is_ev else ("Commercial Transport" if is_commercial else "Private Passenger Vehicle")
        plate_type = "Green HSRP (EV)" if is_ev else ("Yellow HSRP (Commercial)" if is_commercial else "White HSRP (Private)")

        return {
            "is_valid": True,
            "plate": cleaned,
            "state_code": state_code,
            "state": state_name,
            "rto_code": rto_key,
            "rto_office": rto_name,
            "series": series_alpha or "General",
            "number": num.zfill(4),
            "category": category,
            "plate_type": plate_type,
            "is_commercial": is_commercial,
            "is_ev": is_ev
        }

    return {
        "is_valid": False,
        "plate": cleaned,
        "category": "Unregistered / Custom Series",
        "state": "Non-Standard Indian Plate",
        "rto_office": "—",
        "series": "—",
        "is_commercial": False
    }
