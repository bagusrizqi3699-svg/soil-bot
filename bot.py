import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
ADMIN_ID = "1145085024"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

last_update_id = 0

# ================= INIT GEE =================
service_account = json.loads(os.environ["GEE_KEY"])

credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# ================= TELEGRAM =================
def tg(msg, chat_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
        if r.status_code != 200:
            log.error(f"TG error {r.status_code}: {r.text}")
        else:
            log.info(f"TG send status: 200")
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ================= REVERSE GEOCODE =================
def get_location_name(lat, lon):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "SoilAnalysisBot/1.0"},
            timeout=10
        )
        data = r.json()
        addr = data.get("address", {})

        # Ambil nama lokasi spesifik (kecamatan/kota/kabupaten)
        local = (
            addr.get("village") or
            addr.get("town") or
            addr.get("city") or
            addr.get("municipality") or
            addr.get("county") or
            addr.get("state_district") or
            addr.get("state") or
            "Tidak diketahui"
        )
        region = (
            addr.get("state") or
            addr.get("province") or
            ""
        )
        country = addr.get("country", "Tidak diketahui")
        country_code = addr.get("country_code", "").upper()

        return local, region, country, country_code
    except Exception as e:
        log.error(f"Geocode error: {e}")
        return "Tidak diketahui", "", "Tidak diketahui", ""

# ================= FLAG EMOJI =================
def flag(country_code):
    if not country_code or len(country_code) != 2:
        return ""
    return chr(0x1F1E6 + ord(country_code[0]) - ord('A')) + \
           chr(0x1F1E6 + ord(country_code[1]) - ord('A'))

# ================= SOIL =================
def get_soil_profile(lat, lon):

    point = ee.Geometry.Point([lon, lat])

    depth_index = {
        "0-5cm":    0,
        "5-15cm":   1,
        "15-30cm":  2,
        "30-60cm":  3,
        "60-100cm": 4,
    }

    datasets = {
        "clay": "projects/soilgrids-isric/clay_mean",
        "sand": "projects/soilgrids-isric/sand_mean",
        "silt": "projects/soilgrids-isric/silt_mean",
        "bdod": "projects/soilgrids-isric/bdod_mean",
        "soc":  "projects/soilgrids-isric/soc_mean"
    }

    profile = {}

    for d, idx in depth_index.items():
        profile[d] = {}
        for prop, ds in datasets.items():
            try:
                img = ee.Image(ds).select(idx)
                result = img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=point,
                    scale=250,
                    bestEffort=True
                )
                keys = result.keys().getInfo()
                val = ee.Number(result.get(keys[0])).getInfo() if keys else None
            except Exception as e:
                log.error(f"GEE error [{prop}][{d}]: {e}")
                val = None

            if val is not None:
                if prop in ["clay", "sand", "silt"]:
                    val = val / 10
                elif prop in ["bdod", "soc"]:
                    val = val / 100

            profile[d][prop] = val

    log.info(f"Soil 30-60cm: {profile.get('30-60cm')}")
    return profile

# ================= AGGREGATE =================
def aggregate(p):

    def avg(keys, f):
        vals = [p[k][f] for k in keys if p[k][f] is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "0-30cm": {
            "clay": avg(["0-5cm", "5-15cm", "15-30cm"], "clay"),
            "sand": avg(["0-5cm", "5-15cm", "15-30cm"], "sand"),
            "silt": avg(["0-5cm", "5-15cm", "15-30cm"], "silt"),
            "bdod": avg(["0-5cm", "5-15cm", "15-30cm"], "bdod"),
            "soc":  avg(["0-5cm", "5-15cm", "15-30cm"], "soc")
        },
        "30-60cm":  p["30-60cm"],
        "60-100cm": p["60-100cm"]
    }

# ================= TERRAIN =================
def get_slope(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    try:
        slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
        val = slope.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=30
        ).get("slope")
        if val is None:
            return 0.0
        return ee.Number(val).getInfo()
    except Exception as e:
        log.error(f"GEE slope error: {e}")
        return 0.0

# ================= RAIN =================
def get_rain(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    try:
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate("2015-01-01", "2024-01-01") \
            .sum()
        val = rain.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=5000
        ).get("precipitation")
        if val is None:
            return None
        return ee.Number(val).getInfo() / 9
    except Exception as e:
        log.error(f"GEE rain error: {e}")
        return None

# ================= MODEL =================

def classify(c, s, si):
    if c is None or s is None or si is None:
        return "N/A"
    if c >= s and c >= si:
        return "Lempung"
    if si >= c and si >= s:
        return "Lanau"
    return "Pasir"

def soil_emoji(soil_type):
    return {"Lempung": "🟫", "Lanau": "🟤", "Pasir": "🟡"}.get(soil_type, "⬜")

def peat(soc, bdod):
    return soc is not None and soc > 20 and bdod is not None and bdod < 1.2

def estimate_cbr(c, s, si, bdod, soc, rain):
    if c is None or s is None or si is None:
        return None
    if soc is not None and soc > 20:
        return 1.5
    if c > 45:
        v = 3
    elif c > 35:
        v = 4
    elif c > 25:
        v = 6
    elif s > 60:
        v = 15
    else:
        v = 8
    if bdod:
        if bdod > 1.35:
            v *= 1.3
        elif bdod < 1.1:
            v *= 0.7
    if rain is not None and rain > 2500:
        v *= 0.85
    return round(v, 1)

def cbr_label(cbr):
    if cbr is None: return ""
    if cbr < 3:  return "🔴 Sangat Lemah"
    if cbr < 6:  return "🟠 Lemah"
    if cbr < 10: return "🟡 Sedang"
    if cbr < 20: return "🟢 Baik"
    return "🔵 Sangat Baik"

def estimate_settlement(cbr, clay, soc):
    if soc is not None and soc > 20:
        return "Sangat Besar (di atas 10 cm)"
    if cbr is None:
        return "N/A"
    if cbr < 3:
        return "Besar (5-10 cm)"
    if cbr < 6:
        return "Sedang (2-5 cm)"
    if clay is not None and clay > 40:
        return "Sedang (2-5 cm)"
    return "Kecil (di bawah 2 cm)"

def settlement_emoji(s):
    if "Sangat" in s: return "🔴"
    if "Besar" in s:  return "🟠"
    if "Sedang" in s: return "🟡"
    if "Kecil" in s:  return "🟢"
    return "⬜"

def hard_layer(bd):
    if bd is None:
        return "N/A"
    if bd >= 1.45: return "+-0.8 m"
    if bd >= 1.38: return "+-1.0 m"
    if bd >= 1.32: return "+-1.3 m"
    if bd >= 1.28: return "+-1.6 m"
    return "lebih dari 2 m"

def slope_label(s):
    if s < 2:  return "Datar"
    if s < 8:  return "Landai"
    if s < 15: return "Miring"
    if s < 30: return "Curam"
    return "Sangat Curam"

def rain_label(r):
    if r is None: return ""
    if r < 500:  return "Sangat Kering"
    if r < 1500: return "Kering"
    if r < 2500: return "Normal"
    if r < 4000: return "Basah"
    return "Sangat Basah"

# ================= ANALYZE =================

def analyze(lat, lon, chat_id):

    log.info(f"Analyze start: {lat}, {lon}")
    tg("⏳ Sedang menganalisis tanah, mohon tunggu...", chat_id)

    local, region, country, cc = get_location_name(lat, lon)
    flag_em = flag(cc)

    raw = get_soil_profile(lat, lon)
    p = aggregate(raw)

    rain = get_rain(lat, lon)
    slope = get_slope(lat, lon)

    clay = p["30-60cm"]["clay"]
    sand = p["30-60cm"]["sand"]
    silt = p["30-60cm"]["silt"]
    soc  = p["30-60cm"]["soc"]
    bd   = p["30-60cm"]["bdod"]

    log.info(f"clay={clay} sand={sand} silt={silt} soc={soc} bd={bd} rain={rain} slope={slope}")

    soil     = classify(clay, sand, silt)
    s_emoji  = soil_emoji(soil)
    is_peat  = peat(raw["0-5cm"]["soc"], raw["0-5cm"]["bdod"])
    cbr      = estimate_cbr(clay, sand, silt, bd, soc, rain)
    cbr_lbl  = cbr_label(cbr)
    settle   = estimate_settlement(cbr, clay, soc)
    set_em   = settlement_emoji(settle)
    hard     = hard_layer(bd)

    cbr_txt   = f"{cbr}%  {cbr_lbl}" if cbr is not None else "N/A"
    rain_txt  = f"{rain:.0f} mm/thn  ({rain_label(rain)})" if rain is not None else "N/A"
    slope_txt = f"{slope:.1f} derajat  ({slope_label(slope)})" if slope is not None else "N/A"

    loc_line = local
    if region and region != local:
        loc_line += f", {region}"
    loc_line += f", {country} {flag_em}"

    peat_line = "Ya  (Indikasi Gambut)" if is_peat else "Tidak terindikasi"
    peat_em   = "🌿" if is_peat else "✅"

    msg = (
        f"╔══════════════════════╗\n"
        f"     🌍 SOIL ANALYSIS REPORT\n"
        f"╚══════════════════════╝\n\n"
        f"📍 <b>LOKASI</b>\n"
        f"    {loc_line}\n"
        f"    🗺 {lat}, {lon}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>RINGKASAN HASIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{s_emoji} <b>Jenis Tanah</b>\n"
        f"    {soil}\n\n"
        f"🚧 <b>Estimasi CBR</b>\n"
        f"    {cbr_txt}\n\n"
        f"🌧 <b>Curah Hujan</b>\n"
        f"    {rain_txt}\n\n"
        f"⛰ <b>Kemiringan Lereng</b>\n"
        f"    {slope_txt}\n\n"
        f"🧱 <b>Perkiraan Tanah Keras</b>\n"
        f"    {hard}\n\n"
        f"{set_em} <b>Potensi Penurunan</b>\n"
        f"    {settle}\n\n"
        f"{peat_em} <b>Gambut</b>\n"
        f"    {peat_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪨 <b>PROFIL TANAH DETAIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    depth_labels = {
        "0-30cm":   "🟫 Lapisan Atas   (0-30 cm)",
        "30-60cm":  "🟤 Lapisan Tengah (30-60 cm)",
        "60-100cm": "⬛ Lapisan Bawah  (60-100 cm)",
    }

    for d, data in p.items():
        clay_txt = f"{data['clay']:.1f}%" if data["clay"] is not None else "N/A"
        sand_txt = f"{data['sand']:.1f}%" if data["sand"] is not None else "N/A"
        silt_txt = f"{data['silt']:.1f}%" if data["silt"] is not None else "N/A"
        soil_d   = classify(data["clay"], data["sand"], data["silt"])
        s_em     = soil_emoji(soil_d)
        msg += (
            f"\n{depth_labels.get(d, d)}\n"
            f"  {s_em} Jenis  : {soil_d}\n"
            f"  Clay   : {clay_txt}\n"
            f"  Sand   : {sand_txt}\n"
            f"  Silt   : {silt_txt}\n"
        )

    msg += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>POTENSI MASALAH JALAN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🔸 Retak reflektif akibat kembang susut\n"
        f"  🔸 Rutting / ambles (daya dukung rendah)\n"
        f"  🔸 Genangan air saat curah hujan tinggi\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>Preliminary assessment berbasis SoilGrids "
        f"via Google Earth Engine. Wajib verifikasi lapangan.</i>"
    )

    tg(msg, chat_id)
    log.info("Analyze done")

# ================= LOOP =================

def loop():
    global last_update_id
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}",
                timeout=20
            ).json()
            for u in r.get("result", []):
                last_update_id = u["update_id"]
                msg = u.get("message")
                if not msg or "text" not in msg:
                    continue
                text = msg["text"]
                chat = str(msg["chat"]["id"])
                log.info(f"Received: '{text}' from {chat}")
                coord = re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)", text)
                if coord:
                    analyze(float(coord.group(1)), float(coord.group(2)), chat)
        except Exception as e:
            log.error(f"Loop error: {e}")
        time.sleep(2)

# ================= MAIN =================

def main():
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook", timeout=10)
        log.info("Webhook deleted")
    except Exception as e:
        log.error(f"deleteWebhook error: {e}")
    log.info("Bot running")
    tg("🤖 Soil AI siap digunakan!", ADMIN_ID)
    loop()

main()
