"""LLM çıktısının kurala dayalı doğrulaması (son işlem).

Eğitim düzeyi: qwen2.5:7b "lisans" ile "lise"yi karıştırabiliyor ve metinde olmayan düzeyler
uydurabiliyordu. Kural:
  - LLM'in verdiği düzey ilan metninde geçiyorsa olduğu gibi kalır.
  - Geçmiyorsa ve metinde başka düzeyler geçiyorsa, geçenlerin en düşüğü seçilir
    (prompt'taki "birden fazla düzey yazıyorsa en düşüğünü seç" kuralıyla aynı).
  - Metinde hiçbir eğitim ifadesi yoksa "Belirtilmemiş" olur.
  - LLM "Belirtilmemiş" dediyse dokunulmaz ("üniversite öğrencisi" gibi şart olmayan
    ifadelerden yanlış etiket üretmemek için).
"""
import re

SIRA = ["Lise", "Ön Lisans", "Lisans", "Yüksek Lisans", "Doktora"]  # düşükten yükseğe

_YL = r"yüksek\s?lisans|\bmaster\b|\bmba\b"
_ON = r"ön\s?lisans|önlisans|meslek\s?yüksek\s?okulu|\bmyo\b|2\s?yıllık"
DESENLER = {
    "Doktora": r"doktora|\bph\.?\s?d\b",
    "Yüksek Lisans": _YL,
    "Ön Lisans": _ON,
    "Lisans": r"\blisans\b|üniversite|fakülte|4\s?yıllık",   # YL/ÖL ifadeleri önce silinir
    "Lise": r"\blise(si|sinden|den|ye|ler)?\b|ortaöğretim",
}


def metindeki_egitimler(metin: str) -> set[str]:
    m = metin.lower().replace("i̇", "i")
    bulunan = {ad for ad in ("Doktora", "Yüksek Lisans", "Ön Lisans") if re.search(DESENLER[ad], m)}
    sade = re.sub(_YL + "|" + _ON, " ", m)  # "yüksek lisans" ve "ön lisans" düz "lisans" sayılmasın
    for ad in ("Lisans", "Lise"):
        if re.search(DESENLER[ad], sade):
            bulunan.add(ad)
    return bulunan


def egitimi_dogrula(egitim: str, metin: str) -> str:
    """LLM'in eğitim etiketini ilan metnine göre doğrular; gerekirse düzeltilmiş değeri döndürür."""
    if egitim not in SIRA:          # "Belirtilmemiş" vb.
        return egitim
    bulunan = metindeki_egitimler(metin)
    if egitim in bulunan:
        return egitim
    if bulunan:
        return min(bulunan, key=SIRA.index)
    return "Belirtilmemiş"


def sonucu_dogrula(sonuc: dict, metin: str) -> tuple[dict, dict]:
    """(düzeltilmiş_sonuç, {alan: llm_değeri}) döndürür; düzeltme yoksa ikinci sözlük boş."""
    yeni = dict(sonuc)
    duzeltme = {}
    dogru = egitimi_dogrula(sonuc.get("egitim", ""), metin)
    if dogru != sonuc.get("egitim"):
        duzeltme["egitim"] = sonuc.get("egitim")
        yeni["egitim"] = dogru
    return yeni, duzeltme
