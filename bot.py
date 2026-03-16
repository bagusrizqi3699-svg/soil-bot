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
USERS_FILE="users.json"
DAILY_LIMIT=20

logging.basicConfig(level=logging.INFO)
log=logging.getLogger(__name__)

last_update_id=0

# ================= EARTH ENGINE =================

service_account=json.loads(os.environ["GEE_KEY"])

credentials=ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# ================= TELEGRAM =================

def tg(msg,chat_id):

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":chat_id,"text":msg,"parse_mode":"HTML"},
        timeout=30
    )

# ================= USER STORAGE =================

def load_users():

    if not os.path.exists(USERS_FILE):

        return {"approved":[ADMIN_ID],"pending":[],"usage":{}}

    with open(USERS_FILE,"r") as f:

        return json.load(f)

def save_users(data):

    with open(USERS_FILE,"w") as f:

        json.dump(data,f)

# ================= USER CHECK =================

def check_user(chat_id):

    if chat_id==ADMIN_ID:
        return "approved"

    users=load_users()

    if chat_id in users["approved"]:
        return "approved"

    if chat_id in users["pending"]:
        return "pending"

    users["pending"].append(chat_id)

    save_users(users)

    tg(f"⚠ User baru meminta akses\nID: {chat_id}\n/approve {chat_id}",ADMIN_ID)

    return "new"

# ================= QUOTA =================

def check_quota(chat_id):

    if chat_id==ADMIN_ID:
        return True

    users=load_users()

    today=datetime.utcnow().strftime("%Y-%m-%d")

    if chat_id not in users["usage"]:
        users["usage"][chat_id]={}

    if today not in users["usage"][chat_id]:
        users["usage"][chat_id][today]=0

    if users["usage"][chat_id][today]>=DAILY_LIMIT:
        return False

    users["usage"][chat_id][today]+=1
    save_users(users)

    return True

# ================= LOCATION =================

def get_location(lat,lon):

    try:

        r=requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat":lat,"lon":lon,"format":"json"},
            headers={"User-Agent":"soilbot"}
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

        r=requests.post("https://overpass-api.de/api/interpreter",data=q)

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

# ================= INTERPRETATION =================

def classify_soil(clay,sand,silt):

    if clay>40 and silt>40:
        return "Lempung lanauan"

    if clay>40:
        return "Lempung"

    if clay>30 and sand>40:
        return "Lempung berpasir"

    if sand>60:
        return "Pasir"

    if silt>50:
        return "Lanau"

    return "Tanah campuran"

def detect_peat(soc,bdod):

    return soc>=20 and bdod<=1.2

def estimate_cbr(clay,sand,silt,soc,rain):

    if soc>20:
        cbr=1.5
    elif clay>45:
        cbr=3
    elif clay>35:
        cbr=4.5
    elif clay>25:
        cbr=6
    elif sand>60:
        cbr=15
    else:
        cbr=8

    if rain>2500:
        cbr*=0.8

    return round(cbr,1)

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

# ================= ANALYSIS =================

def analyze_soil(lat,lon,chat_id):

    tg("⏳ Menganalisis tanah...",chat_id)

    profile=get_soil_profile(lat,lon)

    location=get_location(lat,lon)
    road=get_road(lat,lon)

    rain=get_rain(lat,lon)
    slope=get_slope(lat,lon)

    clay=profile["30-60cm"]["clay"]
    sand=profile["30-60cm"]["sand"]
    silt=profile["30-60cm"]["silt"]
    soc=profile["30-60cm"]["soc"]

    soil_type=classify_soil(clay,sand,silt)

    peat=detect_peat(profile["0-5cm"]["soc"],profile["0-5cm"]["bdod"])

    cbr=estimate_cbr(clay,sand,silt,soc,rain)

    hard=estimate_hard_layer(profile)

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
"""

    msg+=f"""

🛠 <b>REKOMENDASI PENANGANAN</b>

• Stabilisasi kapur 5–8% atau semen
• Geotextile pada subgrade
• Drainase baik
"""

    msg+=f"""

🔬 <b>PENGUJIAN TANAH</b>

• Field CBR
• Atterberg limits
• DCP test
• Sondir / CPT
"""

    tg(msg,chat_id)

# ================= TELEGRAM LOOP =================

def check_messages():

    global last_update_id

    while True:

        try:

            r=requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}"
            ).json()

            for update in r.get("result",[]):

                last_update_id=update["update_id"]

                msg=update.get("message",{})

                chat_id=str(msg.get("chat",{}).get("id",""))
                text=msg.get("text","")

                if text.startswith("/approve") and chat_id==ADMIN_ID:

                    uid=text.split(" ")[1]

                    users=load_users()

                    users["approved"].append(uid)

                    save_users(users)

                    tg("✅ Approved",uid)

                    continue

                status=check_user(chat_id)

                if status!="approved":

                    tg("⛔ Menunggu persetujuan admin",chat_id)

                    continue

                if not check_quota(chat_id):

                    tg("⚠ Kuota harian habis",chat_id)

                    continue

                coord=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if coord:

                    lat=float(coord.group(1))
                    lon=float(coord.group(2))

                    analyze_soil(lat,lon,chat_id)

                else:

                    tg("📍 Kirim koordinat\n-7.6048,111.9102",chat_id)

        except Exception as e:

            log.error(e)

        time.sleep(2)

# ================= MAIN =================

def main():

    log.info("Soil AI Bot starting")

    tg("🤖 AI Soil Analyzer siap digunakan",ADMIN_ID)

    check_messages()

main()
