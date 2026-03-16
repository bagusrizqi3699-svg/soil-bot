import ee
import os
import json
import requests
import logging
import time
import re

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
# TELEGRAM
# =========================

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=15
    )

# =========================
# SOIL FROM GEE
# =========================

def get_soil_all(lat, lon):

    point = ee.Geometry.Point([lon, lat])

    depths = [
        "0-5cm","5-15cm","15-30cm",
        "30-60cm","60-100cm","100-200cm"
    ]

    datasets = {
        "clay":"projects/soilgrids-isric/clay_mean",
        "sand":"projects/soilgrids-isric/sand_mean",
        "silt":"projects/soilgrids-isric/silt_mean",
        "bdod":"projects/soilgrids-isric/bdod_mean",
        "soc":"projects/soilgrids-isric/soc_mean",
        "cec":"projects/soilgrids-isric/cec_mean"
    }

    all_depths = {}

    for depth in depths:

        all_depths[depth] = {}

        for prop, ds in datasets.items():

            band = f"{prop}_{depth}_mean"

            img = ee.Image(ds).select(band)

            val = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=250
            ).get(band)

            if val is None:
                continue

            v = ee.Number(val).getInfo()

            if prop in ["clay","sand","silt"]:
                v = v / 10.0

            all_depths[depth][prop] = v

    for label, d in all_depths.items():
        if "clay" in d and "sand" in d and "silt" not in d:
            d["silt"] = max(0, 100 - d["clay"] - d["sand"])

    return all_depths

# =========================
# SOIL CLASS
# =========================

def classify_soil(clay, sand, silt):
    if clay >= 40 and silt >= 40: return "Silty Clay"
    elif clay >= 40: return "Clay"
    elif clay >= 35 and sand >= 45: return "Sandy Clay"
    elif clay >= 27 and 20 <= sand < 45: return "Clay Loam"
    elif clay >= 27 and silt >= 20: return "Silty Clay Loam"
    elif clay >= 20 and sand >= 45: return "Sandy Clay Loam"
    elif silt >= 80: return "Silt"
    elif silt >= 50 and clay < 27: return "Silt Loam"
    elif sand >= 85: return "Sand"
    elif sand >= 70 and clay < 15: return "Loamy Sand"
    elif clay < 15 and sand >= 52: return "Sandy Loam"
    else: return "Loam"

# =========================
# CATEGORY
# =========================

def soil_category(clay, bdod, soc):

    if (soc and soc > 120) or (bdod and bdod < 0.5):
        return ("PEAT/GAMBUT", "🔴")

    elif clay > 50:
        return ("SANGAT LUNAK", "🔴")

    elif clay > 35:
        return ("LUNAK", "🟠")

    elif clay > 20:
        return ("SEDANG", "🟡")

    elif clay > 10:
        return ("AGAK PADAT", "🟢")

    else:
        return ("PADAT", "✅")

# =========================
# CBR
# =========================

def estimate_cbr(clay, sand, bdod):

    if bdod and bdod < 0.5:
        return "<1% (Peat)"

    if clay > 50:
        return "1-3%"

    elif clay > 35:
        return "3-5%"

    elif clay > 20:
        return "5-8%"

    elif sand > 60:
        return "10-20%"

    else:
        return "6-10%"

# =========================
# ANALYZE
# =========================

def analyze_soil(lat, lon, chat_id):

    tg(f"⏳ Menganalisis tanah...\n📍 {lat}, {lon}", chat_id)

    try:

        all_depths = get_soil_all(lat, lon)

    except Exception as e:

        tg(f"❌ Gagal ambil data\n{str(e)}", chat_id)
        return

    msg = (
        f"📍 <b>LAPORAN TANAH — ROAD ENGINEERING</b>\n"
        f"Koordinat: {lat}, {lon}\n"
        f"Sumber: GEE SoilGrids\n\n"
    )

    for depth, d in all_depths.items():

        clay = d.get("clay",0)
        sand = d.get("sand",0)
        silt = d.get("silt",0)

        soil_type = classify_soil(clay,sand,silt)

        msg += (
            f"━━ {depth} ━━\n"
            f"Clay: {clay:.1f}%\n"
            f"Sand: {sand:.1f}%\n"
            f"Silt: {silt:.1f}%\n"
            f"Soil: {soil_type}\n\n"
        )

    md = all_depths["30-60cm"]

    clay = md.get("clay",0)
    sand = md.get("sand",0)
    bdod = md.get("bdod")

    msg += f"📊 CBR Estimate: {estimate_cbr(clay,sand,bdod)}"

    tg(msg, chat_id)

# =========================
# TELEGRAM LOOP
# =========================

def check_messages():

    global last_update_id

    while True:

        try:

            url = (
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
                f"?offset={last_update_id+1}&timeout=30"
            )

            r = requests.get(url,timeout=35).json()

            for update in r.get("result",[]):

                last_update_id = update["update_id"]

                msg = update.get("message",{})

                chat_id = str(msg.get("chat",{}).get("id",""))

                text = msg.get("text","").strip()

                coord = re.search(
                    r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)",
                    text
                )

                if coord:

                    lat = float(coord.group(1))
                    lon = float(coord.group(2))

                    analyze_soil(lat,lon,chat_id)

                else:

                    tg(
                        "📍 Kirim koordinat:\n<code>-7.6048,111.9102</code>",
                        chat_id
                    )

        except Exception as e:

            log.error(e)

        time.sleep(2)

# =========================
# MAIN
# =========================

def main():

    log.info("Soil Bot start")

    tg("✅ Soil Analyzer aktif!")

    check_messages()

main()
