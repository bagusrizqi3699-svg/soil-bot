import ee
import os
import json
import requests
import logging
import time
import re
from datetime import datetime

TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
ADMIN_ID = "1145085024"  # admin untuk approve
USERS_FILE = "users.json"
DAILY_LIMIT = 20

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

last_update_id = 0

# ================= EARTH ENGINE =================

service_account = json.loads(os.environ["GEE_KEY"])

credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# ================= TELEGRAM =================

def tg(msg, chat_id=None):
    cid = chat_id or ADMIN_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=30
    )

# ================= USER STORAGE =================

def load_users():

    if not os.path.exists(USERS_FILE):

        return {
            "approved": [],
            "pending": [],
            "usage": {}
        }

    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):

    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

# ================= USER CHECK =================

def check_user(chat_id):

    users = load_users()

    if chat_id in users["approved"]:
        return "approved"

    if chat_id in users["pending"]:
        return "pending"

    users["pending"].append(chat_id)

    save_users(users)

    tg(
        f"⚠ <b>User baru meminta akses</b>\n"
        f"ID: <code>{chat_id}</code>\n\n"
        f"/approve {chat_id}"
    )

    return "new"

# ================= QUOTA =================

def check_quota(chat_id):

    users = load_users()

    today = datetime.utcnow().strftime("%Y-%m-%d")

    if chat_id not in users["usage"]:
        users["usage"][chat_id] = {}

    if today not in users["usage"][chat_id]:
        users["usage"][chat_id][today] = 0

    if users["usage"][chat_id][today] >= DAILY_LIMIT:
        return False

    users["usage"][chat_id][today] += 1

    save_users(users)

    return True

# ================= LOCATION =================

def get_location(lat, lon):

    try:

        url = "https://nominatim.openstreetmap.org/reverse"

        r = requests.get(
            url,
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "soilbot"}
        )

        addr = r.json()["address"]

        city = addr.get("city") or addr.get("town") or addr.get("county") or ""
        state = addr.get("state", "")
        country = addr.get("country", "")

        return f"{city}, {state}, {country}"

    except:
        return "Lokasi tidak diketahui"

# ================= ROAD =================

def get_road(lat, lon):

    try:

        url = "https://overpass-api.de/api/interpreter"

        q = f"""
        [out:json];
        way(around:100,{lat},{lon})["highway"];
        out tags 1;
        """

        r = requests.post(url, data=q, timeout=20)
        data = r.json()

        if not data["elements"]:
            return None

        return data["elements"][0]["tags"].get("name")

    except:
        return None

# ================= SOIL PROFILE =================

def get_soil_profile(lat, lon):

    point = ee.Geometry.Point([lon, lat])

    depths = ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]

    clay = ee.Image("projects/soilgrids-isric/clay_mean")
    sand = ee.Image("projects/soilgrids-isric/sand_mean")
    silt = ee.Image("projects/soilgrids-isric/silt_mean")
    bdod = ee.Image("projects/soilgrids-isric/bdod_mean")
    soc = ee.Image("projects/soilgrids-isric/soc_mean")

    profile = {}

    for d in depths:

        img = clay.select(f"clay_{d}_mean")\
        .addBands(sand.select(f"sand_{d}_mean"))\
        .addBands(silt.select(f"silt_{d}_mean"))\
        .addBands(bdod.select(f"bdod_{d}_mean"))\
        .addBands(soc.select(f"soc_{d}_mean"))

        vals = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=250,
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()

        profile[d] = {
            "clay": vals.get(f"clay_{d}_mean",0)/10,
            "sand": vals.get(f"sand_{d}_mean",0)/10,
            "silt": vals.get(f"silt_{d}_mean",0)/10,
            "bdod": vals.get(f"bdod_{d}_mean",0)/100,
            "soc": vals.get(f"soc_{d}_mean",0)/100
        }

    return profile

# ================= MODEL =================

def classify_soil(clay,sand,silt):

    if clay>40 and silt>40:
        return "Lempung Lanauan"

    if clay>40:
        return "Lempung"

    if clay>30 and sand>40:
        return "Lempung Berpasir"

    if sand>60:
        return "Pasir"

    if silt>50:
        return "Lanau"

    return "Tanah campuran"

def estimate_cbr(clay,sand):

    if clay>45:
        return 3
    if clay>30:
        return 5
    if sand>60:
        return 15
    return 8

# ================= ANALYSIS =================

def analyze_soil(lat,lon,chat_id):

    tg("⏳ Menganalisis lokasi...",chat_id)

    profile = get_soil_profile(lat,lon)

    location = get_location(lat,lon)

    road = get_road(lat,lon)

    clay = profile["30-60cm"]["clay"]
    sand = profile["30-60cm"]["sand"]
    silt = profile["30-60cm"]["silt"]

    soil_type = classify_soil(clay,sand,silt)

    cbr = estimate_cbr(clay,sand)

    msg=f"""
🌍 <b>LAPORAN INTERPRETASI TANAH — AI ANALYSIS</b>

📍 Koordinat
{lat}, {lon}

🗺 Wilayah
{location}

🛣 Jalan
{road if road else "Tidak terdeteksi"}

━━━━━━━━━━━━

🪨 Jenis tanah dominan
<b>{soil_type}</b>

🚧 Estimasi CBR
<b>{cbr}%</b>

━━━━━━━━━━━━
🪨 <b>PROFIL TANAH</b>
"""

    for d,data in profile.items():

        soil = classify_soil(data["clay"],data["sand"],data["silt"])

        msg+=f"""
{d}
Jenis tanah : {soil}
Clay {data["clay"]:.1f} %
Sand {data["sand"]:.1f} %
Silt {data["silt"]:.1f} %
Bulk Density {data["bdod"]:.2f} g/cm³
Organic Carbon {data["soc"]:.1f} %
"""

    tg(msg,chat_id)

# ================= TELEGRAM LOOP =================

def check_messages():

    global last_update_id

    while True:

        try:

            url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"

            r=requests.get(url,timeout=35).json()

            for update in r.get("result",[]):

                last_update_id=update["update_id"]

                msg=update.get("message",{})

                chat_id=str(msg.get("chat",{}).get("id",""))

                text=msg.get("text","").strip()

                # ===== ADMIN COMMAND =====

                if text.startswith("/approve") and chat_id==ADMIN_ID:

                    uid=text.split(" ")[1]

                    users=load_users()

                    if uid in users["pending"]:
                        users["pending"].remove(uid)

                    if uid not in users["approved"]:
                        users["approved"].append(uid)

                    save_users(users)

                    tg(f"✅ User {uid} disetujui")

                    tg("🎉 Akses bot telah disetujui.",uid)

                    continue

                # ===== USER CHECK =====

                status=check_user(chat_id)

                if status=="new":

                    tg("⛔ Bot memerlukan izin admin.",chat_id)
                    continue

                if status=="pending":

                    tg("⏳ Menunggu persetujuan admin.",chat_id)
                    continue

                if not check_quota(chat_id):

                    tg("⚠ Kuota harian habis.",chat_id)
                    continue

                # ===== COORDINATE =====

                coord=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if coord:

                    lat=float(coord.group(1))
                    lon=float(coord.group(2))

                    analyze_soil(lat,lon,chat_id)

                else:

                    tg("📍 Kirim koordinat\n<code>-7.6048,111.9102</code>",chat_id)

        except Exception as e:

            log.error(f"Telegram loop error: {e}")

        time.sleep(2)

# ================= MAIN =================

def main():

    log.info("Soil AI Bot starting")

    tg(
        "🤖 <b>AI Analisis Tanah siap digunakan</b>\n\n"
        "Bot menggunakan sistem approval admin.\n"
        "Kirim pesan untuk meminta akses."
    )

    check_messages()

main()
