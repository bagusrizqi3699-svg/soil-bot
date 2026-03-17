import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
ADMIN_ID = "1145085024"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

last_update_id = 0

# ================= INIT GEE =================
service_account = json.loads(os.environ["GEE_KEY"])
credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)
ee.Initialize(credentials)

# ================= TELEGRAM =================
def tg(msg, chat_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
        if r.status_code != 200:
            log.error(f"TG error {r.status_code}: {r.text}")
        else:
            log.info("TG send status: 200")
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ================= REVERSE GEOCODE =================
def get_location_name(lat, lon):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "SoilAnalysisBot/1.0"},
            timeout=10
        )
        data = r.json()
        addr = data.get("address", {})
        local = (
            addr.get("village") or addr.get("town") or
            addr.get("city") or addr.get("municipality") or
            addr.get("county") or addr.get("state_district") or
            addr.get("state") or "Tidak diketahui"
        )
        region  = addr.get("state") or addr.get("province") or ""
        country = addr.get("country", "Tidak diketahui")
        cc      = addr.get("country_code", "").upper()
        return local, region, country, cc
    except Exception as e:
        log.error(f"Geocode error: {e}")
        return "Tidak diketahui", "", "Tidak diketahui", ""

def flag(cc):
    if not cc or len(cc) != 2:
        return ""
    return chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))

# ================= SOIL =================
def get_soil_profile(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    depth_index = {"0-5cm":0,"5-15cm":1,"15-30cm":2,"30-60cm":3,"60-100cm":4}
    datasets = {
        "clay":"projects/soilgrids-isric/clay_mean",
        "sand":"projects/soilgrids-isric/sand_mean",
        "silt":"projects/soilgrids-isric/silt_mean",
        "bdod":"projects/soilgrids-isric/bdod_mean",
        "soc": "projects/soilgrids-isric/soc_mean"
    }
    profile = {}
    for d, idx in depth_index.items():
        profile[d] = {}
        for prop, ds in datasets.items():
            try:
                img = ee.Image(ds).select(idx)
                result = img.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=point, scale=250, bestEffort=True
                )
                keys = result.keys().getInfo()
                val  = ee.Number(result.get(keys[0])).getInfo() if keys else None
            except Exception as e:
                log.error(f"GEE error [{prop}][{d}]: {e}")
                val = None
            if val is not None:
                if prop in ["clay","sand","silt"]: val = val / 10
                elif prop in ["bdod","soc"]:       val = val / 100
            profile[d][prop] = val
    log.info(f"Soil 30-60cm: {profile.get('30-60cm')}")
    return profile

def aggregate(p):
    def avg(keys, f):
        vals = [p[k][f] for k in keys if p[k][f] is not None]
        return sum(vals)/len(vals) if vals else None
    return {
        "0-30cm": {
            "clay": avg(["0-5cm","5-15cm","15-30cm"],"clay"),
            "sand": avg(["0-5cm","5-15cm","15-30cm"],"sand"),
            "silt": avg(["0-5cm","5-15cm","15-30cm"],"silt"),
            "bdod": avg(["0-5cm","5-15cm","15-30cm"],"bdod"),
            "soc":  avg(["0-5cm","5-15cm","15-30cm"],"soc")
        },
        "30-60cm":  p["30-60cm"],
        "60-100cm": p["60-100cm"]
    }

# ================= TERRAIN =================
def get_slope(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    try:
        slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
        val = slope.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=30
        ).get("slope")
        return ee.Number(val).getInfo() if val is not None else 0.0
    except Exception as e:
        log.error(f"GEE slope error: {e}")
        return 0.0

def get_rain(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    try:
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate("2015-01-01","2024-01-01").sum()
        val = rain.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=5000
        ).get("precipitation")
        return ee.Number(val).getInfo() / 9 if val is not None else None
    except Exception as e:
        log.error(f"GEE rain error: {e}")
        return None

# ================= CLASSIFICATION =================
def classify_detail(c, s, si):
    if c is None or s is None or si is None:
        return "N/A", "Data tidak tersedia"
    total = c + s + si
    if total == 0:
        return "N/A", "Data tidak valid"
    if c >= 40:
        if s > 20:  return "Lempung Berpasir",       "Dominan lempung dengan campuran pasir cukup signifikan"
        if si > 20: return "Lempung Berlanau",        "Dominan lempung dengan campuran lanau"
        return          "Lempung Murni",               "Sangat dominan lempung, plastisitas tinggi"
    if s >= 60:
        if c > 10:  return "Pasir Berlempung",        "Dominan pasir dengan campuran lempung"
        if si > 15: return "Pasir Berlanau",           "Dominan pasir dengan campuran lanau"
        return          "Pasir Murni",                 "Sangat dominan pasir, drainase sangat tinggi"
    if si >= 40:
        if c > 20:  return "Lanau Berlempung",        "Dominan lanau dengan campuran lempung"
        if s > 20:  return "Lanau Berpasir",           "Dominan lanau dengan campuran pasir"
        return          "Lanau Murni",                 "Sangat dominan lanau, rentan erosi"
    if c > 25 and s > 25 and si > 25:
        return          "Lempung Campuran (Loam)",     "Campuran seimbang — ideal untuk konstruksi"
    if c > s and c > si: return "Lempung Campuran",   "Lempung dominan dengan campuran pasir dan lanau"
    if s > si:           return "Pasir Campuran",     "Pasir dominan dengan campuran lempung dan lanau"
    return                      "Lanau Campuran",     "Lanau dominan dengan campuran lempung dan pasir"

def soil_emoji(name):
    for k, v in {"Lempung":"🟫","Lanau":"🟤","Pasir":"🟡","Loam":"🟢"}.items():
        if k in name: return v
    return "⬜"

def bar(val, max_val=100, length=10):
    if val is None: return "░" * length
    filled = max(0, min(length, round((val / max_val) * length)))
    return "█" * filled + "░" * (length - filled)

def peat(soc, bdod):
    return soc is not None and soc > 20 and bdod is not None and bdod < 1.2

# ================= CBR FIX =================
def estimate_cbr(c, s, si, bdod, soc, rain):
    if c is None or s is None or si is None:
        return None

    if soc is not None and soc > 20:
        return 1.5

    if s >= 70:
        v = 25
    elif s >= 55:
        v = 18
    elif s >= 45:
        v = 12
    elif c >= 40:
        v = 4
    elif c >= 30:
        v = 6
    else:
        v = 10

    if bdod is not None:
        if bdod >= 1.40:
            v *= 1.25
        elif bdod <= 1.20:
            v *= 0.75

    if rain is not None:
        if rain > 3000:
            v *= 0.75
        elif rain > 2000:
            v *= 0.85
        elif rain < 1200:
            v *= 1.10

    if s >= 50 and soc is not None and soc < 3:
        v = max(v, 8)
def main():
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook", timeout=10)
        log.info("Webhook deleted")
    except Exception as e:
        log.error(f"deleteWebhook error: {e}")
    log.info("Bot running")
    tg("Bot Soil AI siap digunakan!", ADMIN_ID)
    loop()

if __name__ == "__main__":
    main()
    return round(v, 1)
