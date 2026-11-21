"""Scraping yöntemlerinin performansını kaydeder (rapordaki yöntem karşılaştırması için)."""
import csv
from datetime import datetime

import config

DOSYA = config.RAW_DIR / "scraping_istatistik.csv"
ALANLAR = ["zaman", "yontem", "site", "deneme", "basarili", "hata", "engellenen",
           "toplam_sure_sn", "ilan_basina_sn"]


def kaydet(yontem, site, deneme, basarili, hata, engellenen, toplam_sure):
    yeni = not DOSYA.exists()
    DOSYA.parent.mkdir(parents=True, exist_ok=True)
    with open(DOSYA, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        if yeni:
            w.writeheader()
        w.writerow({
            "zaman": datetime.now().isoformat(timespec="seconds"),
            "yontem": yontem, "site": site, "deneme": deneme, "basarili": basarili,
            "hata": hata, "engellenen": engellenen,
            "toplam_sure_sn": round(toplam_sure, 1),
            "ilan_basina_sn": round(toplam_sure / basarili, 2) if basarili else "",
        })
    print(f"\n[{yontem}] deneme={deneme} basarili={basarili} hata={hata} "
          f"engellenen={engellenen} sure={toplam_sure:.0f} sn")
