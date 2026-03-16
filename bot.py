import ee
import os
import json
import requests
import logging
import time
import re
from datetime import datetime

TELEGRAM_TOKEN="8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
ADMIN_ID="1145085024"

logging.basicConfig(level=logging.INFO)
log=logging.getLogger(__name__)

last_update_id=0

service_account=json.loads(os.environ["GEE_KEY"])

credentials=ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# ================= TELEGRAM =================

def tg(msg,chat_id):

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id":chat_id,"text":msg,"parse_mode":"HTML"},
            timeout=15
        )
    except:
        log.error("Telegram send failed")

# ================= LOCATION =================

def get_location(lat,lon):

    try:

        r=requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat":lat,"lon":lon,"format":"json"},
            headers={"User-Agent":"soilbot"},
            timeout=10
        )

        addr=r.json()["address"]

        city=addr.get("city") or addr.get("town") or addr.get("county") or ""
        state=addr.get("state","")
        country=addr.get("country","")

        return f"{city}, {state}, {country}"

    except:
        return "Tidak terdeteksi"

# ================= ROAD =================

def get_road(lat,lon):

    try:

        q=f"""
        [out:json];
        way(around:100,{lat},{lon})["highway"];
        out tags 1;
        """

        r=requests.post(
            "https://overpass-api.de/api/interpreter",
            data=q,
            timeout=10
        )

        data=r.json()

        if not data["elements"]:
            return None

        return data["elements"][0]["tags"].get("name")

    except:
        return None

# ================= SOIL =================

def get_soil_profile(lat,lon):

    point=ee.Geometry.Point([lon,lat])

    depths=["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]

    clay=ee.Image("projects/soilgrids-isric/clay_mean")
    sand=ee.Image("projects/soilgrids-isric/sand_mean")
    silt=ee.Image("projects/soilgrids-isric/silt_mean")
    bdod=ee.Image("projects/soilgrids-isric/bdod_mean")
    soc=ee.Image("projects/soilgrids-isric/soc_mean")

    profile={}

    for d in depths:

        img=clay.select(f"clay_{d}_mean")\
        .addBands(sand.select(f"sand_{d}_mean"))\
        .addBands(silt.select(f"silt_{d}_mean"))\
        .addBands(bdod.select(f"bdod_{d}_mean"))\
        .addBands(soc.select(f"soc_{d}_mean"))

        vals=img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=250,
            bestEffort=True
        ).getInfo()

        profile[d]={
            "clay":vals.get(f"clay_{d}_mean",0)/10,
            "sand":vals.get(f"sand_{d}_mean",0)/10,
            "silt":vals.get(f"silt_{d}_mean",0)/10,
            "bdod":vals.get(f"bdod_{d}_mean",0)/100,
            "soc":vals.get(f"soc_{d}_mean",0)/100
        }

    return profile

# ================= AGGREGATE LAYER =================

def aggregate_profile(profile):

    def avg(keys,field):
        return sum(profile[k][field] for k in keys)/len(keys)

    agg={}

    agg["0-30cm"]={
        "clay":avg(["0-5cm","5-15cm","15-30cm"],"clay"),
        "sand":avg(["0-5cm","5-15cm","15-30cm"],"sand"),
        "silt":avg(["0-5cm","5-15cm","15-30cm"],"silt"),
        "bdod":avg(["0-5cm","5-15cm","15-30cm"],"bdod"),
        "soc":avg(["0-5cm","5-15cm","15-30cm"],"soc")
    }

    agg["30-60cm"]=profile["30-60cm"]
    agg["60-100cm"]=profile["60-100cm"]

    return agg

# ================= TERRAIN =================

def get_slope(lat,lon):

    point=ee.Geometry.Point([lon,lat])

    dem=ee.Image("USGS/SRTMGL1_003")
    slope=ee.Terrain.slope(dem)

    val=slope.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=30
    ).get("slope")

    return ee.Number(val).getInfo()

# ================= RAIN =================

def get_rain(lat,lon):

    point=ee.Geometry.Point([lon,lat])

    rain=ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")\
        .filterDate("2015-01-01","2024-01-01")\
        .sum()

    val=rain.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=5000
    ).get("precipitation")

    return ee.Number(val).getInfo()/9

# ================= CLASSIFY =================

def classify_soil(clay,sand,silt):

    if clay>=sand and clay>=silt:
        return "Lempung"

    if silt>=clay and silt>=sand:
        return "Lanau"

    return "Pasir"

# ================= PEAT =================

def detect_peat(soc,bdod):
    return soc>=20 and bdod<=1.2

# ================= CBR =================

def estimate_cbr(clay,sand,silt,bdod,soc,rain):

    if soc>20 and bdod<1.15:
        return 1

    if clay>45:
        cbr=3
    elif clay>35:
        cbr=4
    elif clay>25:
        cbr=6
    elif sand>60:
        cbr=15
    else:
        cbr=8

    if bdod>1.35:
        cbr*=1.3
    elif bdod<1.1:
        cbr*=0.7

    if rain>2500:
        cbr*=0.85

    return round(cbr,1)

# ================= HARD LAYER =================

def estimate_hard_layer(profile):

    bd=profile["60-100cm"]["bdod"]

    if bd>=1.45:
        return "±0.8 m"

    if bd>=1.38:
        return "±1.0 m"

    if bd>=1.32:
        return "±1.3 m"

    if bd>=1.28:
        return "±1.6 m"

    return ">2 m"

# ================= CONFIDENCE =================

def model_confidence(clay,sand,silt,bdod):

    score=70

    if bdod>1.35:
        score+=5

    if bdod<1.1:
        score-=10

    return max(60,min(score,85))

# ================= ANALYZE =================

def analyze_soil(lat,lon,chat_id):

    tg("⏳ Menganalisis tanah...",chat_id)

    raw_profile=get_soil_profile(lat,lon)
    profile=aggregate_profile(raw_profile)

    location=get_location(lat,lon)
    road=get_road(lat,lon)

    rain=get_rain(lat,lon)
    slope=get_slope(lat,lon)

    clay=profile["30-60cm"]["clay"]
    sand=profile["30-60cm"]["sand"]
    silt=profile["30-60cm"]["silt"]
    soc=profile["30-60cm"]["soc"]
    bdod=profile["30-60cm"]["bdod"]

    soil_type=classify_soil(clay,sand,silt)

    peat=detect_peat(raw_profile["0-5cm"]["soc"],raw_profile["0-5cm"]["bdod"])

    cbr=estimate_cbr(clay,sand,silt,bdod,soc,rain)

    hard=estimate_hard_layer(profile)

    confidence=model_confidence(clay,sand,silt,bdod)

    msg=f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 Koordinat
{lat}, {lon}

🗺 Wilayah
{location}

🛣 Jalan
{road if road else "Tidak terdeteksi"}

━━━━━━━━━━━━
🔎 <b>RINGKASAN CEPAT</b>

🪨 Jenis tanah dominan
<b>{soil_type}</b>

🚧 Estimasi CBR
<b>{cbr}%</b>

🌧 Curah hujan
<b>{rain:.0f} mm/tahun</b>

⛰ Kemiringan lereng
<b>{slope:.1f}°</b>

🧱 Perkiraan tanah keras
<b>{hard}</b>

🤖 Kepercayaan AI
<b>{confidence}%</b>

{"🌱 Indikasi gambut" if peat else "🌱 Tidak terindikasi gambut"}

━━━━━━━━━━━━
🪨 <b>PROFIL TANAH (0–1 m)</b>
"""

    for d,data in profile.items():

        soil=classify_soil(data["clay"],data["sand"],data["silt"])

        msg+=f"""

{d}
Jenis tanah : {soil}
Clay {data["clay"]:.1f} %
Sand {data["sand"]:.1f} %
Silt {data["silt"]:.1f} %
Bulk Density {data["bdod"]:.2f} g/cm³
Organic Carbon {data["soc"]:.1f} %
"""

    msg+=f"""

━━━━━━━━━━━━
⚠ <b>DAMPAK TERHADAP PERKERASAN</b>

1. Retak reflektif akibat kembang susut tanah
2. Rutting / ambles akibat daya dukung rendah
3. Genangan air saat hujan tinggi

🛠 <b>REKOMENDASI PENANGANAN</b>

• Stabilisasi kapur 5–8% atau semen
• Geotextile pada subgrade
• Drainase baik

🔬 <b>PENGUJIAN TANAH</b>

• Field CBR
• Atterberg limits
• DCP test
• Sondir / CPT

━━━━━━━━━━━━
🤖 <b>CATATAN ANALISIS AI</b>

Analisis ini merupakan <b>preliminary assessment</b> berbasis SoilGrids melalui Google Earth Engine.

Hasil digunakan sebagai indikasi awal kondisi tanah dan tidak menggantikan investigasi geoteknik lapangan.
"""

    tg(msg,chat_id)

# ================= LOOP =================

def check_messages():

    global last_update_id

    while True:

        try:

            r=requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}",
                timeout=20
            ).json()

            for update in r.get("result",[]):

                last_update_id=update["update_id"]

                msg=update.get("message",{})

                chat_id=str(msg.get("chat",{}).get("id",""))
                text=msg.get("text","")

                coord=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if coord:

                    lat=float(coord.group(1))
                    lon=float(coord.group(2))

                    analyze_soil(lat,lon,chat_id)

        except Exception as e:

            log.error(e)

        time.sleep(2)

# ================= MAIN =================

def main():

    log.info("Soil AI Bot starting")

    tg("🤖 AI Soil Analyzer siap digunakan",ADMIN_ID)

    check_messages()

main()
