"""Toplanan ilanları LLM'den geçirip yapılandırılmış veriye çevirir.

Kullanım:
    python -m llm.cikar                                  # tüm ilanlar, ana model
    python -m llm.cikar --model llama3.2:3b --ids data/etiket/etiket_idler.txt
    python -m llm.cikar --limit 20                       # hızlı deneme

Çıktı: data/processed/<model>.jsonl  (her satır bir ilan)
Yarıda kesilirse tekrar çalıştır, kaldığı yerden devam eder.
"""
import argparse
import json

import pandas as pd

import config
from llm.sema import analiz_et


def model_dosyasi(model: str):
    return config.PROCESSED_DIR / (model.replace(":", "_").replace("/", "_") + ".jsonl")


def islenmisler(dosya) -> set:
    if not dosya.exists():
        return set()
    with open(dosya, encoding="utf-8") as f:
        return {json.loads(s)["ilan_id"] for s in f if s.strip()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.ANA_MODEL)
    ap.add_argument("--ids", help="Sadece bu dosyadaki ilan_id'leri işle")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    df = pd.read_csv(config.RAW_DIR / "ilanlar.csv", encoding="utf-8-sig", dtype=str).fillna("")
    if a.ids:
        with open(a.ids, encoding="utf-8") as f:
            idler = {s.strip() for s in f if s.strip()}
        df = df[df["ilan_id"].isin(idler)]

    cikti = model_dosyasi(a.model)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    bitti = islenmisler(cikti)
    df = df[~df["ilan_id"].isin(bitti)]
    if a.limit:
        df = df.head(a.limit)
    print(f"Model: {a.model} | işlenecek ilan: {len(df)} (önceden işlenen: {len(bitti)})")

    with open(cikti, "a", encoding="utf-8") as f:
        for i, (_, satir) in enumerate(df.iterrows(), 1):
            metin = f"Başlık: {satir['baslik']}\nŞehir: {satir['sehir']}\n" \
                    f"Çalışma tipi: {satir['calisma_tipi']}\n\n{satir['ilan_metni']}"
            sonuc, sure, gecerli = analiz_et(metin, a.model)
            f.write(json.dumps({"ilan_id": satir["ilan_id"], "model": a.model, "gecerli": gecerli,
                                "sure_sn": sure, "sonuc": sonuc}, ensure_ascii=False) + "\n")
            f.flush()
            durum = sonuc["pozisyon"] if gecerli else "GEÇERSİZ ÇIKTI"
            print(f"[{i}/{len(df)}] {sure:5.1f} sn | {durum}")
    print(f"Bitti -> {cikti}")
