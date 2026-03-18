# =============================================================================
# SOIL FALLBACK DATABASE — JAWA TIMUR (ALL 666 KECAMATAN) + JAKARTA
# Sumber: Peta Geologi ESDM 1:100.000, BGL, LIPI, ITB, ITS, UNIBRAW,
#         Bina Marga PU, Penelitian CBR lapangan jurnal nasional,
#         Data BPS/Kemendagri 2024
#
# KEY FORMAT: "nama_kecamatan|nama_kabupaten_kota"
# Ini untuk menghindari duplikat — banyak nama kecamatan sama lintas kab/kota
# =============================================================================

ZONA = {
    "alluvial_pantai": {
        "jenis_tanah": "Lempung Alluvial Lunak",
        "uscs": "CH/CL",
        "cbr_min": 1.5, "cbr_max": 3.5,
        "clay": 42.0, "sand": 20.0, "silt": 38.0,
        "bdod": 1.05, "soc": 3.5,
        "is_expansive": False,
        "catatan": "Endapan delta/pantai, tanah lunak, settlement tinggi"
    },
    "alluvial_sungai": {
        "jenis_tanah": "Lempung Alluvial Sedang",
        "uscs": "CL",
        "cbr_min": 2.5, "cbr_max": 5.0,
        "clay": 35.0, "sand": 28.0, "silt": 37.0,
        "bdod": 1.15, "soc": 2.0,
        "is_expansive": False,
        "catatan": "Endapan sungai, konsistensi medium"
    },
    "grumusol_ekspansif": {
        "jenis_tanah": "Lempung Ekspansif (Grumusol)",
        "uscs": "CH",
        "cbr_min": 2.0, "cbr_max": 4.5,
        "clay": 55.0, "sand": 15.0, "silt": 30.0,
        "bdod": 1.20, "soc": 1.5,
        "is_expansive": True,
        "catatan": "Grumusol, LL>50%, PI>25%, kembang susut tinggi, retak musim kemarau"
    },
    "andosol_vulkanik": {
        "jenis_tanah": "Andosol Vulkanik",
        "uscs": "ML/MH",
        "cbr_min": 5.0, "cbr_max": 10.0,
        "clay": 20.0, "sand": 35.0, "silt": 45.0,
        "bdod": 0.90, "soc": 6.0,
        "is_expansive": False,
        "catatan": "Tanah vulkanik gembur, permeabilitas tinggi, rentan erosi"
    },
    "latosol_merah": {
        "jenis_tanah": "Latosol Merah",
        "uscs": "SC/CL",
        "cbr_min": 5.0, "cbr_max": 9.0,
        "clay": 30.0, "sand": 38.0, "silt": 32.0,
        "bdod": 1.20, "soc": 3.0,
        "is_expansive": False,
        "catatan": "Pelapukan batuan vulkanik intensif, konsistensi sedang-kaku"
    },
    "litosol_berbatu": {
        "jenis_tanah": "Litosol / Tanah Berbatu",
        "uscs": "GC/GM",
        "cbr_min": 8.0, "cbr_max": 20.0,
        "clay": 18.0, "sand": 55.0, "silt": 27.0,
        "bdod": 1.45, "soc": 1.5,
        "is_expansive": False,
        "catatan": "Batuan kapur/breksi, daya dukung baik, perlu blasting"
    },
    "mediteran_kapur": {
        "jenis_tanah": "Tanah Mediteran (Kapur)",
        "uscs": "CL-ML",
        "cbr_min": 4.0, "cbr_max": 8.0,
        "clay": 28.0, "sand": 38.0, "silt": 34.0,
        "bdod": 1.32, "soc": 1.2,
        "is_expansive": False,
        "catatan": "Tanah kapur/mediteran, konsistensi sedang, drainase baik"
    },
    "regosol_pantai": {
        "jenis_tanah": "Regosol Pasiran",
        "uscs": "SP/SM",
        "cbr_min": 8.0, "cbr_max": 18.0,
        "clay": 10.0, "sand": 70.0, "silt": 20.0,
        "bdod": 1.40, "soc": 0.8,
        "is_expansive": False,
        "catatan": "Pasir pantai/regosol, daya dukung baik tapi rentan erosi"
    },
    "alluvial_rawa": {
        "jenis_tanah": "Lempung Organik Rawa",
        "uscs": "OH/OL",
        "cbr_min": 1.0, "cbr_max": 2.5,
        "clay": 40.0, "sand": 15.0, "silt": 45.0,
        "bdod": 1.00, "soc": 8.0,
        "is_expansive": False,
        "catatan": "Lempung organik/tambak, sangat lunak, settlement besar"
    },
    "vulkanik_sedang": {
        "jenis_tanah": "Lempung Vulkanik Sedang",
        "uscs": "CL/SC",
        "cbr_min": 4.5, "cbr_max": 8.0,
        "clay": 32.0, "sand": 33.0, "silt": 35.0,
        "bdod": 1.22, "soc": 2.5,
        "is_expansive": False,
        "catatan": "Campuran material vulkanik, konsistensi medium stiff"
    },
    "madura_lempung": {
        "jenis_tanah": "Lempung Madura",
        "uscs": "CL/CH",
        "cbr_min": 2.0, "cbr_max": 5.0,
        "clay": 45.0, "sand": 20.0, "silt": 35.0,
        "bdod": 1.12, "soc": 2.0,
        "is_expansive": True,
        "catatan": "Lempung ekspansif Madura, kembang susut tinggi"
    },
    "urban_jakarta_utara": {
        "jenis_tanah": "Lempung Alluvial Marina Lunak",
        "uscs": "CH/OH",
        "cbr_min": 1.0, "cbr_max": 2.0,
        "clay": 50.0, "sand": 12.0, "silt": 38.0,
        "bdod": 0.95, "soc": 4.5,
        "is_expansive": False,
        "catatan": "Alluvium pantai/reklamasi, tanah lunak, amblesan ekstrim, tiang pancang wajib"
    },
    "urban_jakarta_selatan": {
        "jenis_tanah": "Kipas Alluvial Vulkanik",
        "uscs": "CL/SC",
        "cbr_min": 4.0, "cbr_max": 7.0,
        "clay": 30.0, "sand": 38.0, "silt": 32.0,
        "bdod": 1.25, "soc": 2.0,
        "is_expansive": False,
        "catatan": "Kipas aluvial dari selatan, tanah sedang, kelas situs SD"
    },
}

# =============================================================================
# DATABASE UTAMA — KEY: "kecamatan|kabupaten_kota"
# =============================================================================

DB = {

    # =========================================================================
    # KOTA SURABAYA
    # =========================================================================
    "kenjeran|surabaya":           "alluvial_pantai",
    "bulak|surabaya":              "alluvial_pantai",
    "semampir|surabaya":           "alluvial_pantai",
    "pabean cantian|surabaya":     "alluvial_pantai",
    "krembangan|surabaya":         "alluvial_pantai",
    "tegalsari|surabaya":          "alluvial_sungai",
    "genteng|surabaya":            "alluvial_sungai",
    "bubutan|surabaya":            "alluvial_sungai",
    "simokerto|surabaya":          "alluvial_sungai",
    "tambaksari|surabaya":         "alluvial_sungai",
    "gubeng|surabaya":             "alluvial_sungai",
    "rungkut|surabaya":            "alluvial_sungai",
    "tenggilis mejoyo|surabaya":   "alluvial_sungai",
    "gunung anyar|surabaya":       "alluvial_sungai",
    "sukolilo|surabaya":           "alluvial_sungai",
    "mulyorejo|surabaya":          "alluvial_pantai",
    "benowo|surabaya":             "alluvial_pantai",
    "pakal|surabaya":              "alluvial_sungai",
    "asemrowo|surabaya":           "alluvial_pantai",
    "sukomanunggal|surabaya":      "alluvial_sungai",
    "tandes|surabaya":             "alluvial_sungai",
    "sambikerep|surabaya":         "alluvial_sungai",
    "lakarsantri|surabaya":        "grumusol_ekspansif",
    "sawahan|surabaya":            "alluvial_sungai",
    "wonokromo|surabaya":          "alluvial_sungai",
    "karang pilang|surabaya":      "grumusol_ekspansif",
    "dukuh pakis|surabaya":        "alluvial_sungai",
    "wiyung|surabaya":             "grumusol_ekspansif",
    "gayungan|surabaya":           "alluvial_sungai",
    "jambangan|surabaya":          "alluvial_sungai",
    "wonocolo|surabaya":           "alluvial_sungai",

    # =========================================================================
    # KABUPATEN SIDOARJO
    # =========================================================================
    "sidoarjo|sidoarjo":           "alluvial_pantai",
    "buduran|sidoarjo":            "alluvial_pantai",
    "candi|sidoarjo":              "alluvial_sungai",
    "porong|sidoarjo":             "alluvial_rawa",
    "krembung|sidoarjo":           "alluvial_sungai",
    "tulangan|sidoarjo":           "alluvial_sungai",
    "tanggulangin|sidoarjo":       "alluvial_rawa",
    "jabon|sidoarjo":              "alluvial_rawa",
    "krian|sidoarjo":              "alluvial_sungai",
    "balongbendo|sidoarjo":        "alluvial_sungai",
    "wonoayu|sidoarjo":            "alluvial_sungai",
    "tarik|sidoarjo":              "alluvial_sungai",
    "prambon|sidoarjo":            "alluvial_sungai",
    "taman|sidoarjo":              "alluvial_sungai",
    "waru|sidoarjo":               "alluvial_pantai",
    "gedangan|sidoarjo":           "alluvial_pantai",
    "sedati|sidoarjo":             "alluvial_pantai",
    "sukodono|sidoarjo":           "alluvial_sungai",

    # =========================================================================
    # KABUPATEN GRESIK
    # =========================================================================
    "gresik|gresik":               "alluvial_pantai",
    "kebomas|gresik":              "alluvial_pantai",
    "manyar|gresik":               "alluvial_pantai",
    "bungah|gresik":               "alluvial_pantai",
    "sidayu|gresik":               "alluvial_pantai",
    "ujung pangkah|gresik":        "alluvial_pantai",
    "panceng|gresik":              "mediteran_kapur",
    "duduksampeyan|gresik":        "alluvial_sungai",
    "cerme|gresik":                "alluvial_sungai",
    "benjeng|gresik":              "alluvial_sungai",
    "balong panggang|gresik":      "alluvial_sungai",
    "driyorejo|gresik":            "alluvial_sungai",
    "wringinanom|gresik":          "alluvial_sungai",
    "menganti|gresik":             "alluvial_sungai",
    "kedamean|gresik":             "alluvial_sungai",
    "sangkapura|gresik":           "regosol_pantai",
    "tambak|gresik":               "regosol_pantai",
    "dukun|gresik":                "alluvial_sungai",

    # =========================================================================
    # KABUPATEN MOJOKERTO
    # =========================================================================
    "mojosari|mojokerto":          "alluvial_sungai",
    "bangsal|mojokerto":           "alluvial_sungai",
    "mojoanyar|mojokerto":         "alluvial_sungai",
    "sooko|mojokerto":             "alluvial_sungai",
    "puri|mojokerto":              "alluvial_sungai",
    "jetis|mojokerto":             "alluvial_sungai",
    "dawarblandong|mojokerto":     "grumusol_ekspansif",
    "kemlagi|mojokerto":           "grumusol_ekspansif",
    "gedeg|mojokerto":             "alluvial_sungai",
    "ngoro|mojokerto":             "vulkanik_sedang",
    "pungging|mojokerto":          "alluvial_sungai",
    "kutorejo|mojokerto":          "vulkanik_sedang",
    "trawas|mojokerto":            "andosol_vulkanik",
    "pacet|mojokerto":             "andosol_vulkanik",
    "gondang|mojokerto":           "vulkanik_sedang",
    "jatirejo|mojokerto":          "latosol_merah",
    "dlanggu|mojokerto":           "alluvial_sungai",
    "benar|mojokerto":             "alluvial_sungai",

    # =========================================================================
    # KOTA MOJOKERTO
    # =========================================================================
    "magersari|kota mojokerto":    "alluvial_sungai",
    "prajuritkulon|kota mojokerto": "alluvial_sungai",
    "kranggan|kota mojokerto":     "alluvial_sungai",

    # =========================================================================
    # KABUPATEN JOMBANG
    # =========================================================================
    "jombang|jombang":             "alluvial_sungai",
    "peterongan|jombang":          "alluvial_sungai",
    "jogoroto|jombang":            "alluvial_sungai",
    "diwek|jombang":               "alluvial_sungai",
    "gudo|jombang":                "alluvial_sungai",
    "perak|jombang":               "alluvial_sungai",
    "bandar kedungmulyo|jombang":  "alluvial_sungai",
    "ploso|jombang":               "alluvial_sungai",
    "kabuh|jombang":               "grumusol_ekspansif",
    "plandaan|jombang":            "grumusol_ekspansif",
    "kudu|jombang":                "grumusol_ekspansif",
    "ngusikan|jombang":            "grumusol_ekspansif",
    "mojoagung|jombang":           "alluvial_sungai",
    "sumobito|jombang":            "alluvial_sungai",
    "kesamben|jombang":            "alluvial_sungai",
    "tembelang|jombang":           "alluvial_sungai",
    "megaluh|jombang":             "alluvial_sungai",
    "bareng|jombang":              "vulkanik_sedang",
    "wonosalam|jombang":           "andosol_vulkanik",
    "mojowarno|jombang":           "vulkanik_sedang",
    "ngoro|jombang":               "vulkanik_sedang",

    # =========================================================================
    # KABUPATEN LAMONGAN
    # =========================================================================
    "lamongan|lamongan":           "grumusol_ekspansif",
    "tikung|lamongan":             "grumusol_ekspansif",
    "sarirejo|lamongan":           "grumusol_ekspansif",
    "deket|lamongan":              "alluvial_sungai",
    "glagah|lamongan":             "alluvial_sungai",
    "karangbinangun|lamongan":     "alluvial_pantai",
    "turi|lamongan":               "alluvial_sungai",
    "kalitengah|lamongan":         "alluvial_sungai",
    "karanggeneng|lamongan":       "alluvial_sungai",
    "sekaran|lamongan":            "alluvial_sungai",
    "maduran|lamongan":            "alluvial_sungai",
    "laren|lamongan":              "alluvial_pantai",
    "solokuro|lamongan":           "mediteran_kapur",
    "paciran|lamongan":            "mediteran_kapur",
    "brondong|lamongan":           "mediteran_kapur",
    "bluluk|lamongan":             "grumusol_ekspansif",
    "sukorame|lamongan":           "grumusol_ekspansif",
    "modo|lamongan":               "grumusol_ekspansif",
    "babat|lamongan":              "alluvial_sungai",
    "pucuk|lamongan":              "alluvial_sungai",
    "sukodadi|lamongan":           "alluvial_sungai",
    "sugio|lamongan":              "grumusol_ekspansif",
    "kedungpring|lamongan":        "grumusol_ekspansif",
    "ngimbang|lamongan":           "grumusol_ekspansif",
    "sambeng|lamongan":            "latosol_merah",
    "mantup|lamongan":             "latosol_merah",
    "kembangbahu|lamongan":        "alluvial_sungai",

    # =========================================================================
    # KABUPATEN TUBAN
    # =========================================================================
    "tuban|tuban":                 "mediteran_kapur",
    "jenu|tuban":                  "mediteran_kapur",
    "merakurak|tuban":             "mediteran_kapur",
    "bancar|tuban":                "mediteran_kapur",
    "tambakboyo|tuban":            "mediteran_kapur",
    "bangilan|tuban":              "grumusol_ekspansif",
    "senori|tuban":                "grumusol_ekspansif",
    "singgahan|tuban":             "litosol_berbatu",
    "montong|tuban":               "litosol_berbatu",
    "parengan|tuban":              "grumusol_ekspansif",
    "soko|tuban":                  "grumusol_ekspansif",
    "rengel|tuban":                "alluvial_sungai",
    "grabagan|tuban":              "grumusol_ekspansif",
    "plumpang|tuban":              "alluvial_sungai",
    "widang|tuban":                "alluvial_sungai",
    "palang|tuban":                "alluvial_pantai",
    "semanding|tuban":             "mediteran_kapur",
    "kenduruan|tuban":             "mediteran_kapur",
    "kerek|tuban":                 "mediteran_kapur",
    "jatirogo|tuban":              "grumusol_ekspansif",

    # =========================================================================
    # KABUPATEN BOJONEGORO
    # =========================================================================
    "bojonegoro|bojonegoro":       "grumusol_ekspansif",
    "trucuk|bojonegoro":           "grumusol_ekspansif",
    "malo|bojonegoro":             "alluvial_sungai",
    "purwosari|bojonegoro":        "litosol_berbatu",
    "padangan|bojonegoro":         "grumusol_ekspansif",
    "kasiman|bojonegoro":          "grumusol_ekspansif",
    "ngraho|bojonegoro":           "grumusol_ekspansif",
    "tambakrejo|bojonegoro":       "grumusol_ekspansif",
    "ngambon|bojonegoro":          "litosol_berbatu",
    "sekar|bojonegoro":            "litosol_berbatu",
    "bubulan|bojonegoro":          "latosol_merah",
    "gondang|bojonegoro":          "grumusol_ekspansif",
    "temayang|bojonegoro":         "latosol_merah",
    "sugihwaras|bojonegoro":       "grumusol_ekspansif",
    "kedewan|bojonegoro":          "grumusol_ekspansif",
    "kepohbaru|bojonegoro":        "grumusol_ekspansif",
    "baureno|bojonegoro":          "alluvial_sungai",
    "kanor|bojonegoro":            "alluvial_sungai",
    "sumberrejo|bojonegoro":       "alluvial_sungai",
    "balen|bojonegoro":            "alluvial_sungai",
    "kapas|bojonegoro":            "alluvial_sungai",
    "dander|bojonegoro":           "grumusol_ekspansif",
    "ngasem|bojonegoro":           "grumusol_ekspansif",
    "kalitidu|bojonegoro":         "alluvial_sungai",
    "margomulyo|bojonegoro":       "litosol_berbatu",
    "gayam|bojonegoro":            "grumusol_ekspansif",
    "kedungadem|bojonegoro":       "grumusol_ekspansif",
    "sukosewu|bojonegoro":         "alluvial_sungai",

    # =========================================================================
    # KABUPATEN NGAWI
    # =========================================================================
    "ngawi|ngawi":                 "grumusol_ekspansif",
    "paron|ngawi":                 "grumusol_ekspansif",
    "geneng|ngawi":                "grumusol_ekspansif",
    "gerih|ngawi":                 "alluvial_sungai",
    "padas|ngawi":                 "alluvial_sungai",
    "pangkur|ngawi":               "alluvial_sungai",
    "karangjati|ngawi":            "grumusol_ekspansif",
    "bringin|ngawi":               "grumusol_ekspansif",
    "pitu|ngawi":                  "alluvial_sungai",
    "widodaren|ngawi":             "grumusol_ekspansif",
    "mantingan|ngawi":             "alluvial_sungai",
    "karanganyar|ngawi":           "alluvial_sungai",
    "kedunggalar|ngawi":           "alluvial_sungai",
    "sine|ngawi":                  "latosol_merah",
    "ngrambe|ngawi":               "latosol_merah",
    "jogorogo|ngawi":              "latosol_merah",
    "kendal|ngawi":                "latosol_merah",
    "kwadungan|ngawi":             "grumusol_ekspansif",
    "kasreman|ngawi":              "alluvial_sungai",

    # =========================================================================
    # KABUPATEN MADIUN
    # =========================================================================
    "madiun|madiun":               "alluvial_sungai",
    "balerejo|madiun":             "alluvial_sungai",
    "geger|madiun":                "grumusol_ekspansif",
    "dagangan|madiun":             "grumusol_ekspansif",
    "wungu|madiun":                "latosol_merah",
    "kare|madiun":                 "andosol_vulkanik",
    "gemarang|madiun":             "latosol_merah",
    "saradan|madiun":              "latosol_merah",
    "pilangkenceng|madiun":        "alluvial_sungai",
    "mejayan|madiun":              "alluvial_sungai",
    "wonoasri|madiun":             "alluvial_sungai",
    "jiwan|madiun":                "alluvial_sungai",
    "sawahan|madiun":              "latosol_merah",
    "dolopo|madiun":               "latosol_merah",
    "kebonsari|madiun":            "alluvial_sungai",

    # =========================================================================
    # KOTA MADIUN
    # =========================================================================
    "manguharjo|kota madiun":      "alluvial_sungai",
    "taman|kota madiun":           "alluvial_sungai",
    "kartoharjo|kota madiun":      "alluvial_sungai",

    # =========================================================================
    # KABUPATEN MAGETAN
    # =========================================================================
    "magetan|magetan":             "andosol_vulkanik",
    "plaosan|magetan":             "andosol_vulkanik",
    "panekan|magetan":             "andosol_vulkanik",
    "sidorejo|magetan":            "andosol_vulkanik",
    "lembeyan|magetan":            "andosol_vulkanik",
    "takeran|magetan":             "vulkanik_sedang",
    "nguntoronadi|magetan":        "vulkanik_sedang",
    "kawedanan|magetan":           "vulkanik_sedang",
    "parang|magetan":              "latosol_merah",
    "barat|magetan":               "latosol_merah",
    "sukomoro|magetan":            "latosol_merah",
    "ngariboyo|magetan":           "latosol_merah",
    "karas|magetan":               "grumusol_ekspansif",
    "kartoharjo|magetan":          "grumusol_ekspansif",
    "maospati|magetan":            "alluvial_sungai",
    "karangrejo|magetan":          "alluvial_sungai",
    "bendo|magetan":               "alluvial_sungai",
    "karangmojo|magetan":          "latosol_merah",

    # =========================================================================
    # KABUPATEN PONOROGO
    # =========================================================================
    "ponorogo|ponorogo":           "alluvial_sungai",
    "babadan|ponorogo":            "alluvial_sungai",
    "jenangan|ponorogo":           "vulkanik_sedang",
    "ngebel|ponorogo":             "andosol_vulkanik",
    "pulung|ponorogo":             "andosol_vulkanik",
    "sooko|ponorogo":              "latosol_merah",
    "pudak|ponorogo":              "andosol_vulkanik",
    "bungkal|ponorogo":            "latosol_merah",
    "sambit|ponorogo":             "litosol_berbatu",
    "sawoo|ponorogo":              "litosol_berbatu",
    "slahung|ponorogo":            "latosol_merah",
    "ngrayun|ponorogo":            "litosol_berbatu",
    "badegan|ponorogo":            "latosol_merah",
    "sampung|ponorogo":            "latosol_merah",
    "sukorejo|ponorogo":           "alluvial_sungai",
    "kauman|ponorogo":             "alluvial_sungai",
    "jambon|ponorogo":             "latosol_merah",
    "balong|ponorogo":             "latosol_merah",
    "mlarak|ponorogo":             "alluvial_sungai",
    "siman|ponorogo":              "alluvial_sungai",
    "jetis|ponorogo":              "alluvial_sungai",

    # =========================================================================
    # KABUPATEN PACITAN
    # =========================================================================
    "pacitan|pacitan":             "litosol_berbatu",
    "sudimoro|pacitan":            "litosol_berbatu",
    "ngadirojo|pacitan":           "litosol_berbatu",
    "tulakan|pacitan":             "litosol_berbatu",
    "tegalombo|pacitan":           "litosol_berbatu",
    "arjosari|pacitan":            "litosol_berbatu",
    "nawangan|pacitan":            "litosol_berbatu",
    "bandar|pacitan":              "litosol_berbatu",
    "pringkuku|pacitan":           "litosol_berbatu",
    "donorojo|pacitan":            "litosol_berbatu",
    "punung|pacitan":              "litosol_berbatu",
    "kebonagung|pacitan":          "litosol_berbatu",

    # =========================================================================
    # KABUPATEN TRENGGALEK
    # =========================================================================
    "trenggalek|trenggalek":       "litosol_berbatu",
    "pogalan|trenggalek":          "alluvial_sungai",
    "durenan|trenggalek":          "alluvial_sungai",
    "gandusari|trenggalek":        "latosol_merah",
    "kampak|trenggalek":           "litosol_berbatu",
    "dongko|trenggalek":           "litosol_berbatu",
    "pule|trenggalek":             "litosol_berbatu",
    "bendungan|trenggalek":        "andosol_vulkanik",
    "watulimo|trenggalek":         "latosol_merah",
    "munjungan|trenggalek":        "litosol_berbatu",
    "panggul|trenggalek":          "litosol_berbatu",
    "karangan|trenggalek":         "alluvial_sungai",
    "tugu|trenggalek":             "litosol_berbatu",
    "suruh|trenggalek":            "latosol_merah",

    # =========================================================================
    # KABUPATEN TULUNGAGUNG
    # =========================================================================
    "tulungagung|tulungagung":     "alluvial_sungai",
    "boyolangu|tulungagung":       "alluvial_sungai",
    "kedungwaru|tulungagung":      "alluvial_sungai",
    "ngantru|tulungagung":         "alluvial_sungai",
    "karangrejo|tulungagung":      "alluvial_sungai",
    "kauman|tulungagung":          "alluvial_sungai",
    "gondang|tulungagung":         "alluvial_sungai",
    "sumbergempol|tulungagung":    "alluvial_sungai",
    "ngunut|tulungagung":          "alluvial_sungai",
    "pucanglaban|tulungagung":     "litosol_berbatu",
    "rejotangan|tulungagung":      "latosol_merah",
    "campurdarat|tulungagung":     "mediteran_kapur",
    "tanggunggunung|tulungagung":  "litosol_berbatu",
    "kalidawir|tulungagung":       "latosol_merah",
    "besuki|tulungagung":          "litosol_berbatu",
    "bandung|tulungagung":         "litosol_berbatu",
    "pakel|tulungagung":           "latosol_merah",
    "sendang|tulungagung":         "andosol_vulkanik",
    "pagerwojo|tulungagung":       "andosol_vulkanik",

    # =========================================================================
    # KABUPATEN BLITAR
    # =========================================================================
    "blitar|blitar":               "alluvial_sungai",
    "sanankulon|blitar":           "alluvial_sungai",
    "kanigoro|blitar":             "alluvial_sungai",
    "talun|blitar":                "vulkanik_sedang",
    "selopuro|blitar":             "alluvial_sungai",
    "kesamben|blitar":             "alluvial_sungai",
    "selorejo|blitar":             "vulkanik_sedang",
    "doko|blitar":                 "vulkanik_sedang",
    "wlingi|blitar":               "vulkanik_sedang",
    "gandusari|blitar":            "andosol_vulkanik",
    "garum|blitar":                "alluvial_sungai",
    "nglegok|blitar":              "vulkanik_sedang",
    "ponggok|blitar":              "alluvial_sungai",
    "srengat|blitar":              "alluvial_sungai",
    "wonodadi|blitar":             "alluvial_sungai",
    "udanawu|blitar":              "alluvial_sungai",
    "sutojayan|blitar":            "litosol_berbatu",
    "kademangan|blitar":           "litosol_berbatu",
    "panggungrejo|blitar":         "litosol_berbatu",
    "wonotirto|blitar":            "litosol_berbatu",
    "bakung|blitar":               "litosol_berbatu",
    "binangun|blitar":             "litosol_berbatu",

    # =========================================================================
    # KOTA BLITAR
    # =========================================================================
    "kepanjenkidul|kota blitar":   "alluvial_sungai",
    "sukorejo|kota blitar":        "alluvial_sungai",
    "sananwetan|kota blitar":      "alluvial_sungai",

    # =========================================================================
    # KABUPATEN KEDIRI
    # =========================================================================
    "kediri|kediri":               "alluvial_sungai",
    "gampengrejo|kediri":          "alluvial_sungai",
    "grogol|kediri":               "alluvial_sungai",
    "banyakan|kediri":             "litosol_berbatu",
    "semen|kediri":                "litosol_berbatu",
    "mojo|kediri":                 "latosol_merah",
    "kras|kediri":                 "latosol_merah",
    "kandat|kediri":               "latosol_merah",
    "wates|kediri":                "latosol_merah",
    "ngancar|kediri":              "andosol_vulkanik",
    "plosoklaten|kediri":          "vulkanik_sedang",
    "gurah|kediri":                "alluvial_sungai",
    "puncu|kediri":                "andosol_vulkanik",
    "kepung|kediri":               "andosol_vulkanik",
    "kandangan|kediri":            "vulkanik_sedang",
    "pare|kediri":                 "alluvial_sungai",
    "badas|kediri":                "alluvial_sungai",
    "kunjang|kediri":              "alluvial_sungai",
    "plemahan|kediri":             "alluvial_sungai",
    "purwoasri|kediri":            "alluvial_sungai",
    "papar|kediri":                "alluvial_sungai",
    "pagu|kediri":                 "alluvial_sungai",
    "tarokan|kediri":              "latosol_merah",
    "ngadiluwih|kediri":           "alluvial_sungai",
    "ringinrejo|kediri":           "alluvial_sungai",
    "kayenkidul|kediri":           "alluvial_sungai",

    # =========================================================================
    # KOTA KEDIRI
    # =========================================================================
    "kota|kota kediri":            "alluvial_sungai",
    "pesantren|kota kediri":       "alluvial_sungai",
    "mojoroto|kota kediri":        "alluvial_sungai",

    # =========================================================================
    # KABUPATEN NGANJUK
    # =========================================================================
    "nganjuk|nganjuk":             "alluvial_sungai",
    "bagor|nganjuk":               "alluvial_sungai",
    "ngluyu|nganjuk":              "grumusol_ekspansif",
    "rejoso|nganjuk":              "alluvial_sungai",
    "gondang|nganjuk":             "grumusol_ekspansif",
    "sukomoro|nganjuk":            "grumusol_ekspansif",
    "ngetos|nganjuk":              "andosol_vulkanik",
    "loceret|nganjuk":             "andosol_vulkanik",
    "sawahan|nganjuk":             "andosol_vulkanik",
    "berbek|nganjuk":              "latosol_merah",
    "baron|nganjuk":               "alluvial_sungai",
    "tanjunganom|nganjuk":         "alluvial_sungai",
    "prambon|nganjuk":             "alluvial_sungai",
    "kertosono|nganjuk":           "alluvial_sungai",
    "patianrowo|nganjuk":          "alluvial_sungai",
    "lengkong|nganjuk":            "grumusol_ekspansif",
    "jatikalen|nganjuk":           "grumusol_ekspansif",
    "ngronggot|nganjuk":           "alluvial_sungai",
    "pace|nganjuk":                "alluvial_sungai",
    "wilangan|nganjuk":            "grumusol_ekspansif",

    # =========================================================================
    # KABUPATEN MALANG
    # =========================================================================
    "kepanjen|malang":             "alluvial_sungai",
    "bululawang|malang":           "alluvial_sungai",
    "gondanglegi|malang":          "alluvial_sungai",
    "pagelaran|malang":            "alluvial_sungai",
    "turen|malang":                "alluvial_sungai",
    "dampit|malang":               "latosol_merah",
    "tirtoyudo|malang":            "litosol_berbatu",
    "ampelgading|malang":          "litosol_berbatu",
    "poncokusumo|malang":          "andosol_vulkanik",
    "jabung|malang":               "andosol_vulkanik",
    "pakis|malang":                "andosol_vulkanik",
    "lawang|malang":               "vulkanik_sedang",
    "singosari|malang":            "vulkanik_sedang",
    "karangploso|malang":          "vulkanik_sedang",
    "dau|malang":                  "andosol_vulkanik",
    "pujon|malang":                "andosol_vulkanik",
    "ngantang|malang":             "andosol_vulkanik",
    "kasembon|malang":             "andosol_vulkanik",
    "wagir|malang":                "vulkanik_sedang",
    "pakisaji|malang":             "alluvial_sungai",
    "ngajum|malang":               "latosol_merah",
    "wonosari|malang":             "latosol_merah",
    "kalipare|malang":             "litosol_berbatu",
    "donomulyo|malang":            "litosol_berbatu",
    "bantur|malang":               "litosol_berbatu",
    "gedangan|malang":             "litosol_berbatu",
    "sumbermanjing|malang":        "litosol_berbatu",
    "pagak|malang":                "litosol_berbatu",
    "wajak|malang":                "latosol_merah",
    "tajinan|malang":              "alluvial_sungai",
    "buring|malang":               "vulkanik_sedang",
    "kedungkandang|malang":        "vulkanik_sedang",
    "sukun|malang":                "vulkanik_sedang",

    # =========================================================================
    # KOTA MALANG
    # =========================================================================
    "blimbing|kota malang":        "vulkanik_sedang",
    "lowokwaru|kota malang":       "vulkanik_sedang",
    "klojen|kota malang":          "vulkanik_sedang",
    "sukun|kota malang":           "vulkanik_sedang",
    "kedungkandang|kota malang":   "vulkanik_sedang",

    # =========================================================================
    # KOTA BATU
    # =========================================================================
    "batu|kota batu":              "andosol_vulkanik",
    "junrejo|kota batu":           "andosol_vulkanik",
    "bumiaji|kota batu":           "andosol_vulkanik",

    # =========================================================================
    # KABUPATEN PASURUAN
    # =========================================================================
    "bangil|pasuruan":             "alluvial_pantai",
    "beji|pasuruan":               "vulkanik_sedang",
    "kraton|pasuruan":             "alluvial_pantai",
    "rejoso|pasuruan":             "alluvial_pantai",
    "lekok|pasuruan":              "alluvial_pantai",
    "nguling|pasuruan":            "alluvial_pantai",
    "grati|pasuruan":              "alluvial_pantai",
    "winongan|pasuruan":           "alluvial_sungai",
    "gondangwetan|pasuruan":       "alluvial_sungai",
    "rembang|pasuruan":            "alluvial_sungai",
    "sukorejo|pasuruan":           "alluvial_sungai",
    "pandaan|pasuruan":            "vulkanik_sedang",
    "gempol|pasuruan":             "vulkanik_sedang",
    "bangsal|pasuruan":            "alluvial_sungai",
    "purwodadi|pasuruan":          "vulkanik_sedang",
    "tutur|pasuruan":              "andosol_vulkanik",
    "puspo|pasuruan":              "andosol_vulkanik",
    "tosari|pasuruan":             "andosol_vulkanik",
    "lumbang|pasuruan":            "andosol_vulkanik",
    "pasrepan|pasuruan":           "latosol_merah",
    "kejayan|pasuruan":            "alluvial_sungai",
    "wonorejo|pasuruan":           "alluvial_sungai",
    "pohjentrek|pasuruan":         "alluvial_pantai",
    "prigen|pasuruan":             "andosol_vulkanik",

    # =========================================================================
    # KOTA PASURUAN
    # =========================================================================
    "panggungrejo|kota pasuruan":  "alluvial_pantai",
    "purworejo|kota pasuruan":     "alluvial_pantai",
    "bugul kidul|kota pasuruan":   "alluvial_pantai",
    "gadingrejo|kota pasuruan":    "alluvial_pantai",

    # =========================================================================
    # KABUPATEN PROBOLINGGO
    # =========================================================================
    "kraksaan|probolinggo":        "alluvial_pantai",
    "pajarakan|probolinggo":       "alluvial_pantai",
    "maron|probolinggo":           "alluvial_pantai",
    "gending|probolinggo":         "alluvial_pantai",
    "dringu|probolinggo":          "alluvial_pantai",
    "tongas|probolinggo":          "alluvial_pantai",
    "sumberasih|probolinggo":      "alluvial_pantai",
    "wonomerto|probolinggo":       "alluvial_sungai",
    "bantaran|probolinggo":        "alluvial_sungai",
    "leces|probolinggo":           "vulkanik_sedang",
    "tegalsiwalan|probolinggo":    "vulkanik_sedang",
    "banyuanyar|probolinggo":      "vulkanik_sedang",
    "kotaanyar|probolinggo":       "latosol_merah",
    "paiton|probolinggo":          "alluvial_pantai",
    "besuk|probolinggo":           "alluvial_sungai",
    "tiris|probolinggo":           "latosol_merah",
    "gading|probolinggo":          "andosol_vulkanik",
    "sukapura|probolinggo":        "andosol_vulkanik",
    "sumber|probolinggo":          "andosol_vulkanik",
    "kuripan|probolinggo":         "latosol_merah",
    "krucil|probolinggo":          "andosol_vulkanik",
    "pakuniran|probolinggo":       "latosol_merah",
    "wates|probolinggo":           "latosol_merah",
    "jorongan|probolinggo":        "latosol_merah",

    # =========================================================================
    # KOTA PROBOLINGGO
    # =========================================================================
    "wonoasih|kota probolinggo":   "alluvial_pantai",
    "mayangan|kota probolinggo":   "alluvial_pantai",
    "kanigaran|kota probolinggo":  "alluvial_pantai",
    "kedopok|kota probolinggo":    "alluvial_pantai",
    "kademangan|kota probolinggo": "alluvial_pantai",

    # =========================================================================
    # KABUPATEN LUMAJANG
    # =========================================================================
    "lumajang|lumajang":           "alluvial_sungai",
    "sukodono|lumajang":           "alluvial_sungai",
    "yosowilangun|lumajang":       "alluvial_pantai",
    "tekung|lumajang":             "alluvial_sungai",
    "kunir|lumajang":              "alluvial_sungai",
    "rowokangkung|lumajang":       "alluvial_sungai",
    "jatiroto|lumajang":           "alluvial_sungai",
    "randuagung|lumajang":         "latosol_merah",
    "sumbersuko|lumajang":         "vulkanik_sedang",
    "tempeh|lumajang":             "alluvial_sungai",
    "pasirian|lumajang":           "alluvial_pantai",
    "candipuro|lumajang":          "andosol_vulkanik",
    "pronojiwo|lumajang":          "andosol_vulkanik",
    "senduro|lumajang":            "andosol_vulkanik",
    "pasrujambe|lumajang":         "andosol_vulkanik",
    "gucialit|lumajang":           "andosol_vulkanik",
    "padang|lumajang":             "latosol_merah",
    "klakah|lumajang":             "andosol_vulkanik",
    "kedungjajang|lumajang":       "latosol_merah",
    "tempursari|lumajang":         "litosol_berbatu",
    "pisang|lumajang":             "alluvial_sungai",

    # =========================================================================
    # KABUPATEN JEMBER
    # =========================================================================
    "kaliwates|jember":            "alluvial_sungai",
    "sumbersari|jember":           "alluvial_sungai",
    "patrang|jember":              "alluvial_sungai",
    "ajung|jember":                "latosol_merah",
    "rambipuji|jember":            "latosol_merah",
    "balung|jember":               "latosol_merah",
    "umbulsari|jember":            "latosol_merah",
    "semboro|jember":              "alluvial_sungai",
    "jombang|jember":              "alluvial_sungai",
    "sumberbaru|jember":           "latosol_merah",
    "tanggul|jember":              "andosol_vulkanik",
    "bangsalsari|jember":          "latosol_merah",
    "panti|jember":                "andosol_vulkanik",
    "sukorambi|jember":            "andosol_vulkanik",
    "arjasa|jember":               "andosol_vulkanik",
    "pakusari|jember":             "latosol_merah",
    "kalisat|jember":              "latosol_merah",
    "ledokombo|jember":            "latosol_merah",
    "sumberjambe|jember":          "andosol_vulkanik",
    "sukowono|jember":             "latosol_merah",
    "jelbuk|jember":               "latosol_merah",
    "karanganyar|jember":          "latosol_merah",
    "mumbulsari|jember":           "latosol_merah",
    "tempurejo|jember":            "litosol_berbatu",
    "silo|jember":                 "latosol_merah",
    "mayang|jember":               "latosol_merah",
    "jenggawah|jember":            "alluvial_sungai",
    "ambulu|jember":               "alluvial_pantai",
    "wuluhan|jember":              "alluvial_pantai",
    "puger|jember":                "alluvial_pantai",
    "gumukmas|jember":             "alluvial_pantai",

    # =========================================================================
    # KABUPATEN SITUBONDO
    # =========================================================================
    "situbondo|situbondo":         "alluvial_pantai",
    "panarukan|situbondo":         "alluvial_pantai",
    "mangaran|situbondo":          "alluvial_pantai",
    "kapongan|situbondo":          "alluvial_pantai",
    "arjasa|situbondo":            "alluvial_pantai",
    "jangkar|situbondo":           "alluvial_pantai",
    "asembagus|situbondo":         "alluvial_pantai",
    "banyuputih|situbondo":        "mediteran_kapur",
    "besuki|situbondo":            "alluvial_pantai",
    "suboh|situbondo":             "alluvial_pantai",
    "mlandingan|situbondo":        "latosol_merah",
    "bungatan|situbondo":          "latosol_merah",
    "kendit|situbondo":            "litosol_berbatu",
    "panji|situbondo":             "alluvial_pantai",
    "banyuglugur|situbondo":       "litosol_berbatu",
    "jatibanteng|situbondo":       "litosol_berbatu",
    "sumbermalang|situbondo":      "andosol_vulkanik",

    # =========================================================================
    # KABUPATEN BONDOWOSO
    # =========================================================================
    "bondowoso|bondowoso":         "latosol_merah",
    "tegalampel|bondowoso":        "latosol_merah",
    "tenggarang|bondowoso":        "alluvial_sungai",
    "wonosari|bondowoso":          "latosol_merah",
    "grujugan|bondowoso":          "latosol_merah",
    "maesan|bondowoso":            "andosol_vulkanik",
    "binakal|bondowoso":           "litosol_berbatu",
    "pakem|bondowoso":             "litosol_berbatu",
    "wringin|bondowoso":           "latosol_merah",
    "tapen|bondowoso":             "latosol_merah",
    "botolinggo|bondowoso":        "latosol_merah",
    "prajekan|bondowoso":          "latosol_merah",
    "cermee|bondowoso":            "litosol_berbatu",
    "jambesari|bondowoso":         "latosol_merah",
    "pujer|bondowoso":             "latosol_merah",
    "tlogosari|bondowoso":         "andosol_vulkanik",
    "sukosari|bondowoso":          "andosol_vulkanik",
    "sumberwringin|bondowoso":     "andosol_vulkanik",
    "sempol|bondowoso":            "andosol_vulkanik",
    "klabang|bondowoso":           "latosol_merah",
    "cerme|bondowoso":             "litosol_berbatu",
    "tamanan|bondowoso":           "latosol_merah",
    "ijen|bondowoso":              "andosol_vulkanik",

    # =========================================================================
    # KABUPATEN BANYUWANGI
    # =========================================================================
    "banyuwangi|banyuwangi":       "alluvial_pantai",
    "giri|banyuwangi":             "alluvial_pantai",
    "kabat|banyuwangi":            "alluvial_sungai",
    "rogojampi|banyuwangi":        "alluvial_pantai",
    "songgon|banyuwangi":          "andosol_vulkanik",
    "singojuruh|banyuwangi":       "latosol_merah",
    "srono|banyuwangi":            "alluvial_sungai",
    "muncar|banyuwangi":           "regosol_pantai",
    "tegaldlimo|banyuwangi":       "regosol_pantai",
    "purwoharjo|banyuwangi":       "regosol_pantai",
    "bangorejo|banyuwangi":        "alluvial_sungai",
    "gambiran|banyuwangi":         "alluvial_sungai",
    "tegalsari|banyuwangi":        "latosol_merah",
    "glenmore|banyuwangi":         "latosol_merah",
    "kalibaru|banyuwangi":         "andosol_vulkanik",
    "genteng|banyuwangi":          "alluvial_sungai",
    "sempu|banyuwangi":            "latosol_merah",
    "cluring|banyuwangi":          "alluvial_sungai",
    "pesanggaran|banyuwangi":      "litosol_berbatu",
    "siliragung|banyuwangi":       "litosol_berbatu",
    "wongsorejo|banyuwangi":       "mediteran_kapur",
    "licin|banyuwangi":            "andosol_vulkanik",
    "glagah|banyuwangi":           "andosol_vulkanik",
    "blimbingsari|banyuwangi":     "regosol_pantai",
    "kalipuro|banyuwangi":         "alluvial_pantai",

    # =========================================================================
    # KABUPATEN SAMPANG
    # =========================================================================
    "sampang|sampang":             "madura_lempung",
    "camplong|sampang":            "madura_lempung",
    "omben|sampang":               "madura_lempung",
    "kedungdung|sampang":          "madura_lempung",
    "jrengik|sampang":             "madura_lempung",
    "tambelangan|sampang":         "madura_lempung",
    "banyuates|sampang":           "madura_lempung",
    "robatal|sampang":             "madura_lempung",
    "sokobanah|sampang":           "madura_lempung",
    "torjun|sampang":              "madura_lempung",
    "sreseh|sampang":              "alluvial_pantai",
    "pangarengan|sampang":         "alluvial_pantai",
    "ketapang|sampang":            "madura_lempung",
    "karang penang|sampang":       "madura_lempung",

    # =========================================================================
    # KABUPATEN PAMEKASAN
    # =========================================================================
    "pamekasan|pamekasan":         "madura_lempung",
    "pademawu|pamekasan":          "alluvial_pantai",
    "galis|pamekasan":             "madura_lempung",
    "larangan|pamekasan":          "madura_lempung",
    "batumarmar|pamekasan":        "madura_lempung",
    "pakong|pamekasan":            "madura_lempung",
    "waru|pamekasan":              "madura_lempung",
    "pegantenan|pamekasan":        "madura_lempung",
    "kadur|pamekasan":             "madura_lempung",
    "pasean|pamekasan":            "madura_lempung",
    "tlanakan|pamekasan":          "alluvial_pantai",
    "proppo|pamekasan":            "madura_lempung",
    "palengaan|pamekasan":         "madura_lempung",

    # =========================================================================
    # KABUPATEN SUMENEP
    # =========================================================================
    "kota sumenep|sumenep":        "madura_lempung",
    "batuan|sumenep":              "madura_lempung",
    "lenteng|sumenep":             "madura_lempung",
    "ganding|sumenep":             "madura_lempung",
    "guluk-guluk|sumenep":         "madura_lempung",
    "pasongsongan|sumenep":        "madura_lempung",
    "ambunten|sumenep":            "alluvial_pantai",
    "rubaru|sumenep":              "madura_lempung",
    "dasuk|sumenep":               "madura_lempung",
    "manding|sumenep":             "madura_lempung",
    "batuputih|sumenep":           "mediteran_kapur",
    "gapura|sumenep":              "mediteran_kapur",
    "batang-batang|sumenep":       "mediteran_kapur",
    "dungkek|sumenep":             "alluvial_pantai",
    "nonggunong|sumenep":          "regosol_pantai",
    "gayam|sumenep":               "regosol_pantai",
    "raas|sumenep":                "regosol_pantai",
    "arjasa|sumenep":              "regosol_pantai",
    "kangayan|sumenep":            "regosol_pantai",
    "masalembu|sumenep":           "regosol_pantai",
    "bluto|sumenep":               "madura_lempung",
    "saronggi|sumenep":            "madura_lempung",
    "giligenting|sumenep":         "regosol_pantai",
    "talango|sumenep":             "alluvial_pantai",
    "kalianget|sumenep":           "alluvial_pantai",
    "pragaan|sumenep":             "madura_lempung",
    "sapeken|sumenep":             "regosol_pantai",

    # =========================================================================
    # KABUPATEN BANGKALAN
    # =========================================================================
    "bangkalan|bangkalan":         "madura_lempung",
    "burneh|bangkalan":            "madura_lempung",
    "arosbaya|bangkalan":          "mediteran_kapur",
    "geger|bangkalan":             "madura_lempung",
    "klampis|bangkalan":           "madura_lempung",
    "sepulu|bangkalan":            "alluvial_pantai",
    "tanjung bumi|bangkalan":      "mediteran_kapur",
    "kokop|bangkalan":             "madura_lempung",
    "kwanyar|bangkalan":           "alluvial_pantai",
    "labang|bangkalan":            "alluvial_pantai",
    "kamal|bangkalan":             "alluvial_pantai",
    "modung|bangkalan":            "madura_lempung",
    "blega|bangkalan":             "madura_lempung",
    "konang|bangkalan":            "madura_lempung",
    "galis|bangkalan":             "madura_lempung",
    "tanah merah|bangkalan":       "madura_lempung",
    "tragah|bangkalan":            "madura_lempung",
    "socah|bangkalan":             "alluvial_pantai",
}

# =============================================================================
# DATABASE JAKARTA
# =============================================================================

DB_JAKARTA = {
    "penjaringan|jakarta utara":      "urban_jakarta_utara",
    "pademangan|jakarta utara":       "urban_jakarta_utara",
    "tanjung priok|jakarta utara":    "urban_jakarta_utara",
    "koja|jakarta utara":             "urban_jakarta_utara",
    "kelapa gading|jakarta utara":    "urban_jakarta_utara",
    "cilincing|jakarta utara":        "urban_jakarta_utara",
    "gambir|jakarta pusat":           "alluvial_sungai",
    "sawah besar|jakarta pusat":      "alluvial_sungai",
    "kemayoran|jakarta pusat":        "alluvial_sungai",
    "senen|jakarta pusat":            "alluvial_sungai",
    "cempaka putih|jakarta pusat":    "alluvial_sungai",
    "menteng|jakarta pusat":          "alluvial_sungai",
    "tanah abang|jakarta pusat":      "alluvial_sungai",
    "johar baru|jakarta pusat":       "alluvial_sungai",
    "tamansari|jakarta barat":        "alluvial_sungai",
    "tambora|jakarta barat":          "alluvial_sungai",
    "palmerah|jakarta barat":         "alluvial_sungai",
    "grogol petamburan|jakarta barat": "alluvial_sungai",
    "cengkareng|jakarta barat":       "alluvial_sungai",
    "kalideres|jakarta barat":        "alluvial_sungai",
    "kembangan|jakarta barat":        "alluvial_sungai",
    "kebon jeruk|jakarta barat":      "alluvial_sungai",
    "matraman|jakarta timur":         "alluvial_sungai",
    "pulo gadung|jakarta timur":      "alluvial_sungai",
    "jatinegara|jakarta timur":       "alluvial_sungai",
    "kramat jati|jakarta timur":      "alluvial_sungai",
    "pasar rebo|jakarta timur":       "urban_jakarta_selatan",
    "ciracas|jakarta timur":          "urban_jakarta_selatan",
    "cipayung|jakarta timur":         "urban_jakarta_selatan",
    "makasar|jakarta timur":          "alluvial_sungai",
    "duren sawit|jakarta timur":      "alluvial_sungai",
    "cakung|jakarta timur":           "alluvial_pantai",
    "cililitan|jakarta timur":        "alluvial_sungai",
    "tebet|jakarta selatan":          "urban_jakarta_selatan",
    "setiabudi|jakarta selatan":      "urban_jakarta_selatan",
    "mampang prapatan|jakarta selatan": "urban_jakarta_selatan",
    "pasar minggu|jakarta selatan":   "urban_jakarta_selatan",
    "kebayoran lama|jakarta selatan": "urban_jakarta_selatan",
    "kebayoran baru|jakarta selatan": "urban_jakarta_selatan",
    "pesanggrahan|jakarta selatan":   "urban_jakarta_selatan",
    "cilandak|jakarta selatan":       "urban_jakarta_selatan",
    "jagakarsa|jakarta selatan":      "urban_jakarta_selatan",
    "pancoran|jakarta selatan":       "urban_jakarta_selatan",
}

# Gabung semua DB
DB.update(DB_JAKARTA)

# =============================================================================
# FUNGSI LOOKUP
# =============================================================================


# =============================================================================
# LOOKUP BY KABUPATEN — fallback terakhir kalau nama kecamatan tidak ketemu
# Return zona yang paling dominan/representatif untuk kabupaten tsb
# =============================================================================

KABUPATEN_DEFAULT = {
    # Jawa Timur
    "nganjuk":          "alluvial_sungai",
    "bojonegoro":       "grumusol_ekspansif",
    "lamongan":         "grumusol_ekspansif",
    "tuban":            "mediteran_kapur",
    "gresik":           "alluvial_pantai",
    "sidoarjo":         "alluvial_pantai",
    "surabaya":         "alluvial_sungai",
    "mojokerto":        "alluvial_sungai",
    "jombang":          "alluvial_sungai",
    "madiun":           "alluvial_sungai",
    "magetan":          "andosol_vulkanik",
    "ngawi":            "grumusol_ekspansif",
    "ponorogo":         "latosol_merah",
    "pacitan":          "litosol_berbatu",
    "trenggalek":       "litosol_berbatu",
    "tulungagung":      "alluvial_sungai",
    "blitar":           "alluvial_sungai",
    "kediri":           "alluvial_sungai",
    "malang":           "vulkanik_sedang",
    "pasuruan":         "alluvial_sungai",
    "probolinggo":      "alluvial_pantai",
    "lumajang":         "alluvial_sungai",
    "jember":           "latosol_merah",
    "situbondo":        "alluvial_pantai",
    "bondowoso":        "latosol_merah",
    "banyuwangi":       "latosol_merah",
    "sampang":          "madura_lempung",
    "pamekasan":        "madura_lempung",
    "sumenep":          "madura_lempung",
    "bangkalan":        "madura_lempung",
    # Jakarta
    "jakarta utara":    "urban_jakarta_utara",
    "jakarta pusat":    "alluvial_sungai",
    "jakarta barat":    "alluvial_sungai",
    "jakarta timur":    "alluvial_sungai",
    "jakarta selatan":  "urban_jakarta_selatan",
}


def lookup_by_kabupaten(state_district: str) -> dict | None:
    """Fallback terakhir — return profil default kabupaten."""
    kab = state_district.lower().strip()
    for prefix in ["kabupaten ", "kota ", "kab. ", "kab "]:
        kab = kab.replace(prefix, "")
    zona_key = KABUPATEN_DEFAULT.get(kab)
    if zona_key is None:
        return None
    data = ZONA[zona_key].copy()
    data["cbr_est"]  = (data["cbr_min"] + data["cbr_max"]) / 2
    data["sumber"]   = "Referensi default kabupaten (fallback level 3)"
    data["zona_key"] = zona_key
    return data


def lookup_fallback(village: str, state_district: str = "", state: str = "") -> dict | None:
    """
    Cari data fallback — 4 level:
    1. Exact: kecamatan|kabupaten
    2. Scan: nama kecamatan saja (match pertama)
    3. Default kabupaten dari state_district
    4. Coba village sebagai nama kabupaten langsung
    """
    kec = village.lower().strip() if village else ""
    kab = state_district.lower().strip() if state_district else ""
    for prefix in ["kabupaten ", "kota ", "kab. ", "kab "]:
        kab = kab.replace(prefix, "")

    # Level 1: exact match kecamatan|kabupaten
    zona_key = DB.get(f"{kec}|{kab}")

    # Level 2: scan kecamatan tanpa kabupaten
    if zona_key is None:
        for k, v in DB.items():
            if k.split("|")[0] == kec:
                zona_key = v
                break

    if zona_key is not None:
        data = ZONA[zona_key].copy()
        data["cbr_est"]  = (data["cbr_min"] + data["cbr_max"]) / 2
        data["sumber"]   = "Literatur geoteknik (fallback)"
        data["zona_key"] = zona_key
        return data

    # Level 3: default kabupaten dari state_district
    result = lookup_by_kabupaten(state_district)
    if result is not None:
        return result

    # Level 4: coba village sebagai nama kabupaten/kota langsung
    # (untuk kasus Nominatim return nama kota besar di field local, dist kosong)
    result = lookup_by_kabupaten(village)
    if result is not None:
        return result

    return None


def get_cbr_fallback(village: str, state_district: str = "", state: str = "") -> float | None:
    data = lookup_fallback(village, state_district, state)
    return data["cbr_est"] if data else None
