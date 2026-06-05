import pandas as pd

# 1. MERKEZ SAYFASI VERİSİ (Algoritmanın ana çıkış noktası)
merkez_data = {
    "id": ["MERKEZ"],
    "ad": ["Ana Lojistik Deposu"],
    "lat": [41.0082],  # İstanbul merkezi bir nokta
    "lon": [28.9784]
}

# 2. SÜRÜCÜLER / ARAÇLAR SAYFASI VERİSİ
# ID'ler mutlaka 'D' ile başlamalı. Renkler haritada görünecek renklerdir.
surucu_data = {
    "id": ["D1", "D2", "D3"],
    "ad": ["Ahmet Yılmaz (Sarı Araç)", "Mehmet Demir (Mavi Araç)", "Can Kaya (Mor Araç)"],
    "lat": [41.0422, 40.9920, 41.0150],  # Farklı konumlardaki araç başlangıçları
    "lon": [29.0074, 29.1220, 28.8500],
    "renk": ["orange", "blue", "purple"],
    "kapasite": [5, 4, 6]  # Her aracın taşıyabileceği maksimum müşteri sayısı
}

# 3. MÜŞTERİLER SAYFASI VERİSİ (Dağıtım yapılacak noktalar)
# İstanbul'un farklı ilçelerinden koordinatlar (Kadıköy, Beşiktaş, Bakırköy, Ümraniye vb.)
musteri_data = {
    "id": [f"M{i}" for i in range(1, 13)],
    "ad": [
        "Kadıköy Müşterisi", "Beşiktaş Müşterisi", "Bakırköy Müşterisi",
        "Ümraniye Müşterisi", "Şişli Müşterisi", "Fatih Müşterisi",
        "Maltepe Müşterisi", "Sarıyer Müşterisi", "Zeytinburnu Müşterisi",
        "Ataşehir Müşterisi", "Pendik Müşterisi", "Kartal Müşterisi"
    ],
    "lat": [40.9901, 41.0428, 40.9781, 41.0253, 41.0600, 41.0165, 40.9450, 41.1680, 40.9900, 40.9850, 40.8750, 40.8900],
    "lon": [29.0280, 29.0074, 28.7944, 29.1172, 28.9870, 28.9485, 29.1320, 29.0570, 28.8950, 29.1080, 29.2300, 29.1800]
}

# DataFrame'leri oluşturma
df_merkez = pd.DataFrame(merkez_data)
df_suruculer = pd.DataFrame(surucu_data)
df_musteriler = pd.DataFrame(musteri_data)

# Hepsini tek bir Excel dosyasında farklı sayfalara (sheet) yazma
excel_adi = "VRP_Test_Verisi.xlsx"
with pd.ExcelWriter(excel_adi, engine="openpyxl") as writer:
    df_merkez.to_excel(writer, sheet_name="Merkez", index=False)
    df_suruculer.to_excel(writer, sheet_name="Suruculer", index=False)
    df_musteriler.to_excel(writer, sheet_name="Musteriler", index=False)

print(f"🎉 Harika! '{excel_adi}' dosyası başarıyla oluşturuldu.")