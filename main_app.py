from flask import Flask, render_template, request, redirect, jsonify
import os
import random
import math
import pandas as pd
import folium
import requests

app = Flask(__name__)


# ========================================================
# 1. EN GELİŞMİŞ ALGORİTMA MOTORU (Gerçek Yol Matrisi & Navigasyon Destekli)
# ========================================================
def vrp_motoru_calistir(excel_yolu):
    random.seed(42)

    # Excel sayfalarını yükleme
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

    # Tüm lokasyonları tek bir havuzda toplama
    tum_noktalar = {"MERKEZ": merkez}
    tum_noktalar.update(suruculer)
    tum_noktalar.update(musteriler)
    nokta_idleri = list(tum_noktalar.keys())

    # --- OSRM ÜZERİNDEN GERÇEK YOL MESAFE MATRİSİNİ OLUŞTURMA ---
    mesafe_matrisi = {id1: {id2: 0.0 for id2 in nokta_idleri} for id1 in nokta_idleri}

    koordinat_stringi = ";".join([f"{tum_noktalar[nid]['lon']},{tum_noktalar[nid]['lat']}" for nid in nokta_idleri])
    url = f"https://router.project-osrm.org/table/v1/driving/{koordinat_stringi}?annotations=distance"

    try:
        res = requests.get(url).json()
        if res["code"] == "Ok":
            matris_listesi = res["distances"]
            for i, id1 in enumerate(nokta_idleri):
                for j, id2 in enumerate(nokta_idleri):
                    mesafe_matrisi[id1][id2] = round(matris_listesi[i][j] / 1000, 2)
    except Exception as e:
        def haversine(k1, k2):
            R = 6371.0
            lat1, lon1 = math.radians(k1["lat"]), math.radians(k1["lon"])
            lat2, lon2 = math.radians(k2["lat"]), math.radians(k2["lon"])
            a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
            return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

        for id1 in nokta_idleri:
            for id2 in nokta_idleri:
                mesafe_matrisi[id1][id2] = haversine(tum_noktalar[id1], tum_noktalar[id2])

    # Rota ve Filo Maliyetlerini Gerçek Matris Üzerinden Hesaplayan Fonksiyonlar
    def rota_gercek_maliyeti(rota_listesi):
        return sum(mesafe_matrisi[rota_listesi[i]][rota_listesi[i + 1]] for i in range(len(rota_listesi) - 1))

    def filo_gercek_maliyeti(rotalar_dict):
        return sum(rota_gercek_maliyeti(r) for r in rotalar_dict.values())

    # Haritaya yol çizgisini ve detaylı Türkçe güzergah adımlarını getiren yeni fonksiyon
    def osrm_geometri_ve_tarif_getir(rota_id_listesi):
        koordinatlar = [tum_noktalar[nid] for nid in rota_id_listesi]

        # Önce tüm rotayı tek seferde çekmeyi deniyoruz
        k_str = ";".join([f"{n['lon']},{n['lat']}" for n in koordinatlar])
        url = f"https://router.project-osrm.org/route/v1/driving/{k_str}?overview=full&geometries=geojson&steps=true&language=tr"

        try:
            res = requests.get(url, timeout=5).json()
            if res["code"] == "Ok":
                geometri = [[c[1], c[0]] for c in res["routes"][0]["geometry"]["coordinates"]]
                yol_tarifi_adimlari = []
                legs = res["routes"][0]["legs"]
                for leg in legs:
                    for step in leg["steps"]:
                        manevra = step["maneuver"]["instruction"]
                        if manevra:
                            yol_tarifi_adimlari.append(manevra)
                return geometri, yol_tarifi_adimlari
        except:
            pass

        # YUKARISI HATA VERİRSE: Noktaları ikişerli (parça parça) çekerek rotayı garanti altına alıyoruz
        toplam_geometri = []
        toplam_tarif = []

        for i in range(len(koordinatlar) - 1):
            n1 = koordinatlar[i]
            n2 = koordinatlar[i + 1]
            parca_url = f"https://router.project-osrm.org/route/v1/driving/{n1['lon']},{n1['lat']};{n2['lon']},{n2['lat']}?overview=full&geometries=geojson&steps=true&language=tr"
            try:
                res = requests.get(parca_url, timeout=3).json()
                if res["code"] == "Ok":
                    coords = [[c[1], c[0]] for c in res["routes"][0]["geometry"]["coordinates"]]
                    toplam_geometri.extend(coords)

                    legs = res["routes"][0]["legs"]
                    for leg in legs:
                        for step in leg["steps"]:
                            manevra = step["maneuver"]["instruction"]
                            if manevra:
                                toplam_tarif.append(manevra)
            except:
                continue

        if toplam_geometri:
            return toplam_geometri, toplam_tarif

        return None, [
            "Güzergah tarifi şu an harita sunucusunun yoğunluğu nedeniyle alınamadı. Lütfen az sonra tekrar deneyin."]

    # --- Sürücü Kapasiteli Akıllı Kümeleme ---
    kalan_kapasiteler = {d_id: suruculer[d_id]["kapasite"] for d_id in suruculer.keys()}
    musteri_kumeleri = {d_id: [] for d_id in suruculer.keys()}
    atanmamis_musteriler = list(musteriler.keys())

    while atanmamis_musteriler:
        en_yakin_m, en_yakin_d, en_kisa_yol = None, None, float('inf')
        for m_id in atanmamis_musteriler:
            for d_id in suruculer.keys():
                if kalan_kapasiteler[d_id] <= 0: continue
                yol_mesafesi = mesafe_matrisi[d_id][m_id]
                if yol_mesafesi < en_kisa_yol:
                    en_kisa_yol, en_yakin_m, en_yakin_d = yol_mesafesi, m_id, d_id
        if en_yakin_m:
            musteri_kumeleri[en_yakin_d].append(en_yakin_m)
            kalan_kapasiteler[en_yakin_d] -= 1
            atanmamis_musteriler.remove(en_yakin_m)
        else:
            break

    # En Yakın Komşu (Nearest Neighbor) ile Başlangıç Rotaları
    baslangic_rotalar = {}
    for d_id, m_listesi in musteri_kumeleri.items():
        sirali_rota = [d_id]
        kalan_m = list(m_listesi)
        while kalan_m:
            en_yakin = min(kalan_m, key=lambda m: mesafe_matrisi[sirali_rota[-1]][m])
            sirali_rota.append(en_yakin)
            kalan_m.remove(en_yakin)
        sirali_rota.append("MERKEZ")
        baslangic_rotalar[d_id] = sirali_rota

    # --- Gerçek Yol Bazlı ALNS Optimizasyonu ---
    en_iyi_alns_rotasi = {k: list(v) for k, v in baslangic_rotalar.items()}
    for _ in range(200):
        test_rotalar = {k: list(v) for k, v in en_iyi_alns_rotasi.items()}
        sokulenler = random.sample(list(musteriler.keys()), min(3, len(musteriler)))
        for s_id in test_rotalar.keys():
            test_rotalar[s_id] = [n for n in test_rotalar[s_id] if n not in sokulenler]

        for m_id in sokulenler:
            en_iyi_d, en_iyi_r, en_dusuk_m = None, None, float('inf')
            for d_id, rota in test_rotalar.items():
                if (len(rota) - 2) >= suruculer[d_id]["kapasite"]: continue
                for idx in range(1, len(rota)):
                    aday = rota[:]
                    aday.insert(idx, m_id)
                    maliyet = rota_gercek_maliyeti(aday)
                    if maliyet < en_dusuk_m:
                        en_dusuk_m, en_iyi_d, en_iyi_r = maliyet, d_id, aday
            if en_iyi_d: test_rotalar[en_iyi_d] = en_iyi_r

        if filo_gercek_maliyeti(test_rotalar) < filo_gercek_maliyeti(en_iyi_alns_rotasi):
            en_iyi_alns_rotasi = {k: list(v) for k, v in test_rotalar.items()}

    # --- Gerçek Yol Bazlı 2-Opt İyileştirmesi ---
    def nihai_iki_opt_gercek(rota):
        en_iyi = list(rota)
        iyilesme = True
        while iyilesme:
            iyilesme = False
            for i in range(1, len(en_iyi) - 2):
                for j in range(i + 1, len(en_iyi) - 1):
                    yeni = en_iyi[:]
                    yeni[i:j + 1] = reversed(yeni[i:j + 1])
                    if rota_gercek_maliyeti(yeni) < rota_gercek_maliyeti(en_iyi):
                        en_iyi, iyilesme = yeni, True
        return en_iyi

    nihai_optimize_rotalar = {d_id: nihai_iki_opt_gercek(rota) for d_id, rota in en_iyi_alns_rotasi.items()}

    # --- Raporlama ve İnteraktif Harita Hazırlığı ---
    arac_detaylari = []
    eski_toplam_km = yeni_toplam_km = 0

    harita = folium.Map(location=[merkez["lat"], merkez["lon"]], zoom_start=11, tiles="OpenStreetMap")
    folium.Marker([merkez["lat"], merkez["lon"]], popup=merkez["ad"],
                  icon=folium.Icon(color="red", icon="star", prefix="fa")).add_to(harita)

    for d_id in baslangic_rotalar.keys():
        km_eski = rota_gercek_maliyeti(baslangic_rotalar[d_id])
        km_yeni = rota_gercek_maliyeti(nihai_optimize_rotalar[d_id])
        eski_toplam_km += km_eski
        yeni_toplam_km += km_yeni

        m_listesi = nihai_optimize_rotalar[d_id][1:-1]
        kapasite = suruculer[d_id]["kapasite"]

        # Geometri ve adım adım rota tarifini OSRM'den çekiyoruz
        geometri, tarif = osrm_geometri_ve_tarif_getir(nihai_optimize_rotalar[d_id])

        arac_detaylari.append({
            "id": d_id,
            "sofor": suruculer[d_id]["ad"],
            "kapasite_doluluk": f"{len(m_listesi)} / {kapasite}",
            "yuzde_doluluk": round((len(m_listesi) / kapasite) * 100, 1),
            "eski_km": round(km_eski, 2),
            "yeni_km": round(km_yeni, 2),
            "tasarruf": round(max(0, km_eski - km_yeni), 2),
            "musteriler": m_listesi,
            "guzergah_tarifi": tarif  # HTML sayfasına gönderilen yol tarifi listesi
        })

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
        "eski_toplam": round(eski_toplam_km, 2),
        "yeni_toplam": round(yeni_toplam_km, 2),
        "toplam_tasarruf": round(max(0, eski_toplam_km - yeni_toplam_km), 2)
    }

    return arac_detaylari, ozet, harita_html


# ========================================================
# 2. FLASK CONTROLLER
# ========================================================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file:
            try:
                araclar, ozet, harita_html = vrp_motoru_calistir(file)
                return render_template('dashboard.html', araclar=araclar, ozet=ozet, harita_html=harita_html)
            except Exception as e:
                return f"Algoritma Çalışırken Sunucu Hatası Oluştu: {str(e)}", 500

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)