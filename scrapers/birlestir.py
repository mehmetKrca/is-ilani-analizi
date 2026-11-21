"""İki yöntemle çekilen ilanları tek dosyada birleştirir, tekrar edenleri atar.

Kullanım:  python -m scrapers.birlestir
Çıktı:     data/raw/ilanlar.csv
"""
import pandas as pd

import config

parcalar = []
for dosya in config.RAW_DIR.glob("ilanlar_*.csv"):
    df = pd.read_csv(dosya, encoding="utf-8-sig", dtype=str).fillna("")
    print(f"{dosya.name}: {len(df)} ilan")
    parcalar.append(df)

if not parcalar:
    raise SystemExit("Hiç ham veri yok. Önce scraper'ları çalıştır.")

hepsi = pd.concat(parcalar, ignore_index=True)
hepsi = hepsi[hepsi["ilan_metni"].str.len() >= 100]
hepsi = hepsi.drop_duplicates(subset="ilan_id", keep="first")
cikti = config.RAW_DIR / "ilanlar.csv"
hepsi.to_csv(cikti, index=False, encoding="utf-8-sig")
print(f"\nBirleşik veri: {len(hepsi)} benzersiz ilan -> {cikti}")
