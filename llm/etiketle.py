"""Model karşılaştırması için 'altın standart' etiketleme dosyası hazırlar.

Kullanım:  python -m llm.etiketle --n 30

Çıktı:
  data/etiket/etiket_sablonu.xlsx -> Excel'de aç, boş sütunları ilanı okuyarak SEN doldur,
                                     data/etiket/etiket.xlsx adıyla kaydet.
  data/etiket/etiket_idler.txt    -> İkinci modeli sadece bu ilanlarda çalıştırmak için.

Doldurma kuralları:
  teknik_beceriler : noktalı virgülle ayır  -> Python; Django; PostgreSQL
  seviye           : Stajyer / Junior / Mid / Senior / Yönetici / Belirtilmemiş
  calisma_sekli    : Ofis / Hibrit / Uzaktan / Belirtilmemiş
  sektor           : llm/sema.py içindeki SEKTORLER listesinden biri
ÖNEMLİ: Etiketlerken modelin çıktısına BAKMA, yoksa karşılaştırma taraflı olur.
"""
import argparse

import pandas as pd

import config

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()

    df = pd.read_csv(config.RAW_DIR / "ilanlar.csv", encoding="utf-8-sig", dtype=str).fillna("")
    ornek = df.sample(n=min(a.n, len(df)), random_state=42)
    sablon = ornek[["ilan_id", "baslik", "ilan_metni"]].copy()
    for s in ["teknik_beceriler", "seviye", "calisma_sekli", "sektor"]:
        sablon[s] = ""
    config.ETIKET_DIR.mkdir(parents=True, exist_ok=True)
    sablon.to_excel(config.ETIKET_DIR / "etiket_sablonu.xlsx", index=False)
    (config.ETIKET_DIR / "etiket_idler.txt").write_text("\n".join(sablon["ilan_id"]), encoding="utf-8")
    print(f"{len(sablon)} ilanlık şablon hazır: {config.ETIKET_DIR / 'etiket_sablonu.xlsx'}")
