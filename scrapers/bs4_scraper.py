"""YÖNTEM 1: requests + BeautifulSoup ile scraping.

Sayfanın HTML'ini doğrudan indirir ve ayrıştırır. Çok hızlıdır ama JavaScript ile
sonradan yüklenen içeriği göremez ve bot korumalarına daha kolay takılır.

Kullanım (proje klasöründen):
    python -m scrapers.bs4_scraper --sayfa 5 --limit 200
    python -m scrapers.bs4_scraper --urls urls.txt     # elle toplanmış ilan linkleriyle
"""
import argparse
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from scrapers import istatistik
from scrapers.common import CsvYazici, bekle, detay_sayfasini_ayristir, ilan_id_bul, robots_izin_veriyor_mu

YONTEM = "beautifulsoup"
ENGEL_KODLARI = {403, 429, 503}

oturum = requests.Session()
oturum.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "tr-TR,tr;q=0.9"})


def ilan_linklerini_topla(site: dict, sayfa_sayisi: int) -> list[str]:
    linkler, desen = [], re.compile(site["ilan_link_regex"])
    for sayfa in range(1, sayfa_sayisi + 1):
        url = site["liste_url"].format(sayfa=sayfa)
        if not robots_izin_veriyor_mu(url):
            print(f"robots.txt izin vermiyor: {url}")
            break
        try:
            r = oturum.get(url, timeout=config.ZAMAN_ASIMI_SN)
        except requests.RequestException as e:
            print(f"Liste sayfası alınamadı ({e})")
            break
        if r.status_code in ENGEL_KODLARI:
            print(f"Liste sayfası engellendi (HTTP {r.status_code}). Selenium yöntemini dene.")
            break
        soup = BeautifulSoup(r.text, "html.parser")
        yeni = 0
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0]
            if desen.search(href):
                tam = urljoin(site["taban_url"], href)
                if tam not in linkler:
                    linkler.append(tam)
                    yeni += 1
        print(f"Sayfa {sayfa}: {yeni} yeni ilan linki")
        if yeni == 0:
            print("  Bu sayfada link bulunamadı. İçerik JavaScript ile yükleniyor olabilir "
                  "-> Selenium kullan ya da config.py'deki liste_url'yi kontrol et.")
            break
        bekle()
    return linkler


def calistir(site_adi: str, linkler: list[str], limit: int):
    yazici = CsvYazici(config.RAW_DIR / f"ilanlar_{YONTEM}.csv")
    deneme = basarili = hata = engel = 0
    net_sure = 0.0
    for url in linkler[:limit]:
        if yazici.var_mi(ilan_id_bul(url)):
            continue
        if not robots_izin_veriyor_mu(url):
            print(f"robots.txt izin vermiyor, atlandı: {url}")
            continue
        deneme += 1
        t0 = time.perf_counter()
        try:
            r = oturum.get(url, timeout=config.ZAMAN_ASIMI_SN)
            if r.status_code in ENGEL_KODLARI:
                engel += 1
                print(f"  ENGEL HTTP {r.status_code}: {url}")
                if engel >= 5:
                    print("Üst üste engelleniyoruz, duruyorum. Selenium yöntemine geç.")
                    break
                continue
            r.raise_for_status()
            kayit = detay_sayfasini_ayristir(r.text, url)
            net_sure += time.perf_counter() - t0
            if len(kayit.get("ilan_metni", "")) < 100:
                hata += 1
                print(f"  Metin çok kısa, atlandı: {url}")
                continue
            kayit.update(site=site_adi, yontem=YONTEM, sure_sn=round(time.perf_counter() - t0, 2))
            yazici.yaz(kayit)
            basarili += 1
            print(f"  [{basarili}] {kayit.get('baslik', '')[:60]}")
        except requests.RequestException as e:
            hata += 1
            print(f"  HATA: {e}")
        finally:
            bekle()
    istatistik.kaydet(YONTEM, site_adi, deneme, basarili, hata, engel, net_sure)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="isbul", choices=list(config.SITELER))
    ap.add_argument("--sayfa", type=int, default=3, help="Kaç liste sayfası taransın")
    ap.add_argument("--limit", type=int, default=100, help="En fazla kaç ilan çekilsin")
    ap.add_argument("--urls", help="Her satırda bir ilan linki olan dosya (liste taraması yerine)")
    a = ap.parse_args()

    if a.urls:
        with open(a.urls, encoding="utf-8") as f:
            linkler = [s.strip() for s in f if s.strip().startswith("http")]
    else:
        linkler = ilan_linklerini_topla(config.SITELER[a.site], a.sayfa)
    print(f"Toplam {len(linkler)} link bulundu.")
    calistir(a.site, linkler, a.limit)
