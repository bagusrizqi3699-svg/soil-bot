import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

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
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
    except:
        log.error("Telegram error")

# ================= SOIL =================
def get_soil_profile(lat, lon):

    point = ee.Geometry.Point([lon, lat])

    depths = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm"]

    datasets = {
        "clay": "projects/soilgrids-isric/clay_mean",
        "sand": "projects/soilgrids-isric/sand_mean",
        "silt": "projects/soilgrids-isric/silt_mean",
        "bdod": "projects/soilgrids-isric/bdod_mean",
        "soc":  "projects/soilgrids-isric/soc_mean"
    }

    profile = {}

    for d in depths:

        profile[d] = {}

        for prop, ds in datasets.items():

            band = f"{prop}_{d}_mean"

            try:
                val = ee.Image(ds).select(band).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=point,
                    scale=250,
                    bestEffort=True
                ).get(band)

                val = ee.Number(val).getInfo() if val is not None else None

            except:
                val = None

            # scaling
            if val is not None:
                if prop in ["clay", "sand", "silt"]:
                    val = val / 10
                elif prop in ["bdod", "soc"]:
                    val = val / 100

            profile[d][prop] = val

    return profile

# ================= AGGREGATE =================
def aggregate(p):

    def avg(keys, f):
        vals = [p[k][f] for k in keys if p[k][f] is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "0-30cm": {
            "clay": avg(["0-5cm", "5-15cm", "15-30cm"], "clay"),
            "sand": avg(["0-5cm", "5-15cm", "15-30cm"], "sand"),
            "silt": avg(["0-5cm", "5-15cm", "15-30cm"], "silt"),
            "bdod": avg(["0-5cm", "5-15cm", "15-30cm"], "bdod"),
            "soc":  avg(["0-5cm", "5-15cm", "15-30cm"], "soc")
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
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=30
        ).get("slope")

        if val is None:
            return 0.0

        return ee.Number(val).getInfo()

    except:
        return 0.0

# ================= RAIN =================
def get_rain(lat, lon):

    point = ee.Geometry.Point([lon, lat])

    try:
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate("2015-01-01", "2024-01-01") \
            .sum()

        val = rain.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=5000
        ).get("precipitation")

        if val is None:
            return None

        return ee.Number(val).getInfo() / 9

    except:
        return None

# ================= MODEL =================

def classify(c, s, si):

    if c is None or s is None or si is None:
        return "N/A"

    if c >= s and c >= si:
        return "Lempung"
    if si >= c and si >= s:
        return "Lanau"
    return "Pasir"

def peat(soc, bdod):
    return soc is not None and soc > 20 and bdod is not None and bdod < 1.2

def estimate_cbr(c, s, si, bdod, soc, rain):

    # FIX: cek None sebelum operasi aritmatika
    if c is None or s is None or si is None:
        return None

    if soc is not None and soc > 20:
        return 1.5

    if c > 45:
        v = 3
    elif c > 35:
        v = 4
    elif c > 25:
        v = 6
    elif s > 60:
        v = 15
    else:
        v = 8

    if bdod:
        if bdod > 1.35:
            v *= 1.3
        elif bdod < 1.1:
            v *= 0.7

    if rain is not None and rain > 2500:
        v *= 0.85

    return round(v, 1)

# ================= SETTLEMENT =================
def estimate_settlement(cbr, clay, soc):

    if soc is not None and soc > 20:
        return "Sangat besar (>10 cm)"

    if cbr is None:
        return "N/A"

    if cbr < 3:
        return "Besar (5–10 cm)"

    if cbr < 6:
        return "Sedang (2–5 cm)"

    if clay is not None and clay > 40:
        return "Sedang (2–5 cm)"

    return "Kecil (<2 cm)"

def hard_layer(bd):

    if bd is None:
        return "N/A"

    if bd >= 1.45: return "±0.8 m"
    if bd >= 1.38: return "±1.0 m"
    if bd >= 1.32: return "±1.3 m"
    if bd >= 1.28: return "±1.6 m"

    return ">2 m"

# ================= ANALYZE =================

def analyze(lat, lon, chat_id):

    tg("⏳ Analisis tanah...", chat_id)

    raw = get_soil_profile(lat, lon)
    p = aggregate(raw)

    rain = get_rain(lat, lon)
    slope = get_slope(lat, lon)

    clay = p["30-60cm"]["clay"]
    sand = p["30-60cm"]["sand"]
    silt = p["30-60cm"]["silt"]
    soc  = p["30-60cm"]["soc"]
    bd   = p["30-60cm"]["bdod"]

    soil = classify(clay, sand, silt)

    is_peat = peat(raw["0-5cm"]["soc"], raw["0-5cm"]["bdod"])

    cbr = estimate_cbr(clay, sand, silt, bd, soc, rain)

    settlement = estimate_settlement(cbr, clay, soc)

    hard = hard_layer(bd)

    # FIX: format aman untuk nilai yang bisa None
    cbr_txt   = f"{cbr}%" if cbr is not None else "N/A"
    rain_txt  = f"{rain:.0f} mm/tahun" if rain is not None else "N/A"
    slope_txt = f"{slope:.1f}°" if slope is not None else "N/A"

    msg = f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 Koordinat
{lat}, {lon}

━━━━━━━━━━━━
🔎 <b>RINGKASAN CEPAT</b>

🪨 Jenis tanah dominan
<b>{soil}</b>

🚧 Estimasi CBR
<b>{cbr_txt}</b>

🌧 Curah hujan
<b>{rain_txt}</b>

⛰ Kemiringan lereng
<b>{slope_txt}</b>

🧱 Perkiraan tanah keras
<b>{hard}</b>

📉 Potensi penurunan
<b>{settlement}</b>

{"🌱 Tidak terindikasi gambut" if not is_peat else "🌱 Indikasi gambut"}

━━━━━━━━━━━━
🪨 <b>PROFIL TANAH (hingga 1 m)</b>
"""

    for d, data in p.items():

        clay_txt = f"{data['clay']:.1f}%" if data["clay"] is not None else "N/A"
        sand_txt = f"{data['sand']:.1f}%" if data["sand"] is not None else "N/A"
        silt_txt = f"{data['silt']:.1f}%" if data["silt"] is not None else "N/A"

        msg += f"""
{d}
Jenis tanah : {classify(data["clay"], data["sand"], data["silt"])}
Clay {clay_txt}
Sand {sand_txt}
Silt {silt_txt}
"""

    msg += f"""

━━━━━━━━━━━━
⚠ <b>DAMPAK TERHADAP PERKERASAN</b>

1. Retak reflektif akibat kembang susut tanah
2. Rutting / ambles akibat daya dukung rendah
3. Genangan air saat hujan tinggi

━━━━━━━━━━━━
🤖 <b>CATATAN ANALISIS AI</b>

Analisis ini merupakan <b>preliminary assessment</b> berbasis SoilGrids melalui Google Earth Engine.
Wajib verifikasi investigasi tanah lapangan.
"""

    tg(msg, chat_id)

# ================= LOOP =================

def loop():

    global last_update_id

    while True:

        try:

            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}",
                timeout=20
            ).json()

            for u in r.get("result", []):

                last_update_id = u["update_id"]

                # FIX: skip update yang bukan pesan teks biasa
                msg = u.get("message")
                if not msg or "text" not in msg:
                    continue

                text = msg["text"]
                chat = str(msg["chat"]["id"])

                coord = re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)", text)

                if coord:
                    analyze(float(coord.group(1)), float(coord.group(2)), chat)

        except Exception as e:
            log.error(e)

        time.sleep(2)

# ================= MAIN =================

def main():
    log.info("Bot running")
    tg("🤖 Soil AI siap digunakan", ADMIN_ID)
    loop()

main()
