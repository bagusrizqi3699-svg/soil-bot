import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN="8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID="1145085024"

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

def tg(msg,chat_id=None):

    cid=chat_id or TELEGRAM_CHAT_ID

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":cid,"text":msg,"parse_mode":"HTML"},
        timeout=30
    )

# ================= LOCATION =================

def get_location(lat,lon):

    try:

        url="https://nominatim.openstreetmap.org/reverse"

        r=requests.get(url,params={
            "lat":lat,
            "lon":lon,
            "format":"json"
        },headers={"User-Agent":"soilbot"})

        addr=r.json()["address"]

        city=addr.get("city") or addr.get("town") or addr.get("county") or ""
        state=addr.get("state","")
        country=addr.get("country","")

        return f"{city}, {state}, {country}"

    except:
        return "Lokasi tidak diketahui"

# ================= ROAD =================

def get_road(lat,lon):

    try:

        url="https://overpass-api.de/api/interpreter"

        q=f"""
        [out:json];
        way(around:100,{lat},{lon})["highway"];
        out tags 1;
        """

        r=requests.post(url,data=q,timeout=20)
        data=r.json()

        if not data["elements"]:
            return None

        return data["elements"][0]["tags"].get("name")

    except:
        return None

# ================= SOIL PROFILE =================

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
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()

        profile[d]={
            "clay":vals.get(f"clay_{d}_mean",0)/10,
            "sand":vals.get(f"sand_{d}_mean",0)/10,
            "silt":vals.get(f"silt_{d}_mean",0)/10,
            "bdod":vals.get(f"bdod_{d}_mean",0)/100,
            "soc":vals.get(f"soc_{d}_mean",0)/100
        }

    return profile

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

def rain_class(mm):

    if mm<1000:
        return "rendah"
    if mm<2000:
        return "sedang"
    if mm<3000:
        return "tinggi"

    return "sangat tinggi"

# ================= HARD LAYER (REFINED) =================

def estimate_hard_layer(profile):

    d60 = profile["60-100cm"]["bdod"]

    if d60 >= 1.45:
        return "±0.8 m"

    if d60 >= 1.38:
        return "±1.0 m"

    if d60 >= 1.32:
        return "±1.3 m"

    if d60 >= 1.28:
        return "±1.6 m"

    return "> 2 m"

# ================= REST OF MODEL =================

def classify_soil(clay,sand,silt):

    if clay>40 and silt>40:
        return "Lempung Lanauan"

    if clay>40:
        return "Lempung"

    if clay>30 and sand>40:
        return "Lempung Berpasir"

    if silt>50:
        return "Lanau"

    if sand>60:
        return "Pasir"

    return "Tanah campuran"

def detect_peat(soc,bdod):

    if soc>=20 and bdod<=1.2:
        return True

    return False

def expansive(clay):

    return clay>45

def detect_soft(clay,bdod,soc):

    score=0

    if bdod<1.1:
        score+=1

    if clay>40:
        score+=1

    if soc>15:
        score+=1

    return score>=2

def estimate_cbr(clay,sand,silt,soc,rain):

    if soc>20:
        cbr=2
    elif clay>45:
        cbr=3
    elif clay>30:
        cbr=5
    elif silt>50:
        cbr=6
    elif sand>60:
        cbr=15
    else:
        cbr=8

    if rain>2500:
        cbr*=0.8

    return round(cbr,1)

# ================= IMPACT =================

def impacts(clay,sand,rain,peat,exp):

    out=[]

    if peat:
        out.append("Penurunan tanah besar akibat tanah organik")

    if clay>35:
        out.append("Retak reflektif akibat kembang susut lempung")

    if clay>30:
        out.append("Rutting atau ambles akibat daya dukung rendah")

    if exp:
        out.append("Potensi heave akibat lempung ekspansif")

    if rain>2000:
        out.append("Genangan air saat musim hujan")

    if sand>60:
        out.append("Erosi bahu jalan akibat material pasir")

    return out

# ================= RECOMMEND =================

def recommendations(clay,sand,cbr,peat):

    if peat:
        return [
        "Perbaikan tanah gambut (soil replacement)",
        "Preloading + vertical drain",
        "Geotextile atau geogrid reinforcement"
        ]

    if cbr<3:
        return [
        "Perkuatan tanah dasar",
        "Geogrid reinforcement"
        ]

    if clay>40:
        return [
        "Stabilisasi kapur 5–8%",
        "Geotextile pada subgrade",
        "Drainase baik"
        ]

    if sand>60:
        return [
        "Pemadatan tinggi",
        "Stabilisasi semen"
        ]

    return [
    "Perkerasan standar",
    "Drainase tepi jalan"
    ]

# ================= TEST =================

def tests(clay,sand):

    t=["Field CBR"]

    if clay>30:
        t.append("Atterberg limits")

    if sand>50:
        t.append("Sand cone test")

    t.append("DCP test")
    t.append("Sondir / CPT")

    return t
