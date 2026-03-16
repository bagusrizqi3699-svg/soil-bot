TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID = "1145085024"

import requests, logging, time, re
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)
last_update_id = 0

DEPTHS = [
    ("0-5 cm",    "Subgrade Permukaan", "0-5cm",    75),
    ("5-15 cm",   "Zona Drainase",      "5-15cm",   74),
    ("15-30 cm",  "Subbase Dangkal",    "15-30cm",  73),
    ("30-60 cm",  "Subgrade Utama",     "30-60cm",  72),
    ("60-100 cm", "Lapisan Dalam",      "60-100cm", 68),
    ("100-200 cm","Pondasi Dalam",      "100-200cm",65),
]

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=15
    )

def get_soilgrids(lat, lon, depth_code):
    """Ambil data dari SoilGrids REST API"""
    props = "clay,sand,silt,bdod,soc,cec"
    url = (f"https://rest.isric.org/soilgrids/v2.0/properties/query"
           f"?lon={lon}&lat={lat}&property={props}&depth={depth_code}&value=mean")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    result = {}
    for layer in data.get("properties", {}).get("layers", []):
        name = layer["name"]
        depths = layer.get("depths", [])
        for d in depths:
            if d["label"] == depth_code:
                val = d["values"].get("mean")
                if val is not None:
                    # SoilGrids returns values in specific units, convert:
                    if name == "clay":   result["clay"] = val / 10      # g/kg → %
                    elif name == "sand": result["sand"] = val / 10
                    elif name == "silt": result["silt"] = val / 10
                    elif name == "bdod": result["bdod"] = val / 100     # cg/cm³ → g/cm³
                    elif name == "soc":  result["soc"]  = val / 10      # dg/kg → g/kg
                    elif name == "cec":  result["cec"]  = val / 10      # mmol/kg → cmolc/kg
    return result

def classify_soil(clay, sand, silt):
    """USDA soil texture classification"""
    if clay >= 40 and silt >= 40:             return "Silty Clay"
    elif clay >= 40:                           return "Clay"
    elif clay >= 35 and sand >= 45:           return "Sandy Clay"
    elif clay >= 27 and sand >= 20 and sand < 45: return "Clay Loam"
    elif clay >= 27 and silt >= 20:           return "Silty Clay Loam"
    elif clay >= 20 and sand >= 45:           return "Sandy Clay Loam"
    elif silt >= 80:                           return "Silt"
    elif silt >= 50 and clay < 27:            return "Silt Loam"
    elif sand >= 85:                           return "Sand"
    elif sand >= 70 and clay < 15:            return "Loamy Sand"
    elif clay < 20 and sand < 52 and silt < 80: return "Loam"
    elif clay < 15 and sand >= 52:            return "Sandy Loam"
    else:                                      return "Loam"

def soil_category(clay, bdod, soc):
    """Kategori tanah untuk teknik sipil"""
    if soc and soc > 120:   return ("PEAT/GAMBUT", "🔴")
    elif bdod and bdod < 0.5: return ("PEAT/GAMBUT", "🔴")
    elif clay > 50:           return ("SANGAT LUNAK", "🔴")
    elif clay > 35:           return ("LUNAK", "🟠")
    elif clay > 20:           return ("SEDANG", "🟡")
    elif clay > 10:           return ("AGAK PADAT", "🟢")
    else:                     return ("PADAT", "✅")

def is_expansive(clay, cec):
    """Deteksi tanah ekspansif"""
    score = 0
    if clay and clay > 60:  score += 2
    elif clay and clay > 40: score += 1
    if cec and cec > 15:    score += 2
    elif cec and cec > 10:  score += 1
    if score >= 3:   return ("TINGGI", "🔴", 80)
    elif score >= 2: return ("SEDANG", "🟡", 60)
    else:            return ("RENDAH", "✅", 20)

def is_peat(soc, bdod):
    if (soc and soc > 120) or (bdod and bdod < 0.5):
        return True
    return False

def estimate_cbr(clay, sand, bdod):
    """Estimasi CBR dari komposisi tanah"""
    if bdod and bdod < 0.5:    return "<1% (Peat — tidak layak)"
    if clay and clay > 50:      return "1-3% (Sangat rendah)"
    elif clay and clay > 35:    return "3-5% (Rendah)"
    elif clay and clay > 20:    return "5-8% (Sedang)"
    elif sand and sand > 60:    return "10-20% (Baik)"
    else:                        return "6-10% (Cukup)"

def calc_risks(clay, sand, silt, bdod, soc, cec):
    """Hitung risiko jalan secara dinamis berdasarkan jenis tanah"""
    risks = []
    peat = is_peat(soc, bdod)

    if peat:
        risks.append(("Settlement Ekstrem",  95, "🔴",
            "Gambut sangat kompresibel → jalan amblas masif, tidak stabil"))
        risks.append(("Bearing Capacity Gagal", 92, "🔴",
            "Daya dukung hampir nol → perlu replacement total atau cerucuk"))
        risks.append(("Rutting Parah",        90, "🔴",
            "Beban lalu lintas langsung melesak ke gambut"))
        risks.append(("Kebakaran Bawah Tanah", 60, "🟡",
            "Gambut kering rentan terbakar → rongga bawah jalan"))
    else:
        if clay and clay > 35:
            exp_lvl, _, exp_pct = is_expansive(clay, cec)
            risks.append(("Retak Reflektif", min(95, 40 + clay), "🔴" if clay > 50 else "🟠",
                f"Clay {clay:.0f}% → aspal retak mengikuti pola kembang-susut tanah"))
            risks.append(("Rutting/Ambles",  min(90, 35 + clay), "🔴" if clay > 50 else "🟠",
                f"Subgrade lunak, CBR rendah → jalan mudah amblas saat hujan/beban berat"))
            risks.append(("Heave (Terangkat)", exp_pct, "🔴" if exp_pct > 60 else "🟡",
                f"Tanah ekspansif {exp_lvl} → perkerasan terangkat saat musim hujan"))
            risks.append(("Banjir/Genangan",  min(85, 30 + clay), "🔴" if clay > 45 else "🟠",
                f"Clay tinggi, permeabilitas rendah → air sulit meresap"))

        if silt and silt > 30:
            risks.append(("Erosi Tepi Jalan", min(85, 20 + silt), "🔴" if silt > 50 else "🟡",
                f"Silt {silt:.0f}% → bahu jalan mudah terkikis aliran air"))
            risks.append(("Pumping",          min(75, 15 + silt), "🟡",
                f"Silt tinggi → material keluar dari retakan perkerasan saat beban dinamis"))

        if sand and sand > 60:
            risks.append(("Erosi Tinggi",     min(80, sand), "🟠",
                f"Sand {sand:.0f}% → material mudah terbawa air, tepi jalan rawan longsor"))
            risks.append(("Likuifaksi",       45, "🟡",
                "Pasir lepas → risiko likuifaksi saat gempa atau getaran berat"))

        if clay and clay < 15 and sand and sand > 60:
            risks.append(("Drainase Berlebih", 30, "🟢",
                "Permeabilitas tinggi → air cepat meresap, risiko banjir rendah ✅"))

    risks.sort(key=lambda x: x[1], reverse=True)
    return risks

def recommend(clay, sand, silt, bdod, soc, cec, cbr_str):
    """Rekomendasi road engineering dinamis"""
    peat = is_peat(soc, bdod)
    recs = []

    if peat:
        recs = [
            "❌ TIDAK LAYAK tanpa penanganan khusus",
            "Opsi 1: Full replacement gambut (costly)",
            "Opsi 2: Cerucuk/tiang + geotextile woven",
            "Opsi 3: Preloading + PVD (vertical drain)",
            "Drainase: Sistem drainase dalam wajib",
            "Investigasi: Boring + settlement monitoring",
        ]
    elif clay and clay > 35:
        exp, _, _ = is_expansive(clay, cec)
        recs = [
            f"Stabilisasi: Kapur 5-8% atau Semen 3-5% (clay {clay:.0f}%)",
            "Geotextile: Wajib di interface subgrade-subbase",
            "Lapis Pondasi: Agregat kelas A min 25-30cm",
            f"Drainase: Prioritas tinggi (clay ekspansif {exp})",
            "Perkerasan: Aspal tebal min 10cm + lapis antara",
            "Investigasi: CBR lapangan + Atterberg Limits wajib",
        ]
    elif clay and clay > 20:
        recs = [
            "Stabilisasi: Kapur 3-5% jika perlu",
            "Lapis Pondasi: Agregat kelas B min 20cm",
            "Geotextile: Disarankan di subgrade",
            "Drainase: Saluran tepi + subdrain",
            "Investigasi: DCP test + CBR lapangan",
        ]
    elif sand and sand > 60:
        recs = [
            "Stabilisasi: Semen 3-4% untuk ikat pasir",
            "Geotextile: Wajib cegah erosi & segregasi",
            "Lapis Pondasi: Agregat kelas A min 15cm",
            "Drainase: Perhatikan erosi tepi jalan",
            "Investigasi: Kepadatan lapangan (sandcone)",
        ]
    else:
        recs = [
            "Subgrade: Kondisi relatif baik",
            "Lapis Pondasi: Agregat kelas B min 15cm",
            "Drainase: Standar, saluran tepi cukup",
            "Investigasi: DCP test untuk verifikasi",
        ]

    return recs

def bar(pct, length=10):
    filled = int(round(pct / 100 * length))
    return "█" * filled + "░" * (length - filled)

def analyze_soil(lat, lon, chat_id):
    tg(f"⏳ Menganalisis tanah di koordinat {lat}, {lon}...\nMohon tunggu ~30 detik.", chat_id)

    all_data = {}
    for label, role, depth_code, acc in DEPTHS:
        try:
            d = get_soilgrids(lat, lon, depth_code)
            if d:
                all_data[depth_code] = (label, role, acc, d)
        except Exception as e:
            log.error(f"Error depth {depth_code}: {e}")

    if not all_data:
        tg("❌ Gagal ambil data dari SoilGrids. Coba lagi beberapa menit.", chat_id)
        return

    # Build report
    msg = (f"📍 <b>LAPORAN TANAH — ROAD ENGINEERING</b>\n"
           f"🌐 Koordinat: {lat}, {lon}\n"
           f"🔬 Sumber: SoilGrids (ISRIC)\n\n")

    # Per depth
    for depth_code, (label, role, acc, d) in all_data.items():
        clay  = d.get("clay")
        sand  = d.get("sand")
        silt  = d.get("silt")
        bdod  = d.get("bdod")
        soc   = d.get("soc")
        cec   = d.get("cec")

        if clay is None: continue

        soil_type = classify_soil(clay, sand or 0, silt or 0)
        cat, cat_emoji = soil_category(clay, bdod, soc)
        exp, exp_emoji, _ = is_expansive(clay, cec)
        peat_flag = "YA 🔴" if is_peat(soc, bdod) else "Tidak ✅"

        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"🔍 <b>{label} — {role}</b> (akurasi ~{acc}%)\n"
        msg += f"Jenis: {soil_type} | Kategori: {cat} {cat_emoji}\n"
        if clay is not None:
            msg += f"Clay : {clay:.0f}%  {bar(clay)}\n"
        if sand is not None:
            msg += f"Sand : {sand:.0f}%  {bar(sand)}\n"
        if silt is not None:
            msg += f"Silt : {silt:.0f}%  {bar(silt)}\n"
        if bdod:
            msg += f"Bulk Density: {bdod:.2f} g/cm³\n"
        if cec:
            msg += f"CEC: {cec:.1f} cmolc/kg\n"
        msg += f"Ekspansif : {exp} {exp_emoji} | Peat: {peat_flag}\n\n"

    # Pakai data 30-60cm untuk risiko & rekomendasi (subgrade utama)
    main_data = all_data.get("30-60cm", list(all_data.values())[0])
    _, _, _, md = main_data
    clay  = md.get("clay", 0)
    sand  = md.get("sand", 0)
    silt  = md.get("silt", 0)
    bdod  = md.get("bdod")
    soc   = md.get("soc")
    cec   = md.get("cec")
    cbr   = estimate_cbr(clay, sand, bdod)

    # Risks
    risks = calc_risks(clay, sand, silt, bdod, soc, cec)
    msg += "━━━━━━━━━━━━━━━\n"
    msg += "⚠️ <b>RISIKO JALAN</b> (berdasarkan subgrade utama)\n"
    for name, pct, emoji, desc in risks:
        msg += f"{emoji} {name}: <b>{pct}%</b>\n"
        msg += f"  ↳ {desc}\n"

    # CBR
    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += f"📊 <b>ESTIMASI CBR SUBGRADE</b>\n"
    msg += f"CBR: {cbr}\n"

    # Recommendations
    recs = recommend(clay, sand, silt, bdod, soc, cec, cbr)
    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += "💡 <b>REKOMENDASI ROAD ENGINEERING</b>\n"
    for r in recs:
        msg += f"• {r}\n"

    msg += ("\n━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Data estimasi ~65-75% akurasi.\n"
            "Wajib verifikasi dengan soil investigation\n"
            "lapangan (boring, sondir, CBR, DCP test).</i>")

    tg(msg, chat_id)

def check_messages():
    global last_update_id
    while True:
        try:
            url = (f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
                   f"?offset={last_update_id + 1}&timeout=30")
            r = requests.get(url, timeout=35).json()
            for update in r.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()

                if not text:
                    continue

                # Cek koordinat: -7.6048, 111.9102 atau -7.6048 111.9102
                coord_match = re.search(
                    r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)", text)

                if text.lower() in ["/start", "halo", "hi", "help", "/help"]:
                    tg(
                        "🌍 <b>Soil Analyzer — Road Engineering</b>\n\n"
                        "Kirim koordinat untuk analisis tanah:\n"
                        "Format: <code>-7.6048, 111.9102</code>\n\n"
                        "📊 Data yang dihasilkan:\n"
                        "• Jenis & kategori tanah (6 kedalaman)\n"
                        "• Clay / Sand / Silt %\n"
                        "• Deteksi Peat, Ekspansif\n"
                        "• Estimasi CBR\n"
                        "• Risiko jalan + persentase\n"
                        "• Rekomendasi road engineering\n\n"
                        "⚠️ Akurasi ~65-75%. Bukan pengganti\n"
                        "soil investigation lapangan.",
                        chat_id
                    )
                elif coord_match:
                    lat = float(coord_match.group(1))
                    lon = float(coord_match.group(2))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        analyze_soil(lat, lon, chat_id)
                    else:
                        tg("❌ Koordinat tidak valid. Contoh: -7.6048, 111.9102", chat_id)
                else:
                    tg("📍 Kirim koordinat untuk analisis.\nContoh: <code>-7.6048, 111.9102</code>", chat_id)

        except Exception as e:
            log.error(f"Error: {e}")
        time.sleep(2)

def main():
    log.info("Soil Bot start")
    tg("✅ <b>Soil Analyzer aktif!</b>\n"
       "🌍 Road Engineering Soil Analysis\n"
       "Kirim koordinat untuk mulai analisis.")
    check_messages()

main()
