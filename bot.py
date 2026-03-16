TELEGRAM_TOKEN = "8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID = "1145085024"

import requests, logging, time, re
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)
last_update_id = 0

def tg(msg, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
        timeout=15
    )

def get_soil_all(lat, lon):
    url = "https://api.openepi.io/soil/property"
    params = [
        ("lon", lon), ("lat", lat),
        ("depths", "0-5cm"), ("depths", "5-15cm"), ("depths", "15-30cm"),
        ("depths", "30-60cm"), ("depths", "60-100cm"), ("depths", "100-200cm"),
        ("properties", "clay"), ("properties", "sand"), ("properties", "silt"),
        ("properties", "bdod"), ("properties", "soc"), ("properties", "cec"),
        ("values", "mean"),
    ]
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    all_depths = {}
    for layer in data.get("properties", {}).get("layers", []):
        name = layer.get("name")
        d_factor = layer.get("unit_measure", {}).get("d_factor", 1)
        for d in layer.get("depths", []):
            label = d.get("label")
            val = d.get("values", {}).get("mean")
            if val is None: continue
            if label not in all_depths: all_depths[label] = {}
            all_depths[label][name] = val / d_factor
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
    if clay > 50: return "1-3% (Sangat rendah)"
    elif clay > 35: return "3-5% (Rendah)"
    elif clay > 20: return "5-8% (Sedang)"
    elif sand and sand > 60: return "10-20% (Baik)"
    else: return "6-10% (Cukup)"

def calc_risks(clay, sand, silt, bdod, soc, cec):
    risks = []
    peat = is_peat(soc, bdod)
    if peat:
        risks += [
            ("Settlement Ekstrem", 95, "🔴", "Gambut kompresibel → jalan amblas masif"),
            ("Bearing Capacity Gagal", 92, "🔴", "Daya dukung hampir nol → perlu cerucuk/replacement"),
            ("Rutting Parah", 90, "🔴", "Beban lalu lintas melesak ke gambut"),
            ("Kebakaran Bawah Tanah", 60, "🟡", "Gambut kering → rongga bawah jalan"),
        ]
    else:
        if clay > 35:
            exp_lvl, _, exp_pct = is_expansive(clay, cec)
            risks += [
                ("Retak Reflektif", min(95, 40+int(clay)), "🔴" if clay>50 else "🟠",
                 f"Clay {clay:.0f}% → aspal retak ikuti pola kembang-susut tanah"),
                ("Rutting/Ambles", min(90, 35+int(clay)), "🔴" if clay>50 else "🟠",
                 f"Subgrade lunak, CBR rendah → jalan amblas saat hujan/beban berat"),
                ("Heave (Terangkat)", exp_pct, "🔴" if exp_pct>60 else "🟡",
                 f"Ekspansif {exp_lvl} → perkerasan terangkat musim hujan"),
                ("Banjir/Genangan", min(85, 30+int(clay)), "🔴" if clay>45 else "🟠",
                 "Clay tinggi → air sulit meresap, genangan di badan jalan"),
            ]
        if silt and silt > 30:
            risks += [
                ("Erosi Tepi Jalan", min(85, 20+int(silt)), "🔴" if silt>50 else "🟡",
                 f"Silt {silt:.0f}% → bahu jalan mudah terkikis aliran air"),
                ("Pumping", min(75, 15+int(silt)), "🟡",
                 "Material keluar dari retakan saat beban dinamis"),
            ]
        if sand and sand > 60:
            risks += [
                ("Erosi Tinggi", min(80, int(sand)), "🟠",
                 f"Sand {sand:.0f}% → material terbawa air, tepi jalan rawan longsor"),
                ("Likuifaksi", 45, "🟡",
                 "Pasir lepas → risiko likuifaksi saat gempa/getaran berat"),
            ]
        if not risks:
            risks.append(("Risiko Umum", 25, "🟢", "Kondisi tanah relatif baik, pantau drainase"))
    risks.sort(key=lambda x: x[1], reverse=True)
    return risks

def recommend(clay, sand, silt, bdod, soc, cec):
    peat = is_peat(soc, bdod)
    if peat:
        return ["❌ TIDAK LAYAK tanpa penanganan khusus",
                "Opsi 1: Full replacement gambut",
                "Opsi 2: Cerucuk/tiang + geotextile woven",
                "Opsi 3: Preloading + PVD (vertical drain)",
                "Drainase: Sistem drainase dalam wajib",
                "Investigasi: Boring + settlement monitoring"]
    elif clay > 35:
        exp, _, _ = is_expansive(clay, cec)
        return [f"Stabilisasi: Kapur 5-8% atau Semen 3-5% (clay {clay:.0f}%)",
                "Geotextile: Wajib di interface subgrade-subbase",
                "Lapis Pondasi: Agregat kelas A min 25-30cm",
                f"Drainase: Prioritas tinggi (ekspansif {exp})",
                "Perkerasan: Aspal tebal min 10cm + lapis antara",
                "Investigasi: CBR lapangan + Atterberg Limits wajib"]
    elif clay > 20:
        return ["Stabilisasi: Kapur 3-5% jika perlu",
                "Lapis Pondasi: Agregat kelas B min 20cm",
                "Geotextile: Disarankan di subgrade",
                "Drainase: Saluran tepi + subdrain",
                "Investigasi: DCP test + CBR lapangan"]
    elif sand and sand > 60:
        return ["Stabilisasi: Semen 3-4% untuk ikat pasir",
                "Geotextile: Wajib cegah erosi & segregasi",
                "Lapis Pondasi: Agregat kelas A min 15cm",
                "Drainase: Perhatikan erosi tepi jalan",
                "Investigasi: Kepadatan lapangan (sandcone)"]
    else:
        return ["Subgrade: Kondisi relatif baik",
                "Lapis Pondasi: Agregat kelas B min 15cm",
                "Drainase: Standar, saluran tepi cukup",
                "Investigasi: DCP test untuk verifikasi"]

def bar(pct, length=10):
    filled = int(round(min(pct,100)/100*length))
    return "█"*filled + "░"*(length-filled)

def analyze_soil(lat, lon, chat_id):
    tg(f"⏳ Menganalisis tanah...\n📍 {lat}, {lon}\nMohon tunggu ~20 detik.", chat_id)
    try:
        all_depths = get_soil_all(lat, lon)
    except Exception as e:
        log.error(f"API error: {e}")
        tg(f"❌ Gagal ambil data: {str(e)[:100]}\nCoba lagi beberapa menit.", chat_id)
        return

    if not all_depths:
        tg("❌ Data kosong dari API.", chat_id)
        return

    depth_order = ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm","100-200cm"]
    depth_meta = {
        "0-5cm":    ("0-5 cm",     "Subgrade Permukaan", 75),
        "5-15cm":   ("5-15 cm",    "Zona Drainase",      74),
        "15-30cm":  ("15-30 cm",   "Subbase Dangkal",    73),
        "30-60cm":  ("30-60 cm",   "Subgrade Utama",     72),
        "60-100cm": ("60-100 cm",  "Lapisan Dalam",      68),
        "100-200cm":("100-200 cm", "Pondasi Dalam",      65),
    }

    msg = (f"📍 <b>LAPORAN TANAH — ROAD ENGINEERING</b>\n"
           f"🌐 Koordinat: {lat}, {lon}\n"
           f"🔬 Sumber: OpenEPI/SoilGrids (ISRIC)\n\n")

    for depth_key in depth_order:
        if depth_key not in all_depths: continue
        d = all_depths[depth_key]
        label, role, acc = depth_meta[depth_key]
        clay = d.get("clay", 0)
        sand = d.get("sand", 0)
        silt = d.get("silt", 0)
        bdod = d.get("bdod")
        soc  = d.get("soc")
        cec  = d.get("cec")
        soil_type = classify_soil(clay, sand, silt)
        cat, cat_emoji = soil_category(clay, bdod, soc)
        exp, exp_emoji, _ = is_expansive(clay, cec)
        peat_flag = "YA 🔴" if is_peat(soc, bdod) else "Tidak ✅"

        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"🔍 <b>{label} — {role}</b> (~{acc}%)\n"
        msg += f"Jenis: {soil_type} | {cat} {cat_emoji}\n"
        msg += f"Clay: {clay:.0f}% {bar(clay)}\n"
        msg += f"Sand: {sand:.0f}% {bar(sand)}\n"
        msg += f"Silt: {silt:.0f}% {bar(silt)}\n"
        if bdod: msg += f"Bulk Density: {bdod:.2f} g/cm³\n"
        if cec:  msg += f"CEC: {cec:.1f} cmolc/kg\n"
        msg += f"Ekspansif: {exp} {exp_emoji} | Peat: {peat_flag}\n\n"

    md = all_depths.get("30-60cm", all_depths[list(all_depths.keys())[0]])
    clay = md.get("clay", 0)
    sand = md.get("sand", 0)
    silt = md.get("silt", 0)
    bdod = md.get("bdod")
    soc  = md.get("soc")
    cec  = md.get("cec")
    cbr  = estimate_cbr(clay, sand, bdod)

    risks = calc_risks(clay, sand, silt, bdod, soc, cec)
    msg += "━━━━━━━━━━━━━━━\n"
    msg += "⚠️ <b>RISIKO JALAN</b> (subgrade utama 30-60cm)\n"
    for name, pct, emoji, desc in risks:
        msg += f"{emoji} {name}: <b>{pct}%</b>\n  ↳ {desc}\n"

    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += f"📊 <b>ESTIMASI CBR:</b> {cbr}\n"

    recs = recommend(clay, sand, silt, bdod, soc, cec)
    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += "💡 <b>REKOMENDASI ROAD ENGINEERING</b>\n"
    for r in recs: msg += f"• {r}\n"

    msg += ("\n━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Estimasi ~65-75% akurasi.\n"
            "Wajib verifikasi soil investigation lapangan.</i>")
    tg(msg, chat_id)

def check_messages():
    global last_update_id
    while True:
        try:
            url = (f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
                   f"?offset={last_update_id+1}&timeout=30")
            r = requests.get(url, timeout=35).json()
            for update in r.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if not text: continue
                coord = re.search(r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)", text)
                if text.lower() in ["/start", "help", "/help"]:
                    tg("🌍 <b>Soil Analyzer — Road Engineering</b>\n\n"
                       "Kirim koordinat:\n<code>-7.6048, 111.9102</code>\n\n"
                       "📊 Output:\n• Jenis tanah 6 kedalaman\n"
                       "• Clay/Sand/Silt% + Bulk Density + CEC\n"
                       "• Deteksi Peat & Ekspansif\n"
                       "• Estimasi CBR\n• Risiko jalan + %\n"
                       "• Rekomendasi road engineering\n\n"
                       "⚠️ Akurasi ~65-75%", chat_id)
                elif coord:
                    lat = float(coord.group(1))
                    lon = float(coord.group(2))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        analyze_soil(lat, lon, chat_id)
                    else:
                        tg("❌ Koordinat tidak valid.", chat_id)
                else:
                    tg("📍 Kirim koordinat:\n<code>-7.6048, 111.9102</code>", chat_id)
        except Exception as e:
            log.error(f"Error: {e}")
        time.sleep(2)

def main():
    log.info("Soil Bot start")
    tg("✅ <b>Soil Analyzer aktif!</b>\n🌍 Road Engineering\nKirim koordinat untuk analisis.")
    check_messages()

main()