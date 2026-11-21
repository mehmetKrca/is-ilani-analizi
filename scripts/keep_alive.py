"""Streamlit Community Cloud'daki uygulamayı uyanık tutar (GitHub Actions'tan çağrılır).

Düz bir HTTP isteği uygulamayı uyandırmaz; uygulama ancak gerçek bir tarayıcı sayfayı açıp
WebSocket bağlantısı kurunca çalışır. Bu yüzden Playwright ile headless Chromium kullanılır:
  1. Uygulama adresi açılır.
  2. Uyku ekranındaki "Yes, get this app back up!" butonu çıkarsa tıklanır.
  3. Uygulamanın gerçekten yüklendiği, sayfada (Streamlit Cloud uygulamayı bir iframe içinde
     gösterdiği için iframe'ler dahil) BEKLENEN yazının görünmesiyle doğrulanır.
  4. En fazla SURE_SN saniye beklenir; yüklenmezse çıkış kodu 1 olur (Actions işi başarısız görünür).

Yerelde kullanım:
    pip install playwright && python -m playwright install chromium
    python scripts/keep_alive.py [adres]
"""
import os
import re
import sys
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

URL = (sys.argv[1] if len(sys.argv) > 1 else
       os.environ.get("APP_URL", "https://is-piyasasi-llm.streamlit.app/"))
BEKLENEN = "İş Piyasası Analizi"          # kenar çubuğundaki proje adı
UYANDIR = re.compile(r"get this app back up", re.I)
SURE_SN = int(os.environ.get("BEKLEME_SN", "180"))
EKRAN = os.environ.get("EKRAN_DOSYASI", "keep_alive_hata.png")


def log(mesaj: str):
    print(f"[{time.strftime('%H:%M:%S')}] {mesaj}", flush=True)


def uygulama_yuklendi_mi(sayfa) -> bool:
    for cerceve in sayfa.frames:  # ana sayfa + tüm iframe'ler
        try:
            yazi = cerceve.get_by_text(BEKLENEN, exact=False)
            if yazi.count() and yazi.first.is_visible():
                return True
        except PlaywrightError:
            continue  # çerçeve bu sırada yeniden yükleniyor olabilir
    return False


def uyandir_butonuna_bas(sayfa) -> bool:
    for cerceve in sayfa.frames:
        try:
            buton = cerceve.get_by_role("button", name=UYANDIR)
            if buton.count() and buton.first.is_visible():
                buton.first.click()
                return True
        except PlaywrightError:
            continue
    return False


def main() -> int:
    log(f"Açılıyor: {URL} (en fazla {SURE_SN} sn beklenecek)")
    with sync_playwright() as p:
        tarayici = p.chromium.launch(headless=True)
        sayfa = tarayici.new_page(viewport={"width": 1366, "height": 900})
        try:
            sayfa.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        except PlaywrightError as hata:
            log(f"Sayfa açılamadı: {hata}")  # yine de beklemeye devam et; yönlendirme olabilir
        bitis = time.monotonic() + SURE_SN
        tiklandi = 0
        while time.monotonic() < bitis:
            if uygulama_yuklendi_mi(sayfa):
                log(f"Uygulama yüklendi: '{BEKLENEN}' görüldü. Uyandırma butonu tıklama: {tiklandi}")
                tarayici.close()
                return 0
            if uyandir_butonuna_bas(sayfa):
                tiklandi += 1
                log("Uyku ekranı: 'Yes, get this app back up!' butonuna basıldı, uyanması bekleniyor...")
            time.sleep(3)
        log(f"HATA: {SURE_SN} sn içinde '{BEKLENEN}' görünmedi.")
        try:
            sayfa.screenshot(path=EKRAN, full_page=True)
            log(f"Ekran görüntüsü kaydedildi: {EKRAN}")
        except PlaywrightError:
            pass
        tarayici.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
