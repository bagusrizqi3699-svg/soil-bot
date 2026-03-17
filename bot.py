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

# ================= SOIL =================
def get_soil_profile(lat,lon):

    point=ee.Geometry.Point([lon,lat])

    depths=["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]

    datasets={
        "clay":"projects/soilgrids-isric/clay_mean",
        "sand":"projects/soilgrids-isric/sand_mean",
        "silt":"projects/soilgrids-isric/silt_mean",
        "bdod":"projects/soilgrids-isric/bdod_mean",
        "soc":"projects/soilgrids-isric/soc_mean"
    }

    profile={}

    for d in depths:

        profile[d]={}

        for prop,ds in datasets.items():

            band=f"{prop}_{d}_mean"

            try:

                val=ee.Image(ds).select(band).reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=point,
                    scale=250,
                    bestEffort=True
                ).get(band)

                val=ee.Number(val).getInfo() if val else None

            except:
                val=None

            # scaling
            if val is not None:

                if prop in ["clay","sand","silt"]:
                    val=val/10

                elif prop in ["bdod","soc"]:
                    val=val/100

            profile[d][prop]=val if val is not None else 0

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
    return soc>20 and bdod<1.2

def estimate_cbr(c,s,si,bdod,soc,rain):

    if soc>20:
        return 1.5

    if c>45: v=3
    elif c>35: v=4
    elif c>25: v=6
    elif s>60: v=15
    else: v=8

    if bdod>1.35: v*=1.3
    elif bdod<1.1: v*=0.7

    if rain>2500:
        v*=0.85

    return round(v,1)

def soil_origin(slope,sand):

    if slope<3:
        return "Alluvial"
    if slope>8:
        return "Residual"
    if sand>50:
        return "Material berpasir"
    return "Transisi"

def settlement(cbr,clay,soc):

    if soc>20:
        return "Sangat besar (>10 cm)"
    if cbr<3:
        return "Besar (5–10 cm)"
    if cbr<6:
        return "Sedang (2–5 cm)"
    if clay>40:
        return "Sedang (2–5 cm)"
    return "Kecil (<2 cm)"

def hard_layer(bd):

    if bd>=1.45: return "±0.8 m"
    if bd>=1.38: return "±1.0 m"
    if bd>=1.32: return "±1.3 m"
    if bd>=1.28: return "±1.6 m"
    return ">2 m"

# ================= ANALYZE =================

def analyze(lat,lon,chat_id):

    tg("⏳ Analisis tanah...",chat_id)

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

    origin=soil_origin(slope,sand)

    settle=settlement(cbr,clay,soc)

    hard=hard_layer(bd)

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

{"🌱 Gambut" if is_peat else "🌱 Non gambut"}

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
⚠ Dampak: retak, ambles, genangan

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
    tg("🤖 Soil AI siap digunakan",ADMIN_ID)
    loop()

main()
