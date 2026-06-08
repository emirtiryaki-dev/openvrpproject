import pandas as pd

# 1. MERKEZ SAYFASI VERİSİ
merkez_data = {
    "id": ["MERKEZ"],
    "ad": ["Kadıköy Ana Depo"],
    "lat": [40.9905],
    "lon": [29.0204]
}

# 2. SÜRÜCÜLER / ARAÇLAR SAYFASI VERİSİ
surucu_data = {
    "id": ["D1", "D2", "D3", "D4", "D5"],
    "ad": ["Ahmet (Gaziosmanpaşa)", "Mehmet (Ümraniye)", "Can (Maltepe)", "Murat (Beşiktaş)", "Burak (Bakırköy)"],
    "lat": [41.0583, 41.0167, 40.9333, 41.0428, 40.9781],
    "lon": [28.9141, 29.1244, 29.1333, 29.0075, 28.8744],
    "renk": ["purple", "orange", "blue", "green", "red"],
    "kapasite": [12, 12, 10, 10, 10]
}

# 3. MÜŞTERİLER SAYFASI VERİSİ (50 Nokta)
musteri_data = {
    "id": [f"M{i}" for i in range(1, 51)],
    "ad": [
        "Kadıköy Müşterisi", "Üsküdar Merkez", "Ataşehir Batı", "Ümraniye Çarşı", "Maltepe Sahil",
        "Kartal Merkez", "Pendik Doğu", "Beşiktaş Sahil", "Şişli Mecidiyeköy", "Beyoğlu Taksim",
        "Fatih Sultanahmet", "Zeytinburnu", "Bakırköy İncirli", "Bahçelievler Merkez", "Küçükçekmece Cennet",
        "Avcılar Merkez", "Beylikdüzü", "Esenyurt Doğu", "Bağcılar Meydan", "Esenler Dörtyol",
        "Bayrampaşa", "Gaziosmanpaşa Merkez", "Sultangazi", "Eyüpsultan", "Kağıthane Merkez",
        "Sarıyer Maslak", "Sarıyer Merkez", "Beykoz Kavacık", "Beykoz Merkez", "Çekmeköy Merkez",
        "Sancaktepe", "Sultanbeyli", "Tuzla Marina", "Bostancı İskele", "Suadiye",
        "Göztepe Parkı", "Erenköy", "Kozyatağı", "İçerenköy", "Kayışdağı",
        "Dudullu OSB", "Şerifali", "Batı Ataşehir 2", "Libadiye", "Çamlıca Tepesi",
        "Beylerbeyi", "Çengelköy", "Ümraniye Tepeüstü", "Söğütlüçeşme", "Moda Sahil"
    ],
    "lat": [
        40.9925, 41.0267, 40.9912, 41.0251, 40.9241, 40.8881, 40.8753, 41.0411, 41.0632, 41.0369,
        41.0085, 40.9881, 40.9943, 41.0012, 40.9854, 40.9801, 40.9924, 41.0342, 41.0341, 41.0375,
        41.0471, 41.0574, 41.1042, 41.0474, 41.0812, 41.1124, 41.1663, 41.0915, 41.1163, 41.0412,
        41.0063, 40.9674, 40.8163, 40.9524, 40.9612, 40.9754, 40.9712, 40.9763, 40.9881, 40.9774,
        41.0084, 41.0011, 40.9953, 41.0055, 41.0284, 41.0442, 41.0512, 41.0215, 40.9911, 40.9842
    ],
    "lon": [
        29.0275, 29.0151, 29.1042, 29.0963, 29.1312, 29.1855, 29.2312, 29.0082, 28.9921, 28.9774,
        28.9802, 28.8953, 28.8624, 28.8611, 28.7842, 28.7182, 28.6431, 28.6812, 28.8563, 28.8814,
        28.9122, 28.9155, 28.8893, 28.9341, 28.9734, 29.0211, 29.0512, 29.0914, 29.0664, 29.1741,
        29.2255, 29.2612, 29.3031, 29.0942, 29.0831, 29.0611, 29.0742, 29.0955, 29.1114, 29.1512,
        29.1624, 29.1363, 29.1121, 29.0824, 29.0663, 29.0454, 29.0521, 29.1292, 29.0374, 29.0221
    ]
}

# DataFrame'leri oluşturma
df_merkez = pd.DataFrame(merkez_data)
df_suruculer = pd.DataFrame(surucu_data)
df_musteriler = pd.DataFrame(musteri_data)

# Excel dosyası olarak kaydetme
excel_adi = "İstanbul_50_Musteri_VRP.xlsx"
with pd.ExcelWriter(excel_adi, engine="openpyxl") as writer:
    df_merkez.to_excel(writer, sheet_name="Merkez", index=False)
    df_suruculer.to_excel(writer, sheet_name="Suruculer", index=False)
    df_musteriler.to_excel(writer, sheet_name="Musteriler", index=False)

print(f"🎉 Büyük test dosyası '{excel_adi}' başarıyla oluşturuldu!")