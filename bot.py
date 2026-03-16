import ee
import os
import json
import requests
import logging
import time
import re

# =========================
# TELEGRAM CONFIG
# =========================

TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID = "1145085024"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)
last_update_id = 0

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=20
    )

# =========================
# INIT GEE (Railway ENV: GEE_KEY)
# =========================

service_account = json.loads(os.environ["GEE_KEY"])
credentials = ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)
ee.Initialize(credentials)

# =========================
# DATASET & DEPTH ORDER
# =========================

DEPTHS = ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"]

DATASETS = {
    "clay":"projects/soilgrids-isric/clay_mean",
    "sand":"projects/soilgrids-isric/sand_mean",
    "silt":"projects/soilgrids-isric/silt_mean",
    "bdod":"projects/soilgrids-isric/bdod_mean",
    "soc":"projects/soilgrids-isric/soc_mean",
    "cec":"projects/soilgrids-isric/cec_mean"
}

# =========================
# GEE QUERY (OPTIMAL: 1 reduceRegion)
# =========================

def get_soil_all(lat, lon):
    point = ee.Geometry.Point([lon, lat])

    # gabungkan semua band dari semua dataset
    img = None
    band_map = []  # (prop, depth, band_name)

    for prop, ds in DATASETS.items():
        base = ee.Image(ds)
        for d in DEPTHS:
            band = f"{prop}_{d}_mean"
            sel = base.select(band)
            img = sel if img is None else img.addBands(sel)
            band_map.append((prop, d, band))

    vals = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=250,
        bestEffort=True
    ).getInfo() or {}

    all_depths = {d:{} for d in DEPTHS}

    for prop, d, band in band_map:
        v = vals.get(band)
        if v is None:
            continue

        # konversi unit SoilGrids
        if prop in ["clay","sand","silt"]:
            v = float(v) / 10.0  # g/kg -> %
        else:
            v = float(v)

        all_depths[d][prop] = v

    # hitung silt jika hilang
    for d in DEPTHS:
        clay = all_depths[d].get("clay")
        sand = all_depths[d].get("sand")
        silt = all_depths[d].get("silt")
        if clay is not None and sand is not None and silt is None:
            all_depths[d]["silt"] = max(0.0, 100.0 - clay - sand)

    return all_depths

# =========================
# UTIL
# =========================

def bar(pct, length=10):
    filled = int(round(min(max(pct,0),100)/100*length))
    return "█"*filled + "░"*(length-filled)

def significant_change(prev, cur, thr=2.0):
    if prev is None:
        return True
    return (
        abs(cur.get("clay",0)-prev.get("clay",0))>=thr or
        abs(cur.get("sand",0)-prev.get("sand",0))>=thr or
        abs(cur.get("silt",0)-prev.get("silt",0))>=thr
    )

# =========================
# SOIL CLASSIFICATION
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
# ENGINEERING MODEL
# =========================

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
    if clay > 50: return "1–3% (Sangat rendah)"
    elif clay > 35: return "3–5% (Rendah)"
    elif clay > 20: return "5–8% (Sedang)"
    elif sand and sand > 60: return "10–20% (Baik)"
    else: return "6–10% (Cukup)"

def calc_risks(clay, sand, silt, bdod, soc, cec):
    risks = []
    peat = is_peat(soc, bdod)

    if peat:
        risks += [
            ("Settlement Ekstrem", 95, "🔴", "Gambut kompresibel → amblas"),
            ("Bearing Capacity Gagal", 92, "🔴", "Daya dukung hampir nol"),
            ("Rutting Parah", 90, "🔴", "Beban lalu lintas melesak"),
            ("Kebakaran Bawah Tanah", 60, "🟡", "Gambut kering berongga"),
        ]
    else:
        if clay > 35:
            exp_lvl, _, exp_pct = is_expansive(clay, cec)
            risks += [
                ("Retak Reflektif", min(95, 40+int(clay)), "🔴" if clay>50 else "🟠",
                 f"Clay {clay:.0f}% → kembang-susut"),
                ("Rutting/Ambles", min(90, 35+int(clay)), "🔴" if clay>50 else "🟠",
                 "Subgrade lunak"),
                ("Heave (Terangkat)", exp_pct, "🔴" if exp_pct>60 else "🟡",
                 f"Ekspansif {exp_lvl}"),
                ("Banjir/Genangan", min(85, 30+int(clay)), "🔴" if clay>45 else "🟠",
                 "Infiltrasi buruk"),
            ]
        if silt and silt > 30:
            risks += [
                ("Erosi Tepi Jalan", min(85, 20+int(silt)), "🔴" if silt>50 else "🟡",
                 f"Silt {silt:.0f}%"),
                ("Pumping", min(75, 15+int(silt)), "🟡",
                 "Material keluar dari retakan"),
            ]
        if sand and sand > 60:
            risks += [
                ("Erosi Tinggi", min(80, int(sand)), "🟠",
                 f"Sand {sand:.0f}%"),
                ("Likuifaksi", 45, "🟡",
                 "Pasir lepas saat getaran"),
            ]
        if not risks:
            risks.append(("Risiko Umum", 25, "🟢", "Kondisi relatif baik"))

    risks.sort(key=lambda x: x[1], reverse=True)
    return risks

def recommend(clay, sand, silt, bdod, soc, cec):
    peat = is_peat(soc, bdod)
    if peat:
        return [
            "❌ TIDAK LAYAK tanpa penanganan khusus",
            "Full replacement / cerucuk + geotextile",
            "Preloading + PVD",
            "Drainase dalam wajib",
            "Boring + monitoring settlement"
        ]
    elif clay > 35:
        exp, _, _ = is_expansive(clay, cec)
        return [
            f"Stabilisasi kapur 5–8% / semen 3–5%",
            "Geotextile di interface subgrade–subbase",
            "Agregat kelas A ≥ 25–30 cm",
            f"Drainase prioritas (ekspansif {exp})",
            "CBR lapangan + Atterberg limits"
        ]
    elif clay > 20:
        return [
            "Stabilisasi kapur 3–5%",
            "Agregat kelas B ≥ 20 cm",
            "Geotextile disarankan",
            "Saluran tepi + subdrain",
            "DCP test + CBR"
        ]
    elif sand and sand > 60:
        return [
            "Semen 3–4% untuk ikat pasir",
            "Geotextile cegah erosi",
            "Agregat kelas A ≥ 15 cm",
            "Kontrol erosi tepi",
            "Uji kepadatan (sandcone)"
        ]
    else:
        return [
            "Subgrade relatif baik",
            "Agregat kelas B ≥ 15 cm",
            "Drainase standar",
            "Verifikasi DCP"
        ]

# =========================
# ANALYZE
# =========================

def analyze_soil(lat, lon, chat_id):
    tg(f"⏳ Menganalisis tanah...\n📍 {lat}, {lon}", chat_id)

    try:
        all_depths = get_soil_all(lat, lon)
    except Exception as e:
        log.error(f"GEE error: {e}")
        tg(f"❌ Gagal ambil data: {str(e)[:120]}", chat_id)
        return

    msg = (
        f"📍 <b>LAPORAN TANAH — ROAD ENGINEERING</b>\n"
        f"Koordinat: {lat}, {lon}\n"
        f"🔬 Sumber: GEE / SoilGrids\n\n"
    )

    prev = None
    for d in DEPTHS:
        cur = all_depths.get(d, {})
        if not cur:
            continue
        if not significant_change(prev, cur):
            continue

        clay = cur.get("clay",0)
        sand = cur.get("sand",0)
        silt = cur.get("silt",0)
        bdod = cur.get("bdod")
        soc  = cur.get("soc")
        cec  = cur.get("cec")

        soil_type = classify_soil(clay, sand, silt)
        cat, cat_emoji = soil_category(clay, bdod, soc)
        exp, exp_emoji, _ = is_expansive(clay, cec)
        peat_flag = "YA 🔴" if is_peat(soc, bdod) else "Tidak ✅"

        msg += (
            f"━━ {d} ━━\n"
            f"Jenis: {soil_type} | {cat} {cat_emoji}\n"
            f"Clay: {clay:.1f}% {bar(clay)}\n"
            f"Sand: {sand:.1f}% {bar(sand)}\n"
            f"Silt: {silt:.1f}% {bar(silt)}\n"
        )
        if bdod: msg += f"Bulk Density: {bdod:.2f}\n"
        if cec:  msg += f"CEC: {cec:.1f}\n"
        msg += f"Ekspansif: {exp} {exp_emoji} | Peat: {peat_flag}\n\n"

        prev = cur

    md = all_depths.get("30-60cm", {})
    clay = md.get("clay",0)
    sand = md.get("sand",0)
    silt = md.get("silt",0)
    bdod = md.get("bdod")
    soc  = md.get("soc")
    cec  = md.get("cec")

    risks = calc_risks(clay, sand, silt, bdod, soc, cec)

    msg += "⚠️ <b>RISIKO JALAN</b>\n"
    for name,pct,emoji,desc in risks:
        msg += f"{emoji} {name}: <b>{pct}%</b>\n↳ {desc}\n"

    msg += f"\n📊 <b>ESTIMASI CBR:</b> {estimate_cbr(clay, sand, bdod)}\n\n"

    recs = recommend(clay, sand, silt, bdod, soc, cec)
    msg += "💡 <b>REKOMENDASI</b>\n"
    for r in recs:
        msg += f"• {r}\n"

    tg(msg, chat_id)

# =========================
# TELEGRAM LOOP
# =========================

def check_messages():
    global last_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"
            r = requests.get(url, timeout=35).json()

            for update in r.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()

                coord = re.search(r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)", text)

                if coord:
                    lat = float(coord.group(1))
                    lon = float(coord.group(2))
                    analyze_soil(lat, lon, chat_id)
                else:
                    tg("📍 Kirim koordinat:\n<code>-7.6048,111.9102</code>", chat_id)

        except Exception as e:
            log.error(f"Loop error: {e}")

        time.sleep(2)

# =========================
# MAIN
# =========================

def main():
    log.info("Soil Bot start")
    tg("✅ Soil Analyzer aktif!\nKirim koordinat untuk analisis.")
    check_messages()

main()
