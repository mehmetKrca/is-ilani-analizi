"""Arayüzün internette (Streamlit Cloud) çalışması için hafif, paylaşılabilir veri hazırlar.

Ham ilan metinleri (ilan_metni) repoya konmaz; sadece ilanın künyesi (başlık, şirket, il, adres),
LLM'in çıkardığı yapılandırılmış sonuçlar ve scraping istatistiği data/public/ altına yazılır.
Arayüz yerelde tam veriyi, o yoksa bu klasörü kullanır.

Kullanım (LLM işlemi bittikten sonra):
    python -m llm.disa_aktar
"""
import json
import shutil
from datetime import datetime

import pandas as pd

import config
from llm.dogrula import sonucu_dogrula

KUNYE = ["ilan_id", "site", "baslik", "sirket", "sehir", "ilce", "url", "yayin_tarihi"]


def model_dosya_adi(model: str) -> str:
    return model.replace(":", "_").replace("/", "_") + ".jsonl"


if __name__ == "__main__":
    hedef = config.PUBLIC_DIR
    hedef.mkdir(parents=True, exist_ok=True)

    ham = pd.read_csv(config.RAW_DIR / "ilanlar.csv", encoding="utf-8-sig", dtype=str).fillna("")
    ham = ham.drop_duplicates("ilan_id")
    metinler = (ham["baslik"] + "\n" + ham["ilan_metni"]).set_axis(ham["ilan_id"]).to_dict()
    ham[KUNYE].to_csv(hedef / "ilanlar.csv", index=False, encoding="utf-8-sig")  # ilan metni YOK

    kaynak = config.PROCESSED_DIR / model_dosya_adi(config.ANA_MODEL)
    son = {}
    with open(kaynak, encoding="utf-8") as f:
        for s in f:
            if s.strip():
                r = json.loads(s)
                son[r["ilan_id"]] = r  # aynı ilan iki kez varsa sonuncusu
    # Kurala dayalı doğrulama (llm/dogrula.py): metin burada var, bulutta yok. Düzeltilen
    # kayıtlarda LLM'in ilk cevabı "duzeltme" alanında saklanır.
    duzeltilen = 0
    with open(hedef / model_dosya_adi(config.ANA_MODEL), "w", encoding="utf-8") as f:
        for r in son.values():
            if r.get("gecerli") and r.get("sonuc"):
                r["sonuc"], duz = sonucu_dogrula(r["sonuc"], metinler.get(r["ilan_id"], ""))
                if duz:
                    r["duzeltme"] = duz
                    duzeltilen += 1
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    shutil.copyfile(config.RAW_DIR / "scraping_istatistik.csv", hedef / "scraping_istatistik.csv")

    with open(hedef / "bilgi.json", "w", encoding="utf-8") as f:
        json.dump({"guncelleme": datetime.now().strftime("%d.%m.%Y %H:%M"),
                   "model": config.ANA_MODEL}, f, ensure_ascii=False, indent=2)

    print(f"{len(ham)} ilan künyesi, {len(son)} LLM sonucu ({duzeltilen} eğitim etiketi düzeltildi) -> {hedef}")
