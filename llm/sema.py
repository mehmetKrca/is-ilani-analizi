"""LLM'den istenen çıktının şeması, prompt ve tek ilanı analiz eden fonksiyon.

Ollama'nın "structured outputs" özelliği kullanılır: modele bir JSON şeması verilir,
model çıktısını bu şemaya uymaya zorlanır. Böylece bozuk JSON riski çok azalır.
"""
import json
import time
from typing import Literal

import ollama
from pydantic import BaseModel, Field, ValidationError

import config

SEKTORLER = ["Yazılım/Bilişim", "Mühendislik", "Satış", "Pazarlama", "Finans/Muhasebe",
             "İnsan Kaynakları", "Sağlık", "Eğitim", "Lojistik", "Üretim",
             "Müşteri Hizmetleri", "Tasarım", "Hukuk", "İdari İşler",
             "Hizmet/Güvenlik/Temizlik", "Diğer"]
SEVIYELER = ["Stajyer", "Junior", "Mid", "Senior", "Yönetici", "Belirtilmemiş"]
EGITIM = ["Lise", "Ön Lisans", "Lisans", "Yüksek Lisans", "Doktora", "Belirtilmemiş"]
CALISMA = ["Ofis", "Hibrit", "Uzaktan", "Belirtilmemiş"]


class IlanAnalizi(BaseModel):
    pozisyon: str = Field(description="Pozisyonun kısa, genel adı")
    sektor: Literal[tuple(SEKTORLER)]
    seviye: Literal[tuple(SEVIYELER)]
    deneyim_yil: int = Field(description="İstenen minimum deneyim yılı; belirtilmemişse 0")
    # max_length -> JSON şemasında maxItems: modelin aynı listeyi sonsuza dek uzatmasını engeller
    teknik_beceriler: list[str] = Field(max_length=15)
    sosyal_beceriler: list[str] = Field(max_length=10)
    egitim: Literal[tuple(EGITIM)]
    calisma_sekli: Literal[tuple(CALISMA)]
    yabanci_dil: list[str] = Field(max_length=5)


SISTEM_PROMPT = """Sen bir insan kaynakları uzmanısın. Sana verilen iş ilanını okuyup
istenen bilgileri JSON olarak çıkarıyorsun. Kurallar:
- Sadece ilanda açıkça geçen bilgileri yaz, tahmin uydurma.
- teknik_beceriler: öğrenilerek kazanılan somut, mesleğe özgü beceriler: yazılım/program,
  programlama dili, makine/alet, sertifika/belge, ehliyet ve uzmanlık bilgisi
  (ör. "Python", "SAP", "Excel", "Forklift", "B Sınıfı Ehliyet"). Bu örnekler sadece
  açıklama içindir: SADECE ilan metninde gerçekten geçen becerileri yaz, örnekleri kopyalama.
  Herkesin yapabileceği genel görevler teknik beceri DEĞİLDİR, bunları yazma:
  temizlik yapmak, telefona bakmak, müşteriyle ilgilenmek, servis yapmak, ürün dizmek,
  paketleme, evrak takibi, düzen sağlamak. Kişisel özellikler (dikkatli, düzenli) de değildir.
  Her beceriyi kısa, standart adıyla ve doğru Türkçe yazımla yaz ("Microsoft Excel" yerine "Excel").
  Mesleğe özgü beceri yoksa boş liste [] döndür.
- sektor: pozisyonun YAPTIĞI İŞE göre seç, ilanı veren şirketin sektörüne göre değil
  (inşaat firmasındaki sekreter -> İdari İşler).
  ÖNEMLİ: güvenlik görevlisi, temizlik görevlisi, garson, komi, aşçı, barista, bulaşıkçı ve
  kat görevlisi HER ZAMAN "Hizmet/Güvenlik/Temizlik" sektörüdür (İdari İşler, Müşteri
  Hizmetleri veya Lojistik değil). Sektörler, açıklamaları ve örnek pozisyonlar:
  * Yazılım/Bilişim: yazılım geliştirme, IT destek, sistem/ağ, veri. Örn: yazılım geliştirici,
    IT destek uzmanı, sistem yöneticisi, veri analisti.
  * Mühendislik: mühendislik diplomasıyla yapılan tasarım/proje işleri. Örn: makine mühendisi,
    inşaat mühendisi, elektrik mühendisi, tahribatsız muayene uzmanı.
  * Satış: ürün/hizmet satışı ve müşteri kazanma. Örn: satış temsilcisi, satış danışmanı,
    mağaza satış elemanı, gayrimenkul danışmanı, bölge satış müdürü.
  * Pazarlama: marka, reklam, dijital pazarlama ve içerik. Örn: sosyal medya uzmanı,
    dijital pazarlama uzmanı, içerik üreticisi, marka yöneticisi.
  * Finans/Muhasebe: muhasebe, fatura, vergi, bordro, finans. Örn: muhasebe uzmanı,
    muhasebe sorumlusu, ön muhasebe elemanı, finans uzmanı, mali müşavir.
  * İnsan Kaynakları: işe alım, özlük, eğitim ve personel yönetimi. Örn: İK uzmanı,
    işe alım uzmanı, özlük işleri sorumlusu, bordro ve İK asistanı.
  * Sağlık: hasta bakımı ve sağlık hizmetleri. Örn: hemşire, doktor, fizyoterapist,
    eczane teknisyeni, hasta/yaşlı bakıcısı.
  * Eğitim: öğretim ve çocuk eğitimi. Örn: öğretmen, eğitmen, gölge öğretmen,
    anaokulu öğretmeni, kurs öğretmeni.
  * Lojistik: depolama, sevkiyat, taşıma ve tedarik. Örn: depo elemanı, sevkiyat sorumlusu,
    kurye, şoför, forklift operatörü, lojistik uzmanı.
  * Üretim: fabrikada üretim, montaj ve kalite. Örn: üretim operatörü, CNC operatörü,
    montaj elemanı, kalite kontrol elemanı, kaynakçı.
  * Müşteri Hizmetleri: müşteri soru/şikâyetlerine yanıt ve destek. Örn: çağrı merkezi
    temsilcisi, müşteri temsilcisi, müşteri destek uzmanı.
  * Tasarım: görsel, grafik, ürün ve iç mekân tasarımı. Örn: grafik tasarımcı,
    UI/UX tasarımcı, iç mimar, moda tasarımcısı.
  * Hukuk: hukuki işler. Örn: avukat, hukuk müşaviri, stajyer avukat, hukuk asistanı.
  * İdari İşler: ofis düzeni, sekreterya ve ofis içi destek. Örn: sekreter,
    ofis asistanı, yönetici asistanı, resepsiyonist, idari işler sorumlusu, arşiv elemanı.
  * Hizmet/Güvenlik/Temizlik: güvenlik, temizlik, yiyecek-içecek ve konaklama hizmetleri.
    Örn: güvenlik görevlisi, bekçi, temizlik görevlisi, kat görevlisi, garson, komi,
    aşçı, aşçı yardımcısı, barista, bulaşıkçı, çay ocağı görevlisi, çocuk bakıcısı.
    Garson, barista ve aşçı Lojistik DEĞİLDİR.
  * Diğer: yukarıdakilerin hiçbirine uymayan işler. Örn: kuaför, şantiye işçisi,
    tarım işçisi. Bir sektör uyuyorsa Diğer'i seçme.
- sosyal_beceriler: iletişim, takım çalışması, liderlik, analitik düşünme gibi kişisel yetkinlikler.
- seviye: "en az 5 yıl", "kıdemli" -> Senior; 2-4 yıl -> Mid; 0-1 yıl, "yeni mezun" -> Junior;
  stajyer ilanı -> Stajyer; müdür/yönetici/lider pozisyonu -> Yönetici; ipucu yoksa Belirtilmemiş.
- egitim: SADECE ilanda eğitim/mezuniyet şartı açıkça yazıyorsa doldur:
  "lise mezunu" -> Lise; "ön lisans", "meslek yüksekokulu", "MYO", "2 yıllık" -> Ön Lisans;
  "üniversite/lisans/fakülte mezunu", "4 yıllık" -> Lisans; "yüksek lisans", "master" ->
  Yüksek Lisans; "doktora" -> Doktora. Birden fazla düzey yazıyorsa en düşüğünü seç
  ("lise veya üniversite mezunu" -> Lise). İlanda eğitimden hiç söz edilmiyorsa
  Belirtilmemiş seç; pozisyona veya kıdeme bakarak eğitim düzeyi TAHMİN ETME.
- calisma_sekli: "uzaktan/remote" -> Uzaktan, "hibrit" -> Hibrit, "iş yerinde/ofiste" -> Ofis.
- yabanci_dil: sadece dil adları (ör. "İngilizce").
- Listelerde değer yoksa boş liste [] döndür."""


def analiz_et(metin: str, model: str = config.ANA_MODEL, deneme: int = 2):
    """Tek bir ilan metnini analiz eder.

    Dönüş: (sonuc_dict veya None, gecen_sure_sn, gecerli_mi)
    """
    metin = metin[: config.MAKS_METIN_KARAKTER]
    t0 = time.perf_counter()
    for i in range(deneme):
        # num_predict: tek yanıt için üst sınır (normal yanıt ~200-400 token). İlk deneme bozuk
        # çıkarsa ikinci denemede tekrarları cezalandırıp yeniden dene.
        secenek = {"temperature": 0, "num_ctx": 8192, "num_predict": 1024}
        if i > 0:
            secenek.update({"temperature": 0.2, "repeat_penalty": 1.15})
        try:
            yanit = ollama.chat(
                model=model,
                messages=[{"role": "system", "content": SISTEM_PROMPT},
                          {"role": "user", "content": f"İŞ İLANI:\n{metin}"}],
                format=IlanAnalizi.model_json_schema(),
                options=secenek,
            )
            veri = IlanAnalizi.model_validate_json(yanit["message"]["content"])
            return veri.model_dump(), round(time.perf_counter() - t0, 2), True
        except (ValidationError, json.JSONDecodeError):
            continue  # bozuk/eksik çıktı -> bir kez daha dene
    return None, round(time.perf_counter() - t0, 2), False
