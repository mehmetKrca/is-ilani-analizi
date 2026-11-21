"""YÖNTEM 2: Selenium ile scraping.

Gerçek bir Chrome tarayıcısını kodla yönetir: sayfa açılır, JavaScript çalışır,
aşağı kaydırılır, sonra HTML okunur. Yavaştır ama JS ile yüklenen içeriği görür ve
bot korumalarına daha az takılır. (Selenium 4.6+ ChromeDriver'ı kendisi indirir,
bilgisayarında Google Chrome kurulu olması yeterli.)

Kullanım:
    python -m scrapers.selenium_scraper --sayfa 5 --limit 200
    python -m scrapers.selenium_scraper --sayfa 5 --limit 200 --goster   # tarayıcıyı görerek

Bulunan ilan linkleri data/raw/linkler.txt dosyasına da kaydedilir. Böylece
aynı linkleri BeautifulSoup ile de çekip iki yöntemi adil şekilde karşılaştırabilirsin:
    python -m scrapers.bs4_scraper --urls data/raw/linkler.txt --limit 100
"""
import argparse
import re
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config
from scrapers import istatistik
from scrapers.common import CsvYazici, bekle, detay_sayfasini_ayristir, ilan_id_bul, robots_izin_veriyor_mu

YONTEM = "selenium"


def surucu_olustur(goster: bool) -> webdriver.Chrome:
    opt = Options()
    if not goster:
        opt.add_argument("--headless=new")
    opt.add_argument(f"--user-agent={config.USER_AGENT}")
    opt.add_argument("--lang=tr-TR")
    opt.add_argument("--window-size=1366,900")
    opt.add_argument("--disable-blink-features=AutomationControlled")
    opt.add_argument("--blink-settings=imagesEnabled=false")  # resimleri yükleme, daha hızlı
    d = webdriver.Chrome(options=opt)
    d.set_page_load_timeout(config.ZAMAN_ASIMI_SN * 2)
    return d


def asagi_kaydir(d, adim=6):
    """Sonsuz kaydırma / tembel yükleme olan sayfalarda içeriği yükletmek için."""
    for _ in range(adim):
        d.execute_script("window.scrollBy(0, document.body.scrollHeight / 4);")
        time.sleep(0.7)


LISTE_BEKLEME_SN = 20  # liste sayfasında ilanların görünmesi için en fazla bekleme


def sayfadaki_ilan_linkleri(d, desen) -> list[str]:
    """Sayfadaki <a> etiketlerinden ilan detay linklerini döndürür."""
    hrefler = d.execute_script(
        "return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);")
    return [h.split("?")[0] for h in (hrefler or []) if desen.search(h.split("?")[0])]


def ilanlari_bekle(d, desen, sure_sn: int = LISTE_BEKLEME_SN) -> bool:
    """İlan linkleri sayfada görünene kadar en fazla sure_sn saniye bekler."""
    bitis = time.time() + sure_sn
    while time.time() < bitis:
        try:
            if sayfadaki_ilan_linkleri(d, desen):
                return True
        except WebDriverException:
            pass  # sayfa o an yeniden yükleniyor olabilir
        time.sleep(1)
    return False


def sayfayi_kaydet(d, sayfa: int):
    """Hata ayıklamak için sayfanın ekran görüntüsünü ve HTML'ini data/raw içine kaydeder."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    zaman = time.strftime("%Y%m%d_%H%M%S")
    png = config.RAW_DIR / f"liste_sayfa{sayfa}_{zaman}.png"
    htm = config.RAW_DIR / f"liste_sayfa{sayfa}_{zaman}.html"
    try:
        d.save_screenshot(str(png))
        htm.write_text(d.page_source, encoding="utf-8")
        print(f"  Ekran görüntüsü: {png}\n  HTML: {htm}")
    except WebDriverException as e:
        print(f"  Sayfa kaydedilemedi: {e.msg}")


def ilan_linklerini_topla(d, site: dict, sayfa_sayisi: int, goster: bool = False) -> list[str]:
    linkler, desen = [], re.compile(site["ilan_link_regex"])
    for sayfa in range(1, sayfa_sayisi + 1):
        url = site["liste_url"].format(sayfa=sayfa)
        if not robots_izin_veriyor_mu(url):
            print(f"robots.txt izin vermiyor: {url}")
            break
        try:
            d.get(url)
        except WebDriverException as e:
            print(f"Liste sayfası açılamadı: {e.msg}")
            break

        print(f"Sayfa {sayfa}: ilanların yüklenmesi bekleniyor (en fazla {LISTE_BEKLEME_SN} sn)...")
        hazir = ilanlari_bekle(d, desen)
        if not hazir and goster:
            try:
                input("  İlanlar görünmedi. Tarayıcıda 'Devam et' butonuna bas, "
                      "ilanlar görününce buraya dönüp Enter'a bas... ")
                hazir = ilanlari_bekle(d, desen)
            except EOFError:
                print("\n  Klavye girişi yok (etkileşimsiz terminal), beklenmeden devam ediliyor.")
        if not hazir:
            print("  İlan linki bulunamadı, sayfa kaydediliyor.")
            sayfayi_kaydet(d, sayfa)
            if not goster:
                print("  İpucu: --goster ile çalıştırıp butonu elle geçebilirsin.")
            break

        asagi_kaydir(d)
        yeni = 0
        for href in sayfadaki_ilan_linkleri(d, desen):
            tam = urljoin(site["taban_url"], href)
            if tam not in linkler:
                linkler.append(tam)
                yeni += 1
        print(f"Sayfa {sayfa}: {yeni} yeni ilan linki")
        if yeni == 0:
            print("  Bu sayfada yeni link yok (önceki sayfayla aynı olabilir); "
                  "config.py'deki liste_url parametresini kontrol et.")
            sayfayi_kaydet(d, sayfa)
            break
        bekle()
    return linkler


def calistir(d, site_adi: str, linkler: list[str], limit: int):
    yazici = CsvYazici(config.RAW_DIR / f"ilanlar_{YONTEM}.csv")
    deneme = basarili = hata = 0
    net_sure = 0.0
    for url in linkler[:limit]:
        if yazici.var_mi(ilan_id_bul(url)) or not robots_izin_veriyor_mu(url):
            continue
        deneme += 1
        t0 = time.perf_counter()
        try:
            d.get(url)
            time.sleep(1)  # JS'nin içeriği yerleştirmesi için
            kayit = detay_sayfasini_ayristir(d.page_source, url)
            gecen = time.perf_counter() - t0
            if len(kayit.get("ilan_metni", "")) < 100:
                hata += 1
                print(f"  Metin çok kısa, atlandı: {url}")
                continue
            net_sure += gecen
            kayit.update(site=site_adi, yontem=YONTEM, sure_sn=round(gecen, 2))
            yazici.yaz(kayit)
            basarili += 1
            print(f"  [{basarili}] {kayit.get('baslik', '')[:60]}")
        except WebDriverException as e:
            hata += 1
            print(f"  HATA: {e.msg}")
        finally:
            bekle()
    istatistik.kaydet(YONTEM, site_adi, deneme, basarili, hata, 0, net_sure)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="isbul", choices=list(config.SITELER))
    ap.add_argument("--sayfa", type=int, default=3)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--goster", action="store_true", help="Tarayıcı penceresini göster")
    a = ap.parse_args()

    surucu = surucu_olustur(a.goster)
    try:
        linkler = ilan_linklerini_topla(surucu, config.SITELER[a.site], a.sayfa, a.goster)
        dosya = config.RAW_DIR / "linkler.txt"
        dosya.write_text("\n".join(linkler), encoding="utf-8")
        print(f"Toplam {len(linkler)} link bulundu -> {dosya}")
        calistir(surucu, a.site, linkler, a.limit)
    finally:
        surucu.quit()
