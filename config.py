"""Projenin tüm ayarları tek yerde."""
from pathlib import Path

KOK = Path(__file__).resolve().parent
RAW_DIR = KOK / "data" / "raw"
PROCESSED_DIR = KOK / "data" / "processed"
ETIKET_DIR = KOK / "data" / "etiket"
PUBLIC_DIR = KOK / "data" / "public"   # ilan metni içermeyen, repoda paylaşılan hafif veri

# ---------------- SCRAPING ----------------
# Kariyer.net ilan detay adresleri şu formatta: https://www.kariyer.net/is-ilani/<firma-pozisyon>-<id>
# Liste sayfası adresini tarayıcıda kontrol et: 2. sayfaya geçince adres çubuğunda
# hangi parametre çıkıyorsa (ör. ?cp=2) "liste_url" içine onu yaz. {sayfa} yerine sayfa no gelir.
#
# Not: Kariyer.net hem BeautifulSoup'u (HTTP 403) hem Selenium'u (bot doğrulaması) engelledi;
# korumayı atlatmaya çalışılmadı. Veri isbul.net'ten toplanır (robots.txt liste ve ilan
# sayfalarına izin veriyor, ilan sayfalarında JSON-LD JobPosting var).
SITELER = {
    "isbul": {
        "taban_url": "https://www.isbul.net",
        "liste_url": "https://www.isbul.net/is-ilanlari?page={sayfa}",
        "ilan_link_regex": r"/is-ilani/[a-z0-9\-]+-\d+$",
    },
    "kariyer": {
        "taban_url": "https://www.kariyer.net",
        "liste_url": "https://www.kariyer.net/is-ilanlari?cp={sayfa}",
        "ilan_link_regex": r"/is-ilani/[a-z0-9\-]+-\d+",
    },
}

BEKLEME_SN = 2.5          # iki istek arası bekleme (siteye yük bindirmemek için)
ZAMAN_ASIMI_SN = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# ---------------- LLM ----------------
# Ollama'da indirdiğin model adlarını yaz (ollama list komutuyla görebilirsin)
MODELLER = ["qwen2.5:7b"]   # sade versiyon: tek model
ANA_MODEL = "qwen2.5:7b"   # Tüm veri bu modelle işlenir, arayüz bunun sonuçlarını gösterir
MAKS_METIN_KARAKTER = 4000  # Çok uzun ilanlar kırpılır (hız ve bellek için)
