"""Scraper'ların ortak kullandığı yardımcı fonksiyonlar.

İlan detay sayfasından bilgi çıkarmak için iki yol denenir:
1) JSON-LD: İş ilanı siteleri Google'da görünmek için sayfaya schema.org "JobPosting"
   formatında yapılandırılmış veri koyar. En güvenilir kaynak budur.
2) Yedek: JSON-LD yoksa sayfanın görünen metni temizlenip alınır (LLM zaten
   dağınık metinden de bilgi çıkarabilir).
"""
import csv
import html
import json
import re
import time
import urllib.robotparser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import config

ALANLAR = ["ilan_id", "site", "url", "baslik", "sirket", "sehir", "ilce",
           "calisma_tipi", "yayin_tarihi", "ilan_metni", "yontem", "sure_sn", "cekilme_zamani"]

_robots_cache = {}


def _robots_kurallari(metin: str) -> list[tuple[bool, str]]:
    """robots.txt içinden 'User-agent: *' grubuna ait (izin_mi, yol_deseni) kurallarını döndürür."""
    kurallar, gruplar, aktif, onceki_ua = [], [], False, False
    for satir in metin.splitlines():
        satir = satir.split("#", 1)[0].strip()
        if ":" not in satir:
            continue
        alan, deger = (s.strip() for s in satir.split(":", 1))
        alan = alan.lower()
        if alan == "user-agent":
            if not onceki_ua:          # yeni grup başlıyor
                gruplar = []
            gruplar.append(deger)
            aktif = "*" in gruplar
            onceki_ua = True
            continue
        onceki_ua = False
        if aktif and alan in ("allow", "disallow") and deger:
            kurallar.append((alan == "allow", deger))
    return kurallar


def _desen_eslesir_mi(desen: str, yol: str) -> bool:
    """Google robots.txt kuralı: '*' herhangi bir dizi, sondaki '$' adres sonu demek."""
    sonda = desen.endswith("$")
    rx = "".join(".*" if c == "*" else re.escape(c) for c in desen.rstrip("$"))
    return re.match(rx + ("$" if sonda else ""), yol) is not None


def robots_izin_veriyor_mu(url: str) -> bool:
    """Sitenin robots.txt dosyası bu adresin taranmasına izin veriyor mu?

    Python'un urllib.robotparser modülü '*' ve '$' joker karakterlerini desteklemediği için
    kurallar burada Google'ın yorumuyla değerlendirilir: en uzun eşleşen kural kazanır,
    eşitlikte Allow öncelikli.
    """
    p = urlparse(url)
    kok = f"{p.scheme}://{p.netloc}"
    if kok not in _robots_cache:
        try:
            import requests
            r = requests.get(kok + "/robots.txt", timeout=config.ZAMAN_ASIMI_SN,
                             headers={"User-Agent": config.USER_AGENT})
            _robots_cache[kok] = _robots_kurallari(r.text) if r.status_code == 200 else []
        except Exception:
            _robots_cache[kok] = []  # robots.txt okunamazsa engelleme yapmıyoruz
    yol = (p.path or "/") + (f"?{p.query}" if p.query else "")
    en_iyi = None  # (uzunluk, izin_mi)
    for izin, desen in _robots_cache[kok]:
        if _desen_eslesir_mi(desen, yol):
            aday = (len(desen), izin)
            if en_iyi is None or aday > en_iyi:
                en_iyi = aday
    return True if en_iyi is None else en_iyi[1]


def ilan_id_bul(url: str) -> str:
    m = re.search(r"-(\d+)/?(?:\?.*)?$", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-40:]


def html_temizle(metin: str) -> str:
    """HTML etiketlerini atıp düz metne çevirir."""
    if not metin:
        return ""
    soup = BeautifulSoup(html.unescape(metin), "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for blok in soup.find_all(["p", "li", "div", "h1", "h2", "h3", "h4", "ul", "ol", "tr"]):
        blok.insert_before("\n")
        blok.insert_after("\n")
    metin = soup.get_text("")
    metin = re.sub(r"[ \t\xa0]+", " ", metin)
    metin = re.sub(r"\n\s*\n+", "\n", metin)
    return metin.strip()


def _jobposting_bul(veri):
    """JSON-LD içinde (liste/@graph olabilir) JobPosting nesnesini bulur."""
    if isinstance(veri, list):
        for v in veri:
            sonuc = _jobposting_bul(v)
            if sonuc:
                return sonuc
    elif isinstance(veri, dict):
        tip = veri.get("@type")
        if tip == "JobPosting" or (isinstance(tip, list) and "JobPosting" in tip):
            return veri
        if "@graph" in veri:
            return _jobposting_bul(veri["@graph"])
    return None


def _konum(job: dict) -> tuple[str, str]:
    """(il, ilçe) döndürür. schema.org'da addressRegion = il, addressLocality = ilçe."""
    loc = job.get("jobLocation")
    if isinstance(loc, list) and loc:
        loc = loc[0]
    if isinstance(loc, dict):
        adres = loc.get("address", {})
        if isinstance(adres, dict):
            return (adres.get("addressRegion") or "").strip(), (adres.get("addressLocality") or "").strip()
    return "", ""


def detay_sayfasini_ayristir(sayfa_html: str, url: str) -> dict:
    """İlan detay sayfasının HTML'inden ilan bilgilerini çıkarır."""
    soup = BeautifulSoup(sayfa_html, "html.parser")
    kayit = {"url": url, "ilan_id": ilan_id_bul(url)}

    # 1) JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            veri = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        job = _jobposting_bul(veri)
        if job:
            org = job.get("hiringOrganization") or {}
            tip = job.get("employmentType", "")
            il, ilce = _konum(job)
            kayit.update({
                "baslik": job.get("title", ""),
                "sirket": org.get("name", "") if isinstance(org, dict) else str(org),
                "sehir": il,
                "ilce": ilce,
                "calisma_tipi": ", ".join(tip) if isinstance(tip, list) else tip,
                "yayin_tarihi": job.get("datePosted", ""),
                "ilan_metni": html_temizle(job.get("description", "")),
            })
            if job.get("jobLocationType") == "TELECOMMUTE":
                kayit["calisma_tipi"] = (kayit["calisma_tipi"] + ", REMOTE").strip(", ")
            return kayit

    # 2) Yedek: görünen metin
    for etiket in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        etiket.decompose()
    baslik = soup.find("h1")
    og = soup.find("meta", property="og:title")
    kayit["baslik"] = baslik.get_text(strip=True) if baslik else (og["content"] if og else "")
    ana = soup.find("main") or soup.body or soup
    kayit["ilan_metni"] = html_temizle(str(ana))[:8000]
    return kayit


class CsvYazici:
    """Ham ilanları CSV'ye yazar, daha önce çekilmiş ilanları atlar (kaldığı yerden devam)."""

    def __init__(self, dosya: Path):
        self.dosya = dosya
        self.mevcut = set()
        if dosya.exists():
            with open(dosya, encoding="utf-8-sig", newline="") as f:
                self.mevcut = {r["ilan_id"] for r in csv.DictReader(f)}
        else:
            dosya.parent.mkdir(parents=True, exist_ok=True)
            with open(dosya, "w", encoding="utf-8-sig", newline="") as f:
                csv.DictWriter(f, fieldnames=ALANLAR).writeheader()

    def var_mi(self, ilan_id: str) -> bool:
        return ilan_id in self.mevcut

    def yaz(self, kayit: dict):
        kayit.setdefault("cekilme_zamani", datetime.now().isoformat(timespec="seconds"))
        with open(self.dosya, "a", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=ALANLAR, extrasaction="ignore").writerow(
                {k: kayit.get(k, "") for k in ALANLAR})
        self.mevcut.add(kayit["ilan_id"])


def bekle():
    time.sleep(config.BEKLEME_SN)
