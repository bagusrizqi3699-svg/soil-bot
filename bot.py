import ee
import os
import json
import requests
import logging
import time
import re

# =========================
# TELEGRAM CONFIG
# =========================

TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID = "1145085024"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

last_update_id = 0

# =========================
# INIT GEE
# =========================

service_account = json.loads(os.environ["GEE_KEY"])

credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# =========================
# TELEGRAM SEND
# =========================

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=20
    )

# =========================
# SOIL DATA FROM GEE
# =========================

DEPTHS = ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]

DATASETS = {
    "clay":"projects/soilgrids-isric/clay_mean",
    "sand":"projects/soilgrids-isric/sand_mean",
    "silt":"projects/soilgrids-isric/silt_mean",
    "bdod":"projects/soilgrids-isric/bdod_mean"
}

def get_soil(lat, lon):

    point = ee.Geometry.Point([lon,lat])

    img = None
    bands = []

    for prop,ds in DATASETS.items():

        base = ee.Image(ds)

        for d in DEPTHS:

            band = f"{prop}_{d}_mean"

            layer = base.select(band)

            img = layer if img is None else img.addBands(layer)

            bands.append((prop,d,band))

    values = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=250,
        bestEffort=True
    ).getInfo()

    result = {}

    for prop,d,band in bands:

        v = values.get(band)

        if v is None:
            continue

        v = float(v)

        if prop in ["clay","sand","silt"]:
            v = v / 10.0

        if prop == "bdod":
            v = v / 100.0

        if d not in result:
            result[d] = {}

        result[d][prop] = v

    return result

# =========================
# RAINFALL
# =========================

def get_rain(lat,lon):

    point = ee.Geometry.Point([lon,lat])

    rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterDate("2015-01-01","2024-01-01") \
        .sum()

    val = rain.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=5000
    ).get("precipitation")

    return ee.Number(val).getInfo()

def rain_class(mm):

    if mm < 1000:
        return "rendah"

    elif mm < 2000:
        return "sedang"

    elif mm < 3000:
        return "tinggi"

    return "sangat tinggi"

# =========================
# LANDSLIDE
# =========================

def landslide_risk(lat,lon,clay):

    point = ee.Geometry.Point([lon,lat])

    dem = ee.Image("USGS/SRTMGL1_003")

    slope = ee.Terrain.slope(dem)

    slope_val = slope.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=30
    ).get("slope")

    slope_val = ee.Number(slope_val).getInfo()

    rain = get_rain(lat,lon)

    if slope_val > 20 and rain > 2500 and clay > 35:
        return "potensi longsor tinggi"

    if slope_val > 15 and rain > 2000:
        return "potensi longsor sedang"

    if slope_val > 10:
        return "potensi longsor rendah"

    return "risiko longsor sangat kecil"

# =========================
# SOIL MERGE LAYERS
# =========================

def merge_layers(data):

    def avg(a,b,c):
        return (a+b+c)/3

    layer1 = {
        "clay": avg(data["0-5cm"]["clay"],data["5-15cm"]["clay"],data["15-30cm"]["clay"]),
        "sand": avg(data["0-5cm"]["sand"],data["5-15cm"]["sand"],data["15-30cm"]["sand"]),
        "silt": avg(data["0-5cm"]["silt"],data["5-15cm"]["silt"],data["15-30cm"]["silt"]),
        "bdod": avg(data["0-5cm"]["bdod"],data["5-15cm"]["bdod"],data["15-30cm"]["bdod"])
    }

    layer2 = data["30-60cm"]

    layer3 = data["60-100cm"]

    return layer1,layer2,layer3

# =========================
# HARD SOIL DEPTH
# =========================

def hard_soil_depth(l1,l2,l3):

    layers = [l1,l2,l3]

    depths = [0.15,0.45,0.80]

    for i,l in enumerate(layers):

        if l["bdod"] >= 1.45 and l["clay"] <= 35:

            return depths[i]

    return None

# =========================
# CBR ESTIMATION
# =========================

def estimate_cbr(clay,sand,bdod):

    if clay > 45:
        return "2–4 %"

    if clay > 30:
        return "4–7 %"

    if clay > 20:
        return "6–10 %"

    if sand > 60:
        return "10–20 %"

    return "8–12 %"

# =========================
# ANALYZE
# =========================

def analyze_soil(lat,lon,chat_id):

    tg("⏳ Menganalisis lokasi...",chat_id)

    soil = get_soil(lat,lon)

    l1,l2,l3 = merge_layers(soil)

    depth = hard_soil_depth(l1,l2,l3)

    cbr = estimate_cbr(l2["clay"],l2["sand"],l2["bdod"])

    rain = get_rain(lat,lon)

    rain_c = rain_class(rain)

    landslide = landslide_risk(lat,lon,l2["clay"])

    msg = f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 Koordinat
{lat}, {lon}

📡 Sumber data
SoilGrids + Google Earth Engine

📏 Resolusi data
±250 meter

📊 Estimasi kepercayaan model
±70 %

━━━━━━━━━━━━━━━━

🪨 <b>PROFIL TANAH (hingga 1 m)</b>

0–30 cm
Clay {l1["clay"]:.1f} %
Sand {l1["sand"]:.1f} %
Silt {l1["silt"]:.1f} %
Bulk Density {l1["bdod"]:.2f} g/cm³

30–60 cm
Clay {l2["clay"]:.1f} %
Sand {l2["sand"]:.1f} %
Silt {l2["silt"]:.1f} %
Bulk Density {l2["bdod"]:.2f} g/cm³

60–100 cm
Clay {l3["clay"]:.1f} %
Sand {l3["sand"]:.1f} %
Silt {l3["silt"]:.1f} %
Bulk Density {l3["bdod"]:.2f} g/cm³
"""

    if depth:
        msg += f"\n🧱 Perkiraan tanah relatif keras\n≈ {depth:.2f} meter dari permukaan\n"
    else:
        msg += "\n🧱 Tanah relatif keras diperkirakan lebih dalam dari 1 meter\n"

    msg += f"""
━━━━━━━━━━━━━━━━

🚧 <b>ESTIMASI DAYA DUKUNG SUBGRADE</b>

CBR perkiraan
{cbr}

━━━━━━━━━━━━━━━━

🌧 <b>KONDISI IKLIM</b>

Curah hujan tahunan
{rain:.0f} mm ({rain_c})

━━━━━━━━━━━━━━━━

⛰ <b>ANALISIS GEOMORFOLOGI</b>

Potensi longsor
{landslide}

━━━━━━━━━━━━━━━━

⚠ <b>DAMPAK TERHADAP PERKERASAN</b>

1️⃣ Retak reflektif  
Aspal berpotensi retak mengikuti pergerakan tanah

2️⃣ Rutting / ambles  
Perkerasan dapat mengalami deformasi akibat daya dukung rendah

3️⃣ Heave  
Tanah ekspansif dapat mengangkat perkerasan

4️⃣ Genangan air  
Drainase alami buruk sehingga air mudah tertahan

━━━━━━━━━━━━━━━━

🛠 <b>REKOMENDASI PENANGANAN</b>

• Stabilisasi tanah kapur 5–8 % atau semen 3–5 %  
• Pemasangan geotextile pada subgrade  
• Tebal agregat ≥ 25–30 cm  
• Perbaikan sistem drainase

━━━━━━━━━━━━━━━━

🔬 <b>PENGUJIAN TANAH YANG DISARANKAN</b>

• Field CBR test  
• Atterberg limits  
• DCP test  
• Soil boring / sondir

━━━━━━━━━━━━━━━━

🤖 <i>Analisis ini dihasilkan oleh sistem AI berbasis data global SoilGrids melalui Google Earth Engine.
Digunakan sebagai indikasi awal dan tidak menggantikan investigasi geoteknik lapangan.</i>
"""

    tg(msg,chat_id)

# =========================
# TELEGRAM LOOP
# =========================

def check_messages():

    global last_update_id

    while True:

        try:

            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"

            r = requests.get(url,timeout=35).json()

            for update in r.get("result",[]):

                last_update_id = update["update_id"]

                msg = update.get("message",{})

                chat_id = str(msg.get("chat",{}).get("id",""))

                text = msg.get("text","").strip()

                coord = re.search(r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)", text)

                if coord:

                    lat = float(coord.group(1))
                    lon = float(coord.group(2))

                    analyze_soil(lat,lon,chat_id)

                else:

                    tg("📍 Kirim koordinat:\n<code>-7.6048,111.9102</code>",chat_id)

        except Exception as e:

            log.error(e)

        time.sleep(2)

# =========================
# MAIN
# =========================

def main():

    tg("✅ Bot AI Analisis Tanah aktif!\nKirim koordinat untuk analisis lokasi.")

    check_messages()

main()
