import ee
import os
import json
import requests
import logging
import time
import re
from soil_fallback_db import lookup_fallback, ZONA

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
        # zoom=10 = kecamatan level di Nominatim Indonesia
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
            headers={"User-Agent": "SoilAnalysisBot/1.0"},
            timeout=10
        )
        data_kec = r.json()
        addr_kec = data_kec.get("address", {})

        # Nama kecamatan dari zoom=10
        kecamatan = (
            addr_kec.get("village") or addr_kec.get("town") or
            addr_kec.get("municipality") or addr_kec.get("suburb") or
            addr_kec.get("city_district") or "Tidak diketahui"
        )

        # zoom=14 = nama desa/kelurahan untuk display
        r2 = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 14},
            headers={"User-Agent": "SoilAnalysisBot/1.0"},
            timeout=10
        )
        data_desa = r2.json()
        addr_desa = data_desa.get("address", {})

        local = (
            addr_desa.get("village") or addr_desa.get("town") or
            addr_desa.get("city") or addr_desa.get("municipality") or
            addr_desa.get("county") or kecamatan
        )

        region     = addr_desa.get("state") or addr_desa.get("province") or ""
        state_dist = addr_desa.get("county") or addr_desa.get("state_district") or ""
        country    = addr_desa.get("country", "Tidak diketahui")
        cc         = addr_desa.get("country_code", "").upper()
        log.info(f"Geocode: local={local} kec={kecamatan} dist={state_dist}")
        return local, kecamatan, region, state_dist, country, cc
    except Exception as e:
        log.error(f"Geocode error: {e}")
        return "Tidak diketahui", "Tidak diketahui", "", "", "Tidak diketahui", ""

def flag(cc):
    if not cc or len(cc) != 2:
        return ""
    return chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))

# ================= SOIL GEE =================
VALID_RANGE = {
    "clay": (0, 100), "sand": (0, 100), "silt": (0, 100),
    "bdod": (0.3, 2.5), "soc": (0, 80),
}

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
                lo, hi = VALID_RANGE[prop]
                if not (lo <= val <= hi):
                    log.warning(f"Out of range [{prop}][{d}]: {val} — discarded")
                    val = None
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

# ================= DATA CONFIDENCE =================
def data_confidence(p, rain, slope):
    total = 0; filled = 0
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
    return "Sangat Rendah (kurang dari 40% data tersedia)", "🔴", ratio

# ================= CROSS VALIDATION =================
def cross_validate(p_agg, fb, gee_ratio):
    """
    Bandingkan data GEE (aggregated) dengan fallback DB.
    Return dict:
      status       : "konsisten" | "minor_gap" | "konflik"
      emoji        : str
      cbr_gee      : float | None  — CBR dari GEE
      cbr_fb_min   : float          — CBR min dari fallback
      cbr_fb_max   : float          — CBR max dari fallback
      clay_final   : float | None   — clay yang dipakai
      sand_final   : float | None
      silt_final   : float | None
      bdod_final   : float | None
      soc_final    : float | None
      sumber_soil  : "GEE" | "Fallback" | "Blend" | "GEE (tervalidasi)"
      catatan      : str
      use_fb_layer : bool           — apakah profil layer pakai fallback
    """
    if fb is None:
        # Tidak ada data fallback — pakai GEE sepenuhnya
        return {
            "status": "no_ref", "emoji": "📡",
            "cbr_gee": None, "cbr_fb_min": None, "cbr_fb_max": None,
            "clay_final": p_agg["30-60cm"]["clay"],
            "sand_final": p_agg["30-60cm"]["sand"],
            "silt_final": p_agg["30-60cm"]["silt"],
            "bdod_final": p_agg["30-60cm"]["bdod"],
            "soc_final":  p_agg["30-60cm"]["soc"],
            "sumber_soil": "GEE",
            "catatan": "Tidak ada data referensi geologi untuk lokasi ini",
            "use_fb_layer": False
        }

    clay_gee  = p_agg["30-60cm"]["clay"]
    sand_gee  = p_agg["30-60cm"]["sand"]
    bdod_gee  = p_agg["30-60cm"]["bdod"]

    clay_fb   = fb["clay"]
    sand_fb   = fb["sand"]
    bdod_fb   = fb["bdod"]

    # ---- Hitung CBR GEE (pakai estimasi dari nilai GEE) ----
    # Tidak bisa pakai estimate_cbr langsung karena belum dihitung rain
    # Simpan None dulu, akan diisi di analyze()

    # ---- Cek konsistensi jenis tanah ----
    # Konflik signifikan: GEE pasir dominan tapi FB lempung/grumusol atau sebaliknya
    konflik_tekstur = False
    konflik_detail  = ""

    if clay_gee is not None and clay_fb is not None:
        selisih_clay = abs(clay_gee - clay_fb)
        if selisih_clay > 25:
            konflik_tekstur = True
            konflik_detail = f"Clay GEE {clay_gee:.1f}% vs referensi {clay_fb:.1f}%"

    if sand_gee is not None and sand_fb is not None:
        selisih_sand = abs(sand_gee - sand_fb)
        if selisih_sand > 30 and not konflik_tekstur:
            konflik_tekstur = True
            konflik_detail = f"Sand GEE {sand_gee:.1f}% vs referensi {sand_fb:.1f}%"

    # ---- Tentukan sumber data final berdasarkan confidence ----
    # confidence tinggi (>= 0.90) + tidak konflik → GEE tervalidasi
    # confidence sedang (0.70-0.90) + tidak konflik → Blend
    # confidence rendah (< 0.70) → Fallback dominan
    # konflik → pilih yang lebih reliable berdasarkan confidence

    # ---- Selisih CBR sebagai indikator tambahan ----
    # Dihitung kasar dari clay saja untuk flagging, CBR final dihitung di analyze()
    cbr_gap_flag = False
    if clay_gee is not None and clay_fb is not None:
        # Estimasi kasar CBR GEE vs FB tanpa rain/bdod
        cbr_gee_rough = 3 if clay_gee > 45 else (5 if clay_gee > 35 else (7 if clay_gee > 25 else 10))
        cbr_fb_mid    = (fb["cbr_min"] + fb["cbr_max"]) / 2
        if abs(cbr_gee_rough - cbr_fb_mid) > 5:
            cbr_gap_flag = True

    # ================================================================
    # TABEL KEPUTUSAN — cross-validation SELALU jalan di semua level
    # ================================================================

    if not konflik_tekstur:
        # Tidak ada konflik tekstur — blend berbobot sesuai confidence
        if gee_ratio >= 0.90:
            # GEE sangat reliable, tapi tetap blend ringan dengan referensi
            status  = "konsisten"
            emoji   = "✅"
            sumber  = "Blend (GEE dominan)"
            catatan = f"GEE konsisten dengan referensi geologi. Blend GEE 85% + Referensi 15%."
            w_gee, w_fb = 0.85, 0.15
        elif gee_ratio >= 0.70:
            status  = "konsisten"
            emoji   = "✅"
            sumber  = "Blend"
            catatan = f"GEE dan referensi selaras. Blend berbobot GEE {gee_ratio*100:.0f}% + Referensi {(1-gee_ratio)*100:.0f}%."
            w_gee, w_fb = gee_ratio, 1 - gee_ratio
        elif gee_ratio >= 0.40:
            status  = "minor_gap"
            emoji   = "⚠️"
            sumber  = "Blend"
            catatan = f"GEE confidence sedang ({gee_ratio*100:.0f}%). Blend GEE 40% + Referensi 60%."
            w_gee, w_fb = 0.40, 0.60
        else:
            status  = "minor_gap"
            emoji   = "⚠️"
            sumber  = "Fallback"
            catatan = f"GEE confidence sangat rendah ({gee_ratio*100:.0f}%). Digunakan referensi geologi."
            w_gee, w_fb = 0.0, 1.0

        clay_f = _blend(clay_gee, clay_fb, w_gee, w_fb)
        sand_f = _blend(sand_gee, sand_fb, w_gee, w_fb)
        silt_f = _blend(p_agg["30-60cm"]["silt"], fb["silt"], w_gee, w_fb)
        bdod_f = _blend(bdod_gee, bdod_fb, w_gee, w_fb)
        soc_f  = _blend(p_agg["30-60cm"]["soc"],  fb["soc"],  w_gee, w_fb)
        use_fb = (w_fb == 1.0)

    else:
        # Ada konflik tekstur — keputusan berdasarkan confidence
        if gee_ratio >= 0.80:
            # GEE confidence tinggi + konflik → trust GEE tapi flag warning
            status  = "minor_gap"
            emoji   = "⚠️"
            sumber  = "GEE"
            catatan = f"Perbedaan dengan referensi: {konflik_detail}. GEE confidence tinggi, dipakai GEE."
            clay_f = clay_gee; sand_f = sand_gee
            silt_f = p_agg["30-60cm"]["silt"]; bdod_f = bdod_gee
            soc_f  = p_agg["30-60cm"]["soc"];  use_fb = False
        else:
            # Konflik + GEE confidence rendah → prefer fallback
            status  = "konflik"
            emoji   = "🔴"
            sumber  = "Fallback"
            catatan = f"Konflik signifikan: {konflik_detail}. GEE confidence rendah ({gee_ratio*100:.0f}%), digunakan referensi geologi."
            clay_f = clay_fb; sand_f = sand_fb
            silt_f = fb["silt"]; bdod_f = bdod_fb
            soc_f  = fb["soc"];  use_fb = True

    return {
        "status":      status,
        "emoji":       emoji,
        "cbr_gee":     None,          # diisi di analyze()
        "cbr_fb_min":  fb["cbr_min"],
        "cbr_fb_max":  fb["cbr_max"],
        "clay_final":  clay_f,
        "sand_final":  sand_f,
        "silt_final":  silt_f,
        "bdod_final":  bdod_f,
        "soc_final":   soc_f,
        "sumber_soil": sumber,
        "catatan":     catatan,
        "use_fb_layer": use_fb,
        "fb_zona":     fb.get("zona_key", ""),
        "fb_catatan":  fb.get("catatan", ""),
        "is_expansive": fb.get("is_expansive", False),
    }

def _blend(gee_val, fb_val, w_gee, w_fb):
    if gee_val is None and fb_val is None: return None
    if gee_val is None: return fb_val
    if fb_val  is None: return gee_val
    return round(gee_val * w_gee + fb_val * w_fb, 2)

# ================= CLASSIFICATION =================
def classify_detail(c, s, si):
    if c is None or s is None or si is None:
        return "N/A", "Data tidak tersedia"
    if c + s + si == 0:
        return "N/A", "Data tidak valid"
    if c >= 40:
        if s > 20:  return "Lempung Berpasir",     "Dominan lempung dengan campuran pasir cukup signifikan"
        if si > 20: return "Lempung Berlanau",      "Dominan lempung dengan campuran lanau"
        return              "Lempung Murni",         "Sangat dominan lempung, plastisitas tinggi"
    if s >= 60:
        if c > 10:  return "Pasir Berlempung",      "Dominan pasir dengan campuran lempung"
        if si > 15: return "Pasir Berlanau",         "Dominan pasir dengan campuran lanau"
        return              "Pasir Murni",           "Sangat dominan pasir, drainase sangat tinggi"
    if si >= 40:
        if c > 20:  return "Lanau Berlempung",      "Dominan lanau dengan campuran lempung"
        if s > 20:  return "Lanau Berpasir",         "Dominan lanau dengan campuran pasir"
        return              "Lanau Murni",           "Sangat dominan lanau, rentan erosi"
    if c > 25 and s > 25 and si > 25:
        return              "Lempung Campuran (Loam)", "Campuran seimbang — ideal untuk konstruksi"
    if c > s and c > si: return "Lempung Campuran", "Lempung dominan dengan campuran pasir dan lanau"
    if s > si:           return "Pasir Campuran",   "Pasir dominan dengan campuran lempung dan lanau"
    return                      "Lanau Campuran",   "Lanau dominan dengan campuran lempung dan pasir"

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
    if c < 0 or s < 0 or si < 0:            return None
    if soc is not None and soc > 20:         return 1.5
    if c > 45:      v = 3
    elif c > 35:    v = 5
    elif c > 25:    v = 7
    elif s > 60:    v = 18
    else:           v = 10
    if bdod is not None:
        if bdod < 0.90:    v *= 0.35
        elif bdod < 1.00:  v *= 0.55
        elif bdod < 1.10:  v *= 0.70
        elif bdod < 1.20:  v *= 1.00
        elif bdod <= 1.35: v *= 1.15
        else:              v *= 1.35
    if rain is not None:
        if rain < 500:     v *= 1.15
        elif rain < 1500:  v *= 1.05
        elif rain < 2500:  v *= 1.00
        elif rain < 3500:  v *= 0.90
        else:              v *= 0.80
    return round(v, 1)

def cbr_label(cbr):
    if cbr is None: return "N/A", "⬜"
    if cbr < 3:     return "Sangat Lemah", "🔴"
    if cbr < 6:     return "Lemah", "🟠"
    if cbr < 10:    return "Sedang", "🟡"
    if cbr < 20:    return "Baik", "🟢"
    return                 "Sangat Baik", "🔵"

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
    if slope is None: return "N/A", "⬜"
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

def fmt(val, dec=2, unit="", fallback="N/A"):
    if val is None: return fallback
    return f"{val:.{dec}f}{unit}"

# ================= ROAD ISSUES =================
def road_issues(cbr, clay, sand, silt, soc, bdod, rain, slope, is_peat_flag, is_expansive=False):
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
            issues.append(("🟡", f"Daya dukung <b>memenuhi standar jalan lokal</b> (CBR <b>{cbr}%</b>) — pantau beban berat"))
        else:
            issues.append(("🟢", f"Daya dukung <b>baik</b> (CBR <b>{cbr}%</b>) — memenuhi standar konstruksi jalan"))
    if is_expansive:
        issues.append(("🔴", "<b>Tanah ekspansif</b> — kembang susut tinggi, retak reflektif parah saat kering"))
    elif clay is not None:
        if clay > 40:
            issues.append(("🔴", f"<b>Clay sangat tinggi</b> ({clay:.1f}%) — risiko retak reflektif dan kembang susut"))
        elif clay > 25:
            issues.append(("🟠", f"Clay cukup tinggi ({clay:.1f}%) — waspadai <b>retak permukaan</b> saat musim kering"))
        elif clay < 10 and sand is not None and sand > 60:
            issues.append(("🟡", f"Pasir dominan ({sand:.1f}%) — risiko <b>erosi dan gerusan</b> di tepi jalan"))
    if rain is not None:
        if rain > 3000:
            if clay is not None and clay > 30:
                issues.append(("🔴", f"<b>Curah hujan sangat tinggi</b> ({rain:.0f} mm/thn) + clay tinggi — drainase kritis"))
            else:
                issues.append(("🟠", f"<b>Curah hujan tinggi</b> ({rain:.0f} mm/thn) — drainase jalan harus memadai"))
        elif rain > 2000:
            issues.append(("🟡", f"Curah hujan cukup tinggi ({rain:.0f} mm/thn) — perhatikan <b>kemiringan melintang</b> jalan"))
        elif rain < 300:
            issues.append(("🟡", f"Curah hujan sangat rendah ({rain:.0f} mm/thn) — waspadai <b>deformasi termal</b>"))
    if slope is not None:
        if slope > 25:
            issues.append(("🔴", f"<b>Lereng sangat curam</b> ({slope:.1f} deg) — retaining wall wajib"))
        elif slope > 15:
            issues.append(("🟠", f"Lereng curam ({slope:.1f} deg) — perlu <b>retaining wall</b> dan drainase lereng"))
        elif slope > 8:
            issues.append(("🟡", f"Lereng miring ({slope:.1f} deg) — perlu <b>pengendalian erosi</b> permukaan"))
    if bdod is not None:
        if bdod < 1.0:
            issues.append(("🔴", f"<b>Kepadatan sangat rendah</b> ({bdod:.2f} g/cm3) — tanah gembur, berisiko ambles"))
        elif bdod < 1.2:
            issues.append(("🟠", f"Kepadatan rendah ({bdod:.2f} g/cm3) — perlu <b>pemadatan</b> sebelum konstruksi"))
    if soc is not None and 5 < soc <= 20:
        issues.append(("🟠", f"Bahan organik cukup tinggi ({soc:.1f}%) — <b>tanah tidak stabil</b> jangka panjang"))
    if not issues:
        issues.append(("🟢", "<b>Tidak ada masalah signifikan</b> teridentifikasi berdasarkan data tersedia"))
    return issues

# ================= ANALYZE =================
def analyze(lat, lon, chat_id):
    log.info(f"Analyze start: {lat}, {lon}")
    tg("Menganalisis tanah... mohon tunggu sebentar.", chat_id)

    local, kecamatan, region, state_dist, country, cc = get_location_name(lat, lon)
    flag_em = flag(cc)

    raw   = get_soil_profile(lat, lon)
    p     = aggregate(raw)
    rain  = get_rain(lat, lon)
    slope = get_slope(lat, lon)

    conf_lbl, conf_em, gee_ratio = data_confidence(p, rain, slope)

    # Ambil fallback dari DB — coba kecamatan dulu, fallback ke local
    fb = lookup_fallback(kecamatan, state_dist, region)
    if fb is None:
        fb = lookup_fallback(local, state_dist, region)
    log.info(f"Fallback lookup: kec={kecamatan} local={local} dist={state_dist} → {fb['zona_key'] if fb else 'None'}")

    # Cross-validate GEE vs fallback
    cv = cross_validate(p, fb, gee_ratio)

    # Gunakan nilai final dari cross-validation
    clay = cv["clay_final"]
    sand = cv["sand_final"]
    silt = cv["silt_final"]
    bd   = cv["bdod_final"]

    # SOC — pakai max dari semua layer untuk deteksi gambut
    all_depths = ["0-5cm","5-15cm","15-30cm","30-60cm","60-100cm"]
    soc_max = max([v for v in [raw[d]["soc"] for d in all_depths] if v is not None], default=None)
    # Jika GEE SOC tidak tersedia, pakai SOC dari fallback
    if soc_max is None and fb is not None:
        soc_max = fb["soc"]
    bd_min = min([v for v in [raw[d]["bdod"] for d in all_depths] if v is not None], default=None)
    if bd_min is None and fb is not None:
        bd_min = fb["bdod"]

    is_peat_flag  = peat(soc_max, bd_min)
    is_expansive  = cv.get("is_expansive", False)

    # CBR dari nilai final (cross-validated)
    cbr_final     = estimate_cbr(clay, sand, silt, bd, soc_max, rain)
    cv["cbr_gee"] = cbr_final  # simpan untuk ditampilkan

    # CBR range dari fallback
    cbr_fb_min = cv["cbr_fb_min"]
    cbr_fb_max = cv["cbr_fb_max"]

    cbr_lbl, cbr_em  = cbr_label(cbr_final)
    settle, set_em   = estimate_settlement(cbr_final, clay, soc_max)
    hard             = hard_layer(bd)
    slope_lbl, slope_em = slope_label(slope)
    rain_lbl, rain_em   = rain_label(rain)
    ls_risk, ls_em      = landslide_risk(slope, clay, silt, rain, bd)

    soil_name, soil_desc = classify_detail(clay, sand, silt)
    s_emoji              = soil_emoji(soil_name)

    loc_line = local
    if region and region != local:
        loc_line += f", {region}"

    # Format CBR — tampilkan hasil hitung + range referensi
    if cbr_final is not None and cbr_fb_min is not None:
        cbr_txt = (
            f"{cbr_em} <b>{cbr_final}%</b> ({cbr_lbl})\n"
            f"         Ref. literatur : <b>{cbr_fb_min}-{cbr_fb_max}%</b>"
        )
    elif cbr_final is not None:
        cbr_txt = f"{cbr_em} <b>{cbr_final}%</b> ({cbr_lbl})"
    elif cbr_fb_min is not None:
        cbr_txt = f"🟡 <b>{cbr_fb_min}-{cbr_fb_max}%</b> (dari referensi)"
    else:
        cbr_txt = "N/A"

    rain_txt  = f"{rain_em} <b>{rain:.0f} mm/thn</b> ({rain_lbl})" if rain is not None else "N/A"
    slope_txt = f"{slope_em} <b>{slope:.1f} deg</b> ({slope_lbl})"

    peat_soc_note = f" (SOC maks {soc_max:.1f}%)" if soc_max is not None else ""
    peat_line = (
        f"  {'🌿' if is_peat_flag else '✅'} <b>Gambut</b>     : "
        f"{'Terindikasi' if is_peat_flag else 'Tidak terindikasi'}{peat_soc_note}\n"
        + (f"  🔴 <b>Ekspansif</b>  : Terindikasi\n" if is_expansive else "")
        + "\n"
    )

    issues     = road_issues(cbr_final, clay, sand, silt, soc_max, bd, rain, slope, is_peat_flag, is_expansive)
    issues_txt = "\n".join(f"  {em} {desc}" for em, desc in issues)

    # Bagian validasi silang
    if fb is not None:
        cv_section = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 <b>VALIDASI SILANG DATA</b>\n"
            f"  {cv['emoji']} <b>{cv['status'].upper().replace('_',' ')}</b>\n"
            f"  {cv['catatan']}\n"
            f"  Sumber data tanah : <b>{cv['sumber_soil']}</b>\n"
            f"  Zona referensi    : <b>{fb.get('zona_key','').replace('_',' ').title()}</b>\n"
            f"  {fb.get('catatan','')}\n\n"
        )
    else:
        cv_section = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 <b>VALIDASI SILANG DATA</b>\n"
            f"  📡 Tidak ada data referensi geologi untuk lokasi ini\n\n"
        )

    # Profil layer — tampilkan GEE jika tersedia, fallback ringkasan jika tidak
    depth_labels = {
        "0-30cm":   ("🟫", "Lapisan Atas   (0-30 cm)"),
        "30-60cm":  ("🟤", "Lapisan Tengah (30-60 cm)"),
        "60-100cm": ("⬛", "Lapisan Bawah  (60-100 cm)"),
    }

    profil_section = ""
    if gee_ratio >= 0.40:
        # GEE punya data cukup — tampilkan per layer
        for d, data in p.items():
            em, dlabel = depth_labels.get(d, ("🔲", d))
            c_v   = data["clay"]
            s_v   = data["sand"]
            si_v  = data["silt"]
            soc_v = data["soc"]
            bd_v  = data["bdod"]
            sn, _ = classify_detail(c_v, s_v, si_v)
            profil_section += (
                f"\n{em} <b>{dlabel}</b>\n"
                f"  Jenis   : <b>{sn}</b>\n"
                f"  🟫 Clay  : <b>{fmt(c_v,1,'%','N/A')}</b>  {bar(c_v)}\n"
                f"  🟡 Sand  : <b>{fmt(s_v,1,'%','N/A')}</b>  {bar(s_v)}\n"
                f"  🔘 Silt  : <b>{fmt(si_v,1,'%','N/A')}</b>  {bar(si_v)}\n"
                f"  🌱 Bhn Organik : <b>{fmt(soc_v,2,'%','N/A')}</b>\n"
                f"  🪨 Kepadatan   : <b>{fmt(bd_v,2,' g/cm3','N/A')}</b>\n"
            )
    else:
        # GEE data minim — tampilkan ringkasan dari fallback
        if fb is not None:
            profil_section = (
                f"\n⚠️ <i>Data GEE tidak memadai untuk lokasi ini.</i>\n"
                f"<i>Profil tanah berdasarkan referensi geologi zona <b>{fb.get('zona_key','').replace('_',' ').title()}</b>:</i>\n\n"
                f"  🟫 Clay  : <b>{fb['clay']:.1f}%</b>  {bar(fb['clay'])}\n"
                f"  🟡 Sand  : <b>{fb['sand']:.1f}%</b>  {bar(fb['sand'])}\n"
                f"  🔘 Silt  : <b>{fb['silt']:.1f}%</b>  {bar(fb['silt'])}\n"
                f"  🌱 Bhn Organik : <b>{fb['soc']:.2f}%</b>\n"
                f"  🪨 Kepadatan   : <b>{fb['bdod']:.2f} g/cm3</b>\n"
                f"  📋 Klasifikasi : <b>{fb['jenis_tanah']}</b> ({fb['uscs']})\n"
            )
        else:
            profil_section = "\n⚠️ <i>Data tanah tidak tersedia untuk lokasi ini.</i>\n"

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
        + peat_line
        + cv_section
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪨 <b>PROFIL TANAH DETAIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
        + profil_section
        + f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>ANALISIS POTENSI MASALAH JALAN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{issues_txt}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>TINGKAT KEPERCAYAAN DATA</b>\n"
        f"  {conf_em} <b>{conf_lbl}</b>\n"
        f"  GEE data tersedia : <b>{gee_ratio*100:.0f}%</b>\n"
        f"  Sumber            : SoilGrids ISRIC v2 + CHIRPS + SRTM\n"
        f"  Referensi geologi : {'Tersedia' if fb else 'Tidak tersedia'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>Preliminary assessment via SoilGrids ISRIC + GEE + Literatur Geoteknik.\n"
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
    tg("Bot Soil AI siap digunakan!", ADMIN_ID)
    loop()

main()
