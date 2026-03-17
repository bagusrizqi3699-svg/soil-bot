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
            log.info("TG send status: 200")
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
        local = (
            addr.get("village") or addr.get("town") or
            addr.get("city") or addr.get("municipality") or
            addr.get("county") or addr.get("state_district") or
            addr.get("state") or "Tidak diketahui"
        )
        region  = addr.get("state") or addr.get("province") or ""
        country = addr.get("country", "Tidak diketahui")
        cc      = addr.get("country_code", "").upper()
        return local, region, country, cc
    except Exception as e:
        log.error(f"Geocode error: {e}")
        return "Tidak diketahui", "", "Tidak diketahui", ""

def flag(cc):
    if not cc or len(cc) != 2:
        return ""
    return chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))

# ================= SOIL =================
def get_soil_profile(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    depth_index = {"0-5cm":0,"5-15cm":1,"15-30cm":2,"30-60cm":3,"60-100cm":4}
    datasets = {
        "clay":"projects/soilgrids-isric/clay_mean",
        "sand":"projects/soilgrids-isric/sand_mean",
        "silt":"projects/soilgrids-isric/silt_mean",
        "bdod":"projects/soilgrids-isric/bdod_mean",
        "soc": "projects/soilgrids-isric/soc_mean"
    }
    profile = {}
    for d, idx in depth_index.items():
        profile[d] = {}
        for prop, ds in datasets.items():
            try:
                img = ee.Image(ds).select(idx)
                result = img.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=point, scale=250, bestEffort=True
                )
                keys = result.keys().getInfo()
                val  = ee.Number(result.get(keys[0])).getInfo() if keys else None
            except Exception as e:
                log.error(f"GEE error [{prop}][{d}]: {e}")
                val = None
            if val is not None:
                if prop in ["clay","sand","silt"]: val = val / 10
                elif prop in ["bdod","soc"]:       val = val / 100
            profile[d][prop] = val
    log.info(f"Soil 30-60cm: {profile.get('30-60cm')}")
    return profile

def aggregate(p):
    def avg(keys, f):
        vals = [p[k][f] for k in keys if p[k][f] is not None]
        return sum(vals)/len(vals) if vals else None
    return {
        "0-30cm": {
            "clay": avg(["0-5cm","5-15cm","15-30cm"],"clay"),
            "sand": avg(["0-5cm","5-15cm","15-30cm"],"sand"),
            "silt": avg(["0-5cm","5-15cm","15-30cm"],"silt"),
            "bdod": avg(["0-5cm","5-15cm","15-30cm"],"bdod"),
            "soc":  avg(["0-5cm","5-15cm","15-30cm"],"soc")
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
            reducer=ee.Reducer.mean(), geometry=point, scale=30
        ).get("slope")
        return ee.Number(val).getInfo() if val is not None else 0.0
    except Exception as e:
        log.error(f"GEE slope error: {e}")
        return 0.0

def get_rain(lat, lon):
    point = ee.Geometry.Point([lon, lat])
    try:
        rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
            .filterDate("2015-01-01","2024-01-01").sum()
        val = rain.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=5000
        ).get("precipitation")
        return ee.Number(val).getInfo() / 9 if val is not None else None
    except Exception as e:
        log.error(f"GEE rain error: {e}")
        return None

# ================= CLASSIFICATION =================

def classify_detail(c, s, si):
    if c is None or s is None or si is None:
        return "N/A", "Data tidak tersedia"
    total = c + s + si
    if total == 0:
        return "N/A", "Data tidak valid"
    if c >= 40:
        if s > 20:  return "Lempung Berpasir",       "Dominan lempung dengan campuran pasir cukup signifikan"
        if si > 20: return "Lempung Berlanau",        "Dominan lempung dengan campuran lanau"
        return          "Lempung Murni",               "Sangat dominan lempung, plastisitas tinggi"
    if s >= 60:
        if c > 10:  return "Pasir Berlempung",        "Dominan pasir dengan campuran lempung"
        if si > 15: return "Pasir Berlanau",           "Dominan pasir dengan campuran lanau"
        return          "Pasir Murni",                 "Sangat dominan pasir, drainase sangat tinggi"
    if si >= 40:
        if c > 20:  return "Lanau Berlempung",        "Dominan lanau dengan campuran lempung"
        if s > 20:  return "Lanau Berpasir",           "Dominan lanau dengan campuran pasir"
        return          "Lanau Murni",                 "Sangat dominan lanau, rentan erosi"
    if c > 25 and s > 25 and si > 25:
        return          "Lempung Campuran (Loam)",     "Campuran seimbang — ideal untuk konstruksi"
    if c > s and c > si: return "Lempung Campuran",   "Lempung dominan dengan campuran pasir dan lanau"
    if s > si:           return "Pasir Campuran",     "Pasir dominan dengan campuran lempung dan lanau"
    return                      "Lanau Campuran",     "Lanau dominan dengan campuran lempung dan pasir"

def soil_emoji(name):
    for k, v in {"Lempung":"🟫","Lanau":"🟤","Pasir":"🟡","Loam":"🟢"}.items():
        if k in name: return v
    return "⬜"

def bar(val, max_val=100, length=10):
    if val is None: return "░" * length
    filled = max(0, min(length, round((val / max_val) * length)))
    return "█" * filled + "░" * (length - filled)

def peat(soc, bdod):
    return soc is not None and soc > 20 and bdod is not None and bdod < 1.2

def estimate_cbr(c, s, si, bdod, soc, rain):
    if c is None or s is None or si is None: return None
    if soc is not None and soc > 20: return 1.5
    if c > 45:   v = 3
    elif c > 35: v = 4
    elif c > 25: v = 6
    elif s > 60: v = 15
    else:        v = 8
    if bdod:
        if bdod > 1.35:  v *= 1.3
        elif bdod < 1.1: v *= 0.7
    if rain is not None and rain > 2500: v *= 0.85
    return round(v, 1)

def cbr_label(cbr):
    if cbr is None:  return "N/A", "⬜"
    if cbr < 3:      return "Sangat Lemah", "🔴"
    if cbr < 6:      return "Lemah", "🟠"
    if cbr < 10:     return "Sedang", "🟡"
    if cbr < 20:     return "Baik", "🟢"
    return                  "Sangat Baik", "🔵"

def estimate_settlement(cbr, clay, soc):
    if soc is not None and soc > 20: return "Sangat Besar (di atas 10 cm)", "🔴"
    if cbr is None:                  return "N/A", "⬜"
    if cbr < 3:                      return "Besar (5-10 cm)", "🟠"
    if cbr < 6:                      return "Sedang (2-5 cm)", "🟡"
    if clay is not None and clay > 40: return "Sedang (2-5 cm)", "🟡"
    return                               "Kecil (di bawah 2 cm)", "🟢"

def hard_layer(bd):
    if bd is None:  return "N/A"
    if bd >= 1.45:  return "+-0.8 m"
    if bd >= 1.38:  return "+-1.0 m"
    if bd >= 1.32:  return "+-1.3 m"
    if bd >= 1.28:  return "+-1.6 m"
    return                 "lebih dari 2 m"

def slope_label(s):
    if s < 2:  return "Datar", "🟢"
    if s < 8:  return "Landai", "🟡"
    if s < 15: return "Miring", "🟠"
    if s < 30: return "Curam", "🔴"
    return           "Sangat Curam", "🔴"

def rain_label(r):
    if r is None: return "N/A", "⬜"
    if r < 500:   return "Sangat Kering", "🔴"
    if r < 1500:  return "Kering", "🟠"
    if r < 2500:  return "Normal", "🟢"
    if r < 4000:  return "Basah", "🔵"
    return              "Sangat Basah", "🌊"

def landslide_risk(slope, clay, silt, rain, bdod):
    """Estimasi potensi longsor berdasarkan lereng, tanah, dan hujan"""
    if slope is None:
        return "N/A", "⬜"
    score = 0
    if slope >= 30:   score += 4
    elif slope >= 15: score += 3
    elif slope >= 8:  score += 1
    if rain is not None:
        if rain > 3000:   score += 3
        elif rain > 2000: score += 2
        elif rain > 1500: score += 1
    if clay is not None and clay > 35: score += 2
    if silt is not None and silt > 40: score += 2
    if bdod is not None and bdod < 1.1: score += 1
    if score >= 7:   return "Sangat Tinggi", "🔴"
    if score >= 5:   return "Tinggi", "🟠"
    if score >= 3:   return "Sedang", "🟡"
    if score >= 1:   return "Rendah", "🟢"
    return                  "Sangat Rendah", "🔵"

def data_confidence(p, rain, slope):
    """
    Hitung tingkat kepercayaan data berdasarkan kelengkapan nilai GEE.
    Semakin banyak None, semakin rendah kepercayaan.
    """
    total  = 0
    filled = 0
    for d, data in p.items():
        for v in data.values():
            total += 1
            if v is not None: filled += 1
    if rain  is not None: filled += 1
    total += 1
    if slope is not None and slope > 0: filled += 1
    total += 1

    ratio = filled / total if total > 0 else 0

    if ratio >= 0.90: return "Tinggi (di atas 90% data tersedia)", "🟢", ratio
    if ratio >= 0.70: return "Sedang (70-90% data tersedia)", "🟡", ratio
    if ratio >= 0.40: return "Rendah (40-70% data tersedia)", "🟠", ratio
    return                   "Sangat Rendah (kurang dari 40% data tersedia)", "🔴", ratio

def fmt(val, dec=2, unit="", fallback="0"):
    if val is None: return fallback + unit
    return f"{val:.{dec}f}{unit}"

# ================= DYNAMIC ROAD ISSUES =================
def road_issues(cbr, clay, sand, silt, soc, bdod, rain, slope, is_peat_flag):
    issues = []

    if is_peat_flag:
        issues.append(("🔴", "<b>KRITIS:</b> Tanah gambut — penurunan masif tak terkendali"))
        issues.append(("🔴", "Tidak direkomendasikan tanpa soil replacement atau pondasi dalam"))
        return issues

    if cbr is not None:
        if cbr < 3:
            issues.append(("🔴", f"<b>Daya dukung sangat rendah</b> (CBR <b>{cbr}%</b>, min. 6%) — lapis pondasi tebal wajib"))
        elif cbr < 6:
            issues.append(("🟠", f"<b>Daya dukung di bawah minimum</b> (CBR <b>{cbr}%</b>, min. 6%) — perlu perkuatan subgrade"))
        elif cbr < 10:
            issues.append(("🟡", f"Daya dukung <b>memenuhi standar jalan lokal</b> (CBR <b>{cbr}%</b>, min. 6%) — pantau beban berat"))
        else:
            issues.append(("🟢", f"Daya dukung <b>baik</b> (CBR <b>{cbr}%</b>, min. 6%) — memenuhi standar konstruksi jalan"))

    if clay is not None:
        if clay > 40:
            issues.append(("🔴", f"<b>Clay sangat tinggi</b> ({clay:.1f}%) — risiko retak reflektif dan kembang susut parah"))
        elif clay > 25:
            issues.append(("🟠", f"Clay cukup tinggi ({clay:.1f}%) — waspadai <b>retak permukaan</b> saat musim kering"))
        elif clay < 10 and sand is not None and sand > 60:
            issues.append(("🟡", f"Pasir dominan ({sand:.1f}%) — risiko <b>erosi dan gerusan</b> di tepi jalan"))

    if rain is not None:
        if rain > 3000:
            if clay is not None and clay > 30:
                issues.append(("🔴", f"<b>Curah hujan sangat tinggi</b> ({rain:.0f} mm/thn) + clay tinggi — drainase kritis"))
            else:
                issues.append(("🟠", f"<b>Curah hujan tinggi</b> ({rain:.0f} mm/thn) — sistem drainase jalan harus memadai"))
        elif rain > 2000:
            issues.append(("🟡", f"Curah hujan cukup tinggi ({rain:.0f} mm/thn) — perhatikan <b>kemiringan melintang</b> jalan"))
        elif rain < 300:
            issues.append(("🟡", f"Curah hujan sangat rendah ({rain:.0f} mm/thn) — waspadai <b>deformasi termal</b> dan retak susut"))

    if slope is not None:
        if slope > 25:
            issues.append(("🔴", f"<b>Lereng sangat curam</b> ({slope:.1f} deg) — risiko longsor tinggi, retaining wall wajib"))
        elif slope > 15:
            issues.append(("🟠", f"Lereng curam ({slope:.1f} deg) — perlu <b>retaining wall</b> dan drainase lereng"))
        elif slope > 8:
            issues.append(("🟡", f"Lereng miring ({slope:.1f} deg) — perlu <b>pengendalian erosi</b> permukaan"))

    if bdod is not None:
        if bdod < 1.0:
            issues.append(("🔴", f"<b>Kepadatan sangat rendah</b> (kepadatan {bdod:.2f} g/cm3) — tanah gembur, berisiko ambles"))
        elif bdod < 1.2:
            issues.append(("🟠", f"Kepadatan rendah (kepadatan {bdod:.2f} g/cm3) — perlu <b>pemadatan</b> sebelum konstruksi"))

    if soc is not None and 5 < soc <= 20:
        issues.append(("🟠", f"Bahan organik cukup tinggi ( {soc:.1f}%) — <b>tanah tidak stabil</b>, rentan turun perlahan jangka panjang"))

    if not issues:
        issues.append(("🟢", "<b>Tidak ada masalah signifikan</b> teridentifikasi berdasarkan data tersedia"))

    return issues

# ================= ANALYZE =================

def analyze(lat, lon, chat_id):
    log.info(f"Analyze start: {lat}, {lon}")
    tg("⏳ Menganalisis tanah... mohon tunggu sebentar.", chat_id)

    local, region, country, cc = get_location_name(lat, lon)
    flag_em = flag(cc)

    raw   = get_soil_profile(lat, lon)
    p     = aggregate(raw)
    rain  = get_rain(lat, lon)
    slope = get_slope(lat, lon)

    clay = p["30-60cm"]["clay"]
    sand = p["30-60cm"]["sand"]
    silt = p["30-60cm"]["silt"]
    soc  = p["30-60cm"]["soc"]
    bd   = p["30-60cm"]["bdod"]

    log.info(f"clay={clay} sand={sand} silt={silt} soc={soc} bd={bd} rain={rain} slope={slope}")

    soil_name, soil_desc     = classify_detail(clay, sand, silt)
    s_emoji                  = soil_emoji(soil_name)
    # Cek gambut: pakai nilai tertinggi SOC dari semua lapisan atas (lebih akurat)
    soc_max = max([v for v in [raw[d]["soc"] for d in ["0-5cm","5-15cm","15-30cm"]] if v is not None], default=None)
    bd_min  = min([v for v in [raw[d]["bdod"] for d in ["0-5cm","5-15cm","15-30cm"]] if v is not None], default=None)
    is_peat_flag             = peat(soc_max, bd_min)
    cbr                      = estimate_cbr(clay, sand, silt, bd, soc, rain)
    cbr_lbl, cbr_em          = cbr_label(cbr)
    settle, set_em           = estimate_settlement(cbr, clay, soc)
    hard                     = hard_layer(bd)
    slope_lbl, slope_em      = slope_label(slope)
    rain_lbl, rain_em        = rain_label(rain)
    ls_risk, ls_em           = landslide_risk(slope, clay, silt, rain, bd)
    conf_lbl, conf_em, ratio = data_confidence(p, rain, slope)

    loc_line = local
    if region and region != local:
        loc_line += f", {region}"

    cbr_txt   = f"{cbr_em} <b>{cbr}%</b>  ({cbr_lbl})" if cbr is not None else "N/A"
    rain_txt  = f"{rain_em} <b>{rain:.0f} mm/thn</b>  ({rain_lbl})" if rain is not None else "N/A"
    slope_txt = f"{slope_em} <b>{slope:.1f} deg</b>  ({slope_lbl})"

    issues     = road_issues(cbr, clay, sand, silt, soc, bd, rain, slope, is_peat_flag)
    issues_txt = "\n".join(f"  {em} {desc}" for em, desc in issues)

    msg = (
        f"🌍 <b>AI SOIL ANALYSIS REPORT</b> 🌍\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📍 <b>LOKASI</b>\n"
        f"  {flag_em} <b>{loc_line}</b>\n"
        f"  {country}\n"
        f"  🗺 {lat}, {lon}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔬 <b>JENIS TANAH DOMINAN</b>\n"
        f"  {s_emoji} <b>{soil_name}</b>\n"
        f"  📝 {soil_desc}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>PARAMETER UTAMA</b>\n\n"
        f"  🚧 <b>CBR</b>         : {cbr_txt}\n"
        f"  🌧 <b>Hujan</b>       : {rain_txt}\n"
        f"  ⛰ <b>Lereng</b>      : {slope_txt}\n"
        f"  🧱 <b>Tanah Keras</b> : {hard}\n"
        f"  {set_em} <b>Penurunan</b>  : {settle}\n"
        f"  {ls_em} <b>Longsor</b>    : {ls_risk}\n"
        f"  {'🌿' if is_peat_flag else '✅'} <b>Gambut</b>     : {'⚠️ Terindikasi' if is_peat_flag else 'Tidak terindikasi'}{f' (SOC maks {soc_max:.1f}%)' if soc_max is not None else ''}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪨 <b>PROFIL TANAH DETAIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    depth_labels = {
        "0-30cm":   ("🟫", "Lapisan Atas   (0-30 cm)"),
        "30-60cm":  ("🟤", "Lapisan Tengah (30-60 cm)"),
        "60-100cm": ("⬛", "Lapisan Bawah  (60-100 cm)"),
    }

    for d, data in p.items():
        em, dlabel = depth_labels.get(d, ("🔲", d))
        c     = data["clay"] or 0
        s     = data["sand"] or 0
        si    = data["silt"] or 0
        soc_v = data["soc"]  or 0
        bd_v  = data["bdod"]
        sn, _ = classify_detail(data["clay"], data["sand"], data["silt"])
        msg += (
            f"\n{em} <b>{dlabel}</b>\n"
            f"  Jenis   : <b>{sn}</b>\n"
            f"  🟫 Clay  : <b>{c:.1f}%</b>  {bar(c)}\n"
            f"  🟡 Sand  : <b>{s:.1f}%</b>  {bar(s)}\n"
            f"  🔘 Silt  : <b>{si:.1f}%</b>  {bar(si)}\n"
            f"  🌱 Bhn Organik : <b>{soc_v:.2f}%</b>\n"
            f"  🪨 Kepadatan   : <b>{fmt(bd_v, 2, ' g/cm3', '0.00')}</b>\n"
        )

    msg += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>ANALISIS POTENSI MASALAH JALAN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{issues_txt}\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>TINGKAT KEPERCAYAAN DATA</b>\n"
        f"  {conf_em} <b>{conf_lbl}</b>\n"
        f"  Data tersedia: <b>{ratio*100:.0f}%</b> dari total parameter\n"
        f"  Sumber: SoilGrids ISRIC v2 + CHIRPS + SRTM\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>Preliminary assessment via SoilGrids ISRIC + GEE.\n"
        f"Wajib verifikasi investigasi lapangan.</i>"
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
