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

# ================= SAFE =================
def safe(v,div):
    if v is None:
        return None
    return v/div

# ================= SOIL =================
def get_soil_profile(lat,lon):

    point=ee.Geometry.Point([lon,lat])
    soil=ee.Image("projects/soilgrids-isric/soilgrids_250m")

    depths=["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]

    profile={}

    for d in depths:

        bands=[
            f"clay_{d}_mean",
            f"sand_{d}_mean",
            f"silt_{d}_mean",
            f"bdod_{d}_mean",
            f"soc_{d}_mean"
        ]

        vals=soil.select(bands).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=250,
            bestEffort=True
        ).getInfo()

        profile[d]={
            "clay":safe(vals.get(bands[0]),10),
            "sand":safe(vals.get(bands[1]),10),
            "silt":safe(vals.get(bands[2]),10),
            "bdod":safe(vals.get(bands[3]),100),
            "soc":safe(vals.get(bands[4]),100)
        }

    return profile

# ================= AGGREGATE =================
def aggregate(p):

    def avg(keys,f):
        vals=[p[k][f] for k in keys if p[k][f] is not None]
        return sum(vals)/len(vals) if vals else 0

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

def classify(c,s,si):

    if c>=s and c>=si:
        return "Lempung"

    if si>=c and si>=s:
        return "Lanau"

    return "Pasir"

def peat(soc,bdod):
    return soc and soc>20 and bdod and bdod<1.2

def estimate_cbr(c,s,si,bdod,soc,rain):

    if soc and soc>20:
        return 1.5

    if c>45: v=3
    elif c>35: v=4
    elif c>25: v=6
    elif s>60: v=15
    else: v=8

    if bdod:
        if bdod>1.35: v*=1.3
        elif bdod<1.1: v*=0.7

    if rain>2500:
        v*=0.85

    return round(v,1)

# ================= AUTO DETECT =================

def soil_origin(slope,rain,sand):

    if slope<3:
        return "Alluvial (endapan sungai)"

    if slope>8:
        return "Residual (pelapukan batuan)"

    if sand>50:
        return "Material berpasir (kemungkinan fluvial/pantai)"

    return "Transisi / campuran"

# ================= SETTLEMENT =================

def settlement(cbr,clay,soc):

    if soc and soc>20:
        return "Sangat besar (>10 cm)"

    if cbr<3:
        return "Besar (5–10 cm)"

    if cbr<6:
        return "Sedang (2–5 cm)"

    if clay>40:
        return "Sedang (2–5 cm)"

    return "Kecil (<2 cm)"

# ================= HARD LAYER =================

def hard_layer(bd):

    if bd>=1.45: return "±0.8 m"
    if bd>=1.38: return "±1.0 m"
    if bd>=1.32: return "±1.3 m"
    if bd>=1.28: return "±1.6 m"

    return ">2 m"

# ================= ANALYZE =================

def analyze(lat,lon,chat_id):

    tg("⏳ Analisis berjalan...",chat_id)

    raw=get_soil_profile(lat,lon)
    p=aggregate(raw)

    rain=get_rain(lat,lon)
    slope=get_slope(lat,lon)

    clay=p["30-60cm"]["clay"]
    sand=p["30-60cm"]["sand"]
    silt=p["30-60cm"]["silt"]
    soc=p["30-60cm"]["soc"]
    bd=p["30-60cm"]["bdod"]

    soil=classify(clay,sand,silt)

    is_peat=peat(raw["0-5cm"]["soc"],raw["0-5cm"]["bdod"])

    cbr=estimate_cbr(clay,sand,silt,bd,soc,rain)

    origin=soil_origin(slope,rain,sand)

    settle=settlement(cbr,clay,soc)

    hard=hard_layer(bd if bd else 0)

    msg=f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 {lat}, {lon}

━━━━━━━━━━━━
🔎 <b>RINGKASAN</b>

Jenis tanah: <b>{soil}</b>
CBR: <b>{cbr}%</b>
Curah hujan: <b>{rain:.0f} mm</b>
Kemiringan: <b>{slope:.1f}°</b>
Tanah keras: <b>{hard}</b>

🌍 Asal tanah: <b>{origin}</b>
📉 Potensi penurunan: <b>{settle}</b>

{"🌱 Gambut terindikasi" if is_peat else "🌱 Bukan gambut"}

━━━━━━━━━━━━
🪨 <b>PROFIL TANAH</b>
"""

    for d,data in p.items():

        msg+=f"""
{d}
{classify(data["clay"],data["sand"],data["silt"])}
Clay {data["clay"]:.1f}%
Sand {data["sand"]:.1f}%
Silt {data["silt"]:.1f}%
"""

    msg+=f"""

━━━━━━━━━━━━
⚠ <b>DAMPAK</b>

1. Retak
2. Ambles
3. Genangan

━━━━━━━━━━━━
🤖 Preliminary AI — wajib verifikasi lapangan
"""

    tg(msg,chat_id)

# ================= LOOP =================

def loop():

    global last_update_id

    while True:

        try:

            r=requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}",
                timeout=20
            ).json()

            for u in r.get("result",[]):

                last_update_id=u["update_id"]

                text=u["message"]["text"]
                chat=str(u["message"]["chat"]["id"])

                coord=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if coord:
                    analyze(float(coord.group(1)),float(coord.group(2)),chat)

        except Exception as e:
            log.error(e)

        time.sleep(2)

# ================= MAIN =================

def main():
    log.info("Bot running")
    tg("🤖 Soil AI siap",ADMIN_ID)
    loop()

main()
