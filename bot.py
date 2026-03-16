import ee
import os
import json
import requests
import logging
import time
import re

TELEGRAM_TOKEN="8385287062:AAGgwYA0l7-Cuq4jA7dgcy5GkFAvDp7X1GM"
TELEGRAM_CHAT_ID="1145085024"

logging.basicConfig(level=logging.INFO)
log=logging.getLogger(__name__)
last_update_id=0

service_account=json.loads(os.environ["GEE_KEY"])

credentials=ee.ServiceAccountCredentials(
    service_account["client_email"],
    key_data=json.dumps(service_account)
)

ee.Initialize(credentials)

# ================= TELEGRAM =================

def tg(msg,chat_id=None):

    cid=chat_id or TELEGRAM_CHAT_ID

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":cid,"text":msg,"parse_mode":"HTML"},
        timeout=30
    )

# ================= LOCATION =================

def get_location(lat,lon):

    try:

        url="https://nominatim.openstreetmap.org/reverse"

        r=requests.get(url,params={
            "lat":lat,
            "lon":lon,
            "format":"json"
        },headers={"User-Agent":"soilbot"})

        addr=r.json()["address"]

        city=addr.get("city") or addr.get("town") or addr.get("county") or ""
        state=addr.get("state","")
        country=addr.get("country","")

        return f"{city}, {state}, {country}"

    except:
        return "Lokasi tidak diketahui"

# ================= ROAD =================

def get_road(lat,lon):

    try:

        url="https://overpass-api.de/api/interpreter"

        q=f"""
        [out:json];
        way(around:100,{lat},{lon})["highway"];
        out tags 1;
        """

        r=requests.post(url,data=q,timeout=20)
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
            bestEffort=True,
            maxPixels=1e9
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

def rain_class(mm):

    if mm<1000:
        return "rendah"

    if mm<2000:
        return "sedang"

    if mm<3000:
        return "tinggi"

    return "sangat tinggi"

# ================= SOIL CLASS =================

def classify_soil(clay,sand,silt):

    if clay>40 and silt>40:
        return "Lempung Lanauan"

    if clay>40:
        return "Lempung"

    if clay>30 and sand>40:
        return "Lempung Berpasir"

    if silt>50:
        return "Lanau"

    if sand>60:
        return "Pasir"

    return "Tanah campuran"

# ================= PEAT =================

def detect_peat(soc,bdod):

    if soc>=20 and bdod<=1.2:
        return True

    return False

# ================= EXPANSIVE =================

def expansive(clay):

    return clay>45

# ================= SOFT SOIL =================

def detect_soft(clay,bdod,soc):

    score=0

    if bdod<1.1:
        score+=1

    if clay>40:
        score+=1

    if soc>15:
        score+=1

    return score>=2

# ================= CBR MODEL =================

def estimate_cbr(clay,sand,silt,soc,rain):

    if soc>20:
        cbr=2

    elif clay>45:
        cbr=3

    elif clay>30:
        cbr=5

    elif silt>50:
        cbr=6

    elif sand>60:
        cbr=15

    else:
        cbr=8

    if rain>2500:
        cbr*=0.8

    return round(cbr,1)

# ================= HARD LAYER =================

def estimate_hard_layer(profile):

    for d,data in profile.items():

        if data["bdod"]>1.5:
            return f"sekitar {d}"

    return "> 1 m"

# ================= IMPACT =================

def impacts(clay,sand,rain,peat,exp):

    out=[]

    if peat:
        out.append("Penurunan tanah besar akibat tanah organik")

    if clay>35:
        out.append("Retak reflektif akibat kembang susut lempung")

    if clay>30:
        out.append("Rutting atau ambles akibat daya dukung rendah")

    if exp:
        out.append("Potensi heave akibat lempung ekspansif")

    if rain>2000:
        out.append("Genangan air saat musim hujan")

    if sand>60:
        out.append("Erosi bahu jalan akibat material pasir")

    return out

# ================= RECOMMEND =================

def recommendations(clay,sand,cbr,peat):

    if peat:

        return [
        "Perbaikan tanah gambut (soil replacement)",
        "Preloading + vertical drain",
        "Geotextile atau geogrid reinforcement"
        ]

    if cbr<3:

        return [
        "Perkuatan tanah dasar",
        "Geogrid reinforcement"
        ]

    if clay>40:

        return [
        "Stabilisasi kapur 5–8%",
        "Geotextile pada subgrade",
        "Drainase baik"
        ]

    if sand>60:

        return [
        "Pemadatan tinggi",
        "Stabilisasi semen"
        ]

    return [
    "Perkerasan standar",
    "Drainase tepi jalan"
    ]

# ================= TESTS =================

def tests(clay,sand):

    t=["Field CBR"]

    if clay>30:
        t.append("Atterberg limits")

    if sand>50:
        t.append("Sand cone test")

    t.append("DCP test")
    t.append("Sondir / CPT")

    return t

# ================= ANALYSIS =================

def analyze_soil(lat,lon,chat_id):

    tg("⏳ Menganalisis lokasi...",chat_id)

    profile=get_soil_profile(lat,lon)

    location=get_location(lat,lon)

    road=get_road(lat,lon)

    rain=get_rain(lat,lon)

    slope=get_slope(lat,lon)

    clay=profile["30-60cm"]["clay"]
    sand=profile["30-60cm"]["sand"]
    silt=profile["30-60cm"]["silt"]
    bdod=profile["30-60cm"]["bdod"]
    soc=profile["30-60cm"]["soc"]

    soil_type=classify_soil(clay,sand,silt)

    peat=detect_peat(profile["0-5cm"]["soc"],profile["0-5cm"]["bdod"])

    exp=expansive(clay)

    soft=detect_soft(clay,bdod,soc)

    cbr=estimate_cbr(clay,sand,silt,soc,rain)

    hard=estimate_hard_layer(profile)

    imp=impacts(clay,sand,rain,peat,exp)

    rec=recommendations(clay,sand,cbr,peat)

    tst=tests(clay,sand)

    peat_txt="🌱 Terindikasi gambut" if peat else "🌱 Tidak terindikasi gambut"

    soft_txt="🚨 Subgrade sangat lunak" if soft else "🟢 Subgrade relatif normal"

    exp_txt="⚠ Lempung ekspansif" if exp else "🟢 Tidak ekspansif"

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
<b>{rain:.0f} mm/tahun ({rain_class(rain)})</b>

⛰ Kemiringan lereng
<b>{slope:.1f}°</b>

🧱 Perkiraan tanah relatif keras
<b>{hard}</b>

{peat_txt}
{soft_txt}
{exp_txt}

━━━━━━━━━━━━

🪨 <b>PROFIL TANAH (hingga 1 m)</b>
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

    msg+="\n━━━━━━━━━━━━\n⚠ <b>DAMPAK TERHADAP PERKERASAN</b>\n"

    for i,x in enumerate(imp,1):
        msg+=f"{i}. {x}\n"

    msg+="\n🛠 <b>REKOMENDASI PENANGANAN</b>\n"

    for x in rec:
        msg+=f"• {x}\n"

    msg+="\n🔬 <b>PENGUJIAN TANAH</b>\n"

    for x in tst:
        msg+=f"• {x}\n"

    tg(msg,chat_id)

# ================= TELEGRAM LOOP =================

def check_messages():

    global last_update_id

    while True:

        try:

            url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=30"

            r=requests.get(url).json()

            for u in r["result"]:

                last_update_id=u["update_id"]

                msg=u["message"]

                chat=str(msg["chat"]["id"])

                text=msg.get("text","")

                m=re.search(r"(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)",text)

                if m:

                    lat=float(m.group(1))
                    lon=float(m.group(2))

                    analyze_soil(lat,lon,chat)

                else:

                    tg("📍 Kirim koordinat\n<code>-7.6048,111.9102</code>",chat)

        except Exception as e:

            log.error(e)

        time.sleep(2)

def main():

    tg("✅ Bot AI Analisis Tanah aktif")

    check_messages()

main()
