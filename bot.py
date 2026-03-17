import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN="8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
ADMIN_ID="1145085024"

logging.basicConfig(level=logging.INFO)
log=logging.getLogger(__name__)

last_update_id=0

# ================= INIT GEE =================

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
        log.error("Telegram error")

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
        return f"{addr.get('city','')}, {addr.get('state','')}, {addr.get('country','')}"
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

# ================= SAFE DIV =================

def safe(v,div):
    try:
        if v is None:
            return 0
        return v/div
    except:
        return 0

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
            "clay":safe(vals.get(f"clay_{d}_mean"),10),
            "sand":safe(vals.get(f"sand_{d}_mean"),10),
            "silt":safe(vals.get(f"silt_{d}_mean"),10),
            "bdod":safe(vals.get(f"bdod_{d}_mean"),100),
            "soc":safe(vals.get(f"soc_{d}_mean"),100)
        }

    return profile

# ================= AGGREGATE =================

def aggregate_profile(p):

    def avg(keys,f):
        return sum(p[k][f] for k in keys)/len(keys)

    return {
        "0-30cm":{
            "clay":avg(["0-5cm","5-15cm","15-30cm"],"clay"),
            "sand":avg(["0-5cm","5-15cm","15-30cm"],"sand"),
            "silt":avg(["0-5cm","5-15cm","15-30cm"],"silt"),
            "bdod":avg(["0-5cm","5-15cm","15-30cm"],"bdod"),
            "soc":avg(["0-5cm","5-15cm","15-30cm"],"soc")
        },
        "30-60cm":p["30-60cm"],
        "60-100cm":p["60-100cm"]
    }

# ================= TERRAIN =================

def get_slope(lat,lon):

    point=ee.Geometry.Point([lon,lat])

    slope=ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))

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

# ================= MODEL =================

def classify_soil(c,s,si):
    if c>=s and c>=si: return "Lempung"
    if si>=c and si>=s: return "Lanau"
    return "Pasir"

def detect_peat(soc,bdod):
    return soc>=20 and bdod<=1.2

def estimate_cbr(c,s,si,bdod,soc,rain):

    if soc>20 and bdod<1.15: return 1

    if c>45: v=3
    elif c>35: v=4
    elif c>25: v=6
    elif s>60: v=15
    else: v=8

    if bdod>1.35: v*=1.3
    elif bdod<1.1: v*=0.7

    if rain>2500: v*=0.85

    return round(v,1)

def estimate_hard_layer(p):
    bd=p["60-100cm"]["bdod"]
    if bd>=1.45: return "±0.8 m"
    if bd>=1.38: return "±1.0 m"
    if bd>=1.32: return "±1.3 m"
    if bd>=1.28: return "±1.6 m"
    return ">2 m"

def model_confidence(c,s,si,bd):
    score=70
    if bd>1.35: score+=5
    if bd<1.1: score-=10
    return max(60,min(score,85))

# ================= ANALYZE =================

def analyze_soil(lat,lon,chat_id):

    log.info(f"Analyze {lat},{lon}")

    tg("⏳ Menganalisis tanah...",chat_id)

    raw=get_soil_profile(lat,lon)
    p=aggregate_profile(raw)

    loc=get_location(lat,lon)
    road=get_road(lat,lon)

    rain=get_rain(lat,lon)
    slope=get_slope(lat,lon)

    clay=p["30-60cm"]["clay"]
    sand=p["30-60cm"]["sand"]
    silt=p["30-60cm"]["silt"]
    soc=p["30-60cm"]["soc"]
    bdod=p["30-60cm"]["bdod"]

    soil=classify_soil(clay,sand,silt)
    peat=detect_peat(raw["0-5cm"]["soc"],raw["0-5cm"]["bdod"])

    cbr=estimate_cbr(clay,sand,silt,bdod,soc,rain)
    hard=estimate_hard_layer(p)
    conf=model_confidence(clay,sand,silt,bdod)

    msg=f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 Koordinat
{lat}, {lon}

🗺 Wilayah
{loc}

🛣 Jalan
{road if road else "Tidak terdeteksi"}

━━━━━━━━━━━━
🔎 <b>RINGKASAN CEPAT</b>

🪨 Jenis tanah dominan
<b>{soil}</b>

🚧 Estimasi CBR
<b>{cbr}%</b>

🌧 Curah hujan
<b>{rain:.0f} mm/tahun</b>

⛰ Kemiringan lereng
<b>{slope:.1f}°</b>

🧱 Perkiraan tanah keras
<b>{hard}</b>

🤖 Kepercayaan AI
<b>{conf}%</b>

{"🌱 Indikasi gambut" if peat else "🌱 Tidak terindikasi gambut"}

━━━━━━━━━━━━
🪨 <b>PROFIL TANAH (0–1 m)</b>
"""

    for d,data in p.items():
        msg+=f"""
{d}
Jenis tanah : {classify_soil(data["clay"],data["sand"],data["silt"])}
Clay {data["clay"]:.1f} %
Sand {data["sand"]:.1f} %
Silt {data["silt"]:.1f} %
Bulk Density {data["bdod"]:.2f} g/cm³
Organic Carbon {data["soc"]:.1f} %
"""

    msg+=f"""

━━━━━━━━━━━━
⚠ <b>DAMPAK TERHADAP PERKERASAN</b>

1. Retak reflektif
2. Rutting / ambles
3. Genangan air

🛠 <b>REKOMENDASI</b>

• Stabilisasi tanah
• Geotextile
• Drainase baik

🔬 <b>PENGUJIAN</b>

• Field CBR
• Atterberg
• DCP
• Sondir

━━━━━━━━━━━━
🤖 <b>CATATAN</b>

Preliminary AI analysis — wajib verifikasi lapangan.
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

            for u in r.get("result",[]):

                last_update_id=u["update_id"]

                msg=u.get("message",{})
                chat_id=str(msg.get("chat",{}).get("id",""))
                text=msg.get("text","")

                coord=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if coord:
                    analyze_soil(float(coord.group(1)),float(coord.group(2)),chat_id)

        except Exception as e:
            log.error(e)

        time.sleep(2)

# ================= MAIN =================

def main():
    log.info("Soil AI Bot starting")
    tg("🤖 AI Soil Analyzer siap digunakan",ADMIN_ID)
    check_messages()

main()
