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

service_account = json.loads(os.environ["GEE_KEY"])

credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=15
    )

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

def soil_category(clay, bdod, soc):
    if (soc and soc > 120) or (bdod and bdod < 0.5): return ("PEAT/GAMBUT", "🔴")
    elif clay > 50: return ("SANGAT LUNAK", "🔴")
    elif clay > 35: return ("LUNAK", "🟠")
    elif clay > 20: return ("SEDANG", "🟡")
    elif clay > 10: return ("AGAK PADAT", "🟢")
    else: return ("PADAT", "✅")

def is_expansive(clay, cec=None):
    score = 0
    if clay > 60: score += 2
    elif clay > 40: score += 1
    if cec:
        if cec > 15: score += 2
        elif cec > 10: score += 1
    if score >= 3: return ("TINGGI", "🔴", 80)
    elif score >= 2: return ("SEDANG", "🟡", 55)
    else: return ("RENDAH", "✅", 20)

def is_peat(soc, bdod):
    return (soc and soc > 120) or (bdod and bdod < 0.5)

def estimate_cbr(clay, sand, bdod):
    if bdod and bdod < 0.5: return "<1% (Peat — tidak layak)"
    if clay > 50: return "1-3%"
    elif clay > 35: return "3-5%"
    elif clay > 20: return "5-8%"
    elif sand > 60: return "10-20%"
    else: return "6-10%"

def calc_risks(clay, sand, silt, bdod, soc, cec):

    risks = []

    if clay > 35:

        exp_lvl, _, exp_pct = is_expansive(clay, cec)

        risks += [
            ("Retak Reflektif", min(95, 40+int(clay)), "🔴" if clay>50 else "🟠",
             f"Clay {clay:.0f}% → aspal retak ikuti pola kembang-susut tanah"),

            ("Rutting/Ambles", min(90, 35+int(clay)), "🔴" if clay>50 else "🟠",
             "Subgrade lunak, CBR rendah"),

            ("Heave (Terangkat)", exp_pct, "🔴" if exp_pct>60 else "🟡",
             f"Ekspansif {exp_lvl}"),

            ("Banjir/Genangan", min(85, 30+int(clay)), "🔴" if clay>45 else "🟠",
             "Clay tinggi → air sulit meresap"),
        ]

    risks.sort(key=lambda x: x[1], reverse=True)

    return risks

def recommend(clay, sand, silt, bdod, soc, cec):

    if clay > 35:
        return [
            f"Stabilisasi: Kapur 5-8% atau Semen 3-5%",
            "Geotextile wajib",
            "Agregat kelas A min 25-30cm",
            "Drainase prioritas tinggi",
            "CBR lapangan wajib"
        ]

    elif clay > 20:
        return [
            "Stabilisasi kapur 3-5%",
            "Agregat kelas B min 20cm",
            "Geotextile disarankan",
            "Drainase saluran tepi"
        ]

    else:
        return [
            "Subgrade cukup baik",
            "Agregat kelas B min 15cm"
        ]

def analyze_soil(lat, lon, chat_id):

    tg(f"⏳ Analisis tanah...\n📍 {lat}, {lon}", chat_id)

    try:
        all_depths = get_soil_all(lat, lon)
    except Exception as e:
        tg(f"❌ Error: {str(e)}", chat_id)
        return

    msg = f"📍 <b>LAPORAN TANAH — ROAD ENGINEERING</b>\nKoordinat: {lat},{lon}\n\n"

    for depth, d in all_depths.items():

        clay = d.get("clay",0)
        sand = d.get("sand",0)
        silt = d.get("silt",0)
        bdod = d.get("bdod")
        soc = d.get("soc")
        cec = d.get("cec")

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
    silt = md.get("silt",0)
    bdod = md.get("bdod")
    soc = md.get("soc")
    cec = md.get("cec")

    risks = calc_risks(clay,sand,silt,bdod,soc,cec)

    msg += "⚠️ RISIKO JALAN\n"

    for name,pct,emoji,desc in risks:
        msg += f"{emoji} {name}: {pct}%\n↳ {desc}\n"

    msg += f"\n📊 ESTIMASI CBR: {estimate_cbr(clay,sand,bdod)}\n\n"

    recs = recommend(clay,sand,silt,bdod,soc,cec)

    msg += "💡 REKOMENDASI\n"

    for r in recs:
        msg += f"• {r}\n"

    tg(msg, chat_id)

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

def main():

    tg("✅ Soil Analyzer aktif!")

    check_messages()

main()
