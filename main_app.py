from flask import Flask, render_template, request, redirect, jsonify
import os
import random
import math
import pandas as pd
import folium
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================
# VRP MOTORU (Web İçin Modifiye Edilmiş Hali)
# ==========================================
def vrp_motoru_calistir(excel_yolu):
    random.seed(42)

    df_merkez = pd.read_excel(excel_yolu, sheet_name="Merkez")
    df_suruculer = pd.read_excel(excel_yolu, sheet_name="Suruculer")
    df_musteriler = pd.read_excel(excel_yolu, sheet_name="Musteriler")

    merkez = {
        "id": df_merkez.iloc[0]["id"], "ad": df_merkez.iloc[0]["ad"],
        "lat": float(df_merkez.iloc[0]["lat"]), "lon": float(df_merkez.iloc[0]["lon"])
    }

    suruculer = {str(row["id"]): {
        "id": str(row["id"]), "ad": str(row["ad"]),
        "lat": float(row["lat"]), "lon": float(row["lon"]),
        "renk": str(row["renk"]), "kapasite": int(row["kapasite"])
    } for _, row in df_suruculer.iterrows()}

    musteriler = {str(row["id"]): {
        "id": str(row["id"]), "ad": str(row["ad"]),
        "lat": float(row["lat"]), "lon": float(row["lon"])
    } for _, row in df_musteriler.iterrows()}

    def haversine_mesafe(n1_id, n2_id):
        def get_koor(id_str):
            if id_str == "MERKEZ": return merkez
            return suruculer[id_str] if id_str.startswith("D") else musteriler[id_str]

        k1, k2 = get_koor(n1_id), get_koor(n2_id)
        R = 6371.0
        lat1, lon1 = math.radians(k1["lat"]), math.radians(k1["lon"])
        lat2, lon2 = math.radians(k2["lat"]), math.radians(k2["lon"])
        return round(R * 2 * math.atan2(math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2),
                                        math.sqrt(1 - (math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(
                                            lat2) * math.sin((lon2 - lon1) / 2) ** 2))), 2)

    def hızlı_rota_maliyeti(rota_listesi):
        return sum(haversine_mesafe(rota_listesi[i], rota_listesi[i + 1]) for i in range(len(rota_listesi) - 1))

    def osrm_geometri_ve_mesafe(rota_id_listesi):
        koordinatlar = []
        for n_id in rota_id_listesi:
            if n_id == "MERKEZ":
                koordinatlar.append(merkez)
            elif n_id.startswith("D"):
                koordinatlar.append(suruculer[n_id])
            else:
                koordinatlar.append(musteriler[n_id])
        koordinat_stringi = ";".join([f"{n['lon']},{n['lat']}" for n in koordinatlar])
        url = f"http://router.project-osrm.org/route/v1/driving/{koordinat_stringi}?overview=full&geometries=geojson"
        try:
            res = requests.get(url).json()
            if res["code"] == "Ok":
                return [[c[1], c[0]] for c in res["routes"][0]["geometry"]["coordinates"]], round(
                    res["routes"][0]["distance"] / 1000, 2)
        except:
            pass
        return None, hızlı_rota_maliyeti(rota_id_listesi)

    # --- Capacitated K-Means ---
    kalan_kapasiteler = {d_id: suruculer[d_id]["kapasite"] for d_id in suruculer.keys()}
    küme_merkezleri = {d_id: {"lat": suruculer[d_id]["lat"], "lon": suruculer[d_id]["lon"]} for d_id in
                       suruculer.keys()}
    musteri_kumeleri = {}

    for _ in range(10):
        kalan_kapasiteler = {d_id: suruculer[d_id]["kapasite"] for d_id in suruculer.keys()}
        musteri_kumeleri = {d_id: [] for d_id in suruculer.keys()}
        atanmamis_musteriler = list(musteriler.keys())

        while atanmamis_musteriler:
            en_yakin_m, en_yakin_d, en_kisa_mesafe = None, None, float('inf')
            for m_id in atanmamis_musteriler:
                m_lat, m_lon = musteriler[m_id]["lat"], musteriler[m_id]["lon"]
                for d_id, merkez_koor in küme_merkezleri.items():
                    if kalan_kapasiteler[d_id] <= 0: continue
                    mesafe = math.sqrt((m_lat - merkez_koor["lat"]) ** 2 + (m_lon - merkez_koor["lon"]) ** 2)
                    if mesafe < en_kisa_mesafe:
                        en_kisa_mesafe, en_yakin_m, en_yakin_d = mesafe, m_id, d_id
            if en_yakin_m:
                musteri_kumeleri[en_yakin_d].append(en_yakin_m)
                kalan_kapasiteler[en_yakin_d] -= 1
                atanmamis_musteriler.remove(en_yakin_m)
            else:
                break

        for d_id, m_listesi in musteri_kumeleri.items():
            if m_listesi:
                küme_merkezleri[d_id] = {
                    "lat": sum(musteriler[m]['lat'] for m in m_listesi) / len(m_listesi),
                    "lon": sum(musteriler[m]['lon'] for m in m_listesi) / len(m_listesi)
                }

    baslangic_rotalar = {}
    for d_id, m_listesi in musteri_kumeleri.items():
        sirali_rota = [d_id]
        kalan_m = list(m_listesi)
        while kalan_m:
            en_yakin = min(kalan_m, key=lambda m: haversine_mesafe(sirali_rota[-1], m))
            sirali_rota.append(en_yakin)
            kalan_m.remove(en_yakin)
        sirali_rota.append("MERKEZ")
        baslangic_rotalar[d_id] = sirali_rota

    # --- ALNS + 2-Opt ---
    en_iyi_alns_rotasi = {k: list(v) for k, v in baslangic_rotalar.items()}
    for _ in range(100):
        test_rotalar = {k: list(v) for k, v in en_iyi_alns_rotasi.items()}
        sokulenler = random.sample(list(musteriler.keys()), min(2, len(musteriler)))
        for s_id in test_rotalar.keys():
            test_rotalar[s_id] = [n for n in test_rotalar[s_id] if n not in sokulenler]
        for m_id in sokulenler:
            en_iyi_d, en_iyi_r, en_dusuk_m = None, None, float('inf')
            for d_id, rota in test_rotalar.items():
                if (len(rota) - 2) >= suruculer[d_id]["kapasite"]: continue
                for idx in range(1, len(rota)):
                    aday = rota[:]
                    aday.insert(idx, m_id)
                    maliyet = hızlı_rota_maliyeti(aday)
                    if maliyet < en_dusuk_m:
                        en_dusuk_m, en_iyi_d, en_iyi_r = maliyet, d_id, aday
            if en_iyi_d: test_rotalar[en_iyi_d] = en_iyi_r
        if hızlı_filo_maliyeti(test_rotalar) < hızlı_filo_maliyeti(en_iyi_alns_rotasi):
            en_iyi_alns_rotasi = {k: list(v) for k, v in test_rotalar.items()}

    def nihai_iki_opt(rota):
        en_iyi = list(rota)
        iyilesme = True
        while iyilesme:
            iyilesme = False
            for i in range(1, len(en_iyi) - 2):
                for j in range(i + 1, len(en_iyi) - 1):
                    yeni = en_iyi[:]
                    yeni[i:j + 1] = reversed(yeni[i:j + 1])
                    if hızlı_rota_maliyeti(yeni) < hızlı_rota_maliyeti(en_iyi):
                        en_iyi, iyilesme = yeni, True
        return en_iyi

    nihai_optimize_rotalar = {d_id: nihai_iki_opt(rota) for d_id, rota in en_iyi_alns_rotasi.items()}

    # --- Web İçin Veri Paketleme ---
    arac_detaylari = []
    eski_toplam_osrm = yeni_toplam_osrm = 0

    # Folium Haritası Oluşturma
    harita = folium.Map(location=[merkez["lat"], merkez["lon"]], zoom_start=11, tiles="OpenStreetMap")
    folium.Marker([merkez["lat"], merkez["lon"]], popup=merkez["ad"],
                  icon=folium.Icon(color="red", icon="star", prefix="fa")).add_to(harita)

    for d_id in baslangic_rotalar.keys():
        _, km_eski = osrm_geometri_ve_mesafe(baslangic_rotalar[d_id])
        geometri, km_yeni = osrm_geometri_ve_mesafe(nihai_optimize_rotalar[d_id])
        eski_toplam_osrm += km_eski
        yeni_toplam_osrm += km_yeni

        m_listesi = nihai_optimize_rotalar[d_id][1:-1]
        kapasite = suruculer[d_id]["kapasite"]

        arac_detaylari.append({
            "id": d_id,
            "sofor": suruculer[d_id]["ad"],
            "kapasite_doluluk": f"{len(m_listesi)} / {kapasite}",
            "yuzde_doluluk": round((len(m_listesi) / kapasite) * 100, 1),
            "eski_km": km_eski,
            "yeni_km": km_yeni,
            "tasarruf": round(km_eski - km_yeni, 2),
            "musteriler": m_listesi
        })

        # Haritaya Katman Ekleme
        renk = suruculer[d_id]["renk"]
        katman = folium.FeatureGroup(name=f"🚗 {suruculer[d_id]['ad']}")
        folium.Marker([suruculer[d_id]["lat"], suruculer[d_id]["lon"]], popup=f"{suruculer[d_id]['ad']} Başlangıç",
                      icon=folium.Icon(color=renk, icon="home", prefix="fa")).add_to(katman)

        for idx, m_id in enumerate(m_listesi, start=1):
            folium.Marker([musteriler[m_id]["lat"], musteriler[m_id]["lon"]], popup=f"<b>{m_id}</b><br>Sıra: {idx}",
                          icon=folium.Icon(color=renk, icon="user", prefix="fa")).add_to(katman)

        if geometri:
            folium.GeoJson(data={"type": "Feature",
                                 "geometry": {"type": "LineString", "coordinates": [[c[1], c[0]] for c in geometri]}},
                           style_function=lambda x, r=renk: {'color': r, 'weight': 5, 'opacity': 0.8}).add_to(katman)
        katman.add_to(harita)

    folium.LayerControl(collapsed=False).add_to(harita)
    harita_html = harita._repr_html_()

    ozet = {
        "toplam_musteri": sum(len(a["musteriler"]) for a in arac_detaylari),
        "eski_toplam": round(eski_toplam_osrm, 2),
        "yeni_toplam": round(yeni_toplam_osrm, 2),
        "toplam_tasarruf": round(eski_toplam_osrm - yeni_toplam_osrm, 2)
    }

    return arac_detaylari, ozet, harita_html


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files: return redirect(request.url)
        file = request.files['file']
        if file.filename == '': return redirect(request.url)

        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Algoritmayı çalıştır ve sonuçları al
            araclar, ozet, harita_html = vrp_motoru_calistir(filepath)
            return render_template('dashboard.html', araclar=araclar, ozet=ozet, harita_html=harita_html)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)