"""Modelleri elle etiketlenmiş altın standarda göre karşılaştırır.

Kullanım:  python -m llm.degerlendir
Gereken:   data/etiket/etiket.xlsx (doldurulmuş) ve data/processed/*.jsonl
Çıktı:     data/processed/model_karsilastirma.csv (arayüzde de gösterilir)

Metrikler:
  Beceri precision : Modelin bulduğu becerilerin ne kadarı gerçekten doğru?
  Beceri recall    : İlandaki becerilerin ne kadarını bulabildi?
  Beceri F1        : İkisinin harmonik ortalaması
  Seviye/Çalışma şekli/Sektör doğruluğu, geçerli JSON oranı, ilan başına süre
"""
import json

import pandas as pd

import config
from llm.normalize import anahtar, normalize_et


def kume(beceriler) -> set:
    return {anahtar(normalize_et(b)) for b in beceriler if str(b).strip()}


def model_degerlendir(jsonl, altin: pd.DataFrame) -> dict | None:
    with open(jsonl, encoding="utf-8") as f:
        kayitlar = {r["ilan_id"]: r for r in map(json.loads, filter(str.strip, f))}
    ortak = [i for i in altin.index if i in kayitlar]
    if not ortak:
        return None
    dp = tahmin_say = gercek_say = 0
    dogru = {"seviye": 0, "calisma_sekli": 0, "sektor": 0}
    gecerli, sureler = 0, []
    for i in ortak:
        r, g = kayitlar[i], altin.loc[i]
        sureler.append(r["sure_sn"])
        gercek = kume(str(g["teknik_beceriler"]).split(";"))
        gercek_say += len(gercek)
        if not r["gecerli"]:
            continue
        gecerli += 1
        s = r["sonuc"]
        tahmin = kume(s["teknik_beceriler"])
        tahmin_say += len(tahmin)
        dp += len(tahmin & gercek)
        for alan in dogru:
            dogru[alan] += anahtar(str(s[alan])) == anahtar(str(g[alan]))
    p = dp / tahmin_say if tahmin_say else 0
    rc = dp / gercek_say if gercek_say else 0
    n = len(ortak)
    return {
        "model": jsonl.stem, "ilan_sayisi": n,
        "beceri_precision": round(p, 3), "beceri_recall": round(rc, 3),
        "beceri_f1": round(2 * p * rc / (p + rc), 3) if p + rc else 0,
        "seviye_dogruluk": round(dogru["seviye"] / n, 3),
        "calisma_sekli_dogruluk": round(dogru["calisma_sekli"] / n, 3),
        "sektor_dogruluk": round(dogru["sektor"] / n, 3),
        "gecerli_json_orani": round(gecerli / n, 3),
        "ort_sure_sn": round(sum(sureler) / n, 2),
    }


if __name__ == "__main__":
    altin = pd.read_excel(config.ETIKET_DIR / "etiket.xlsx", dtype=str).fillna("")
    altin = altin.set_index("ilan_id")
    sonuclar = [r for f in sorted(config.PROCESSED_DIR.glob("*.jsonl"))
                if (r := model_degerlendir(f, altin))]
    if not sonuclar:
        raise SystemExit("Etiketli ilanlarla eşleşen model çıktısı yok. Önce llm.cikar --ids ... çalıştır.")
    tablo = pd.DataFrame(sonuclar)
    tablo.to_csv(config.PROCESSED_DIR / "model_karsilastirma.csv", index=False, encoding="utf-8-sig")
    print(tablo.to_string(index=False))
