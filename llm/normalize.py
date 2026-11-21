"""Aynı becerinin farklı yazımlarını tek isimde birleştirir.
Örn: "JS", "Javascript", "javascript" -> "JavaScript"
Yeni eşleşme görürsen ESANLAMLILAR sözlüğüne ekle.
"""
import re
from collections import Counter

ESANLAMLILAR = {
    "js": "JavaScript", "javascript": "JavaScript", "ts": "TypeScript", "typescript": "TypeScript",
    "reactjs": "React", "react.js": "React", "react": "React",
    "nodejs": "Node.js", "node.js": "Node.js", "node": "Node.js",
    "vuejs": "Vue.js", "vue.js": "Vue.js", "vue": "Vue.js",
    "angularjs": "Angular", "angular": "Angular",
    "c#": "C#", "csharp": "C#", "c sharp": "C#",
    ".net": ".NET", "dotnet": ".NET", ".net core": ".NET", "asp.net core": ".NET", "asp.net": ".NET",
    "mssql": "SQL Server", "ms sql": "SQL Server", "ms-sql": "SQL Server", "sql server": "SQL Server",
    "microsoft sql server": "SQL Server", "t-sql": "SQL Server",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "postgre-sql": "PostgreSQL", "postgre sql": "PostgreSQL",
    "mysql": "MySQL", "mongodb": "MongoDB", "mongo": "MongoDB",
    "ms excel": "Excel", "microsoft excel": "Excel", "excel": "Excel", "ileri düzey excel": "Excel",
    "ms office": "MS Office", "microsoft office": "MS Office", "office programları": "MS Office",
    "git": "Git", "github": "Git", "gitlab": "Git",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes", "docker": "Docker",
    "aws": "AWS", "amazon web services": "AWS", "azure": "Azure", "microsoft azure": "Azure",
    "gcp": "Google Cloud", "google cloud": "Google Cloud",
    "ml": "Makine Öğrenmesi", "machine learning": "Makine Öğrenmesi", "makine öğrenmesi": "Makine Öğrenmesi",
    "yapay zeka": "Yapay Zeka", "ai": "Yapay Zeka", "artificial intelligence": "Yapay Zeka",
    "rest": "REST API", "rest api": "REST API", "restful": "REST API", "restful api": "REST API", "web api": "REST API",
    "oop": "OOP", "nesne yönelimli programlama": "OOP", "object oriented programming": "OOP",
    "html": "HTML", "html5": "HTML", "css": "CSS", "css3": "CSS",
    "python": "Python", "java": "Java", "sql": "SQL", "sap": "SAP", "autocad": "AutoCAD",
    "power bi": "Power BI", "powerbi": "Power BI", "seo": "SEO",
    "scrum": "Agile/Scrum", "agile": "Agile/Scrum", "çevik": "Agile/Scrum", "agile/scrum": "Agile/Scrum",
    "ingilizce": "İngilizce", "english": "İngilizce", "almanca": "Almanca", "german": "Almanca",
}


# Kalıp kuralları: küçük harfe çevrilmiş beceri adında desen geçiyorsa standart ada eşlenir.
# Sıra önemli: ilk eşleşen kural kazanır. ("Sabırlı ve dikkatli" -> Sabır)
TEKNIK_KALIPLAR = [
    (r"^ms office|microsoft office|^office\b|^ms (word|outlook|powerpoint)|^word$|^outlook$", "MS Office"),
    (r"e-?fatura|e-?arşiv", "E-Fatura / E-Arşiv"),
    (r"netsis", "Netsis"), (r"logo (tiger|go)|^logo$", "Logo"),
    (r"muhasebe (ve erp )?program", "Muhasebe Programları"),
    (r"özel güvenlik kimli", "Özel Güvenlik Kimliği"),
    (r"^crm", "CRM"), (r"^erp", "ERP"),
    (r"b sınıfı|ehliyet", "Ehliyet"),
    (r"bahçe bakım", "Bahçe Bakımı"),
]
SOSYAL_KALIPLAR = [
    (r"sabır", "Sabır"),
    (r"analitik", "Analitik Düşünme"),
    (r"problem|çözüm odaklı|kriz", "Problem Çözme"),
    (r"takım|ekip|işbirliği|beraber çalış|koordine|koordinasyon", "Takım Çalışması"),
    (r"liderlik", "Liderlik"),
    (r"ikna|satış", "İkna Kabiliyeti"),
    (r"müşteri", "Müşteri Odaklılık"),
    (r"iletişim|ifade etme|anlatım|diksiyon|insan ilişki|dinleme", "İletişim"),
    (r"sorumluluk", "Sorumluluk Sahibi"),
    (r"dikkat|titiz|detay", "Dikkat ve Titizlik"),
    (r"planla|planlı|organizasyon|zaman yönetimi|önceliklendir|takip", "Planlama ve Organizasyon"),
    (r"disiplin|diziplin", "Disiplin"),
    (r"düzen", "Düzenlilik"),
    (r"güvenilir", "Güvenilirlik"),
    (r"güler ?yüz|yardımsever", "Güler Yüzlülük"),
    (r"hızlı|seri çalış|tempo", "Hızlı Çalışma"),
    (r"yaratıcı", "Yaratıcılık"),
    (r"uyum|esnek", "Uyum ve Esneklik"),
    (r"öğrenmeye", "Öğrenmeye Açıklık"),
]
# Tek başına bir beceri anlatmayan, LLM'in görev tanımından aldığı genel kelimeler
TEKNIK_KALDIR = {"yazılım", "makine", "üretim", "güvenlik", "güvenlik görevi", "e-posta",
                 "elektronik", "arşiv", "fatura", "muhasebe", "telefon", "temizlik", "bilgisayar"}


def anahtar(s: str) -> str:
    s = s.strip().replace("İ", "i").replace("I", "ı").lower().replace("̇", "")
    return re.sub(r"\s+", " ", s)


def _buyuk_bas(s: str) -> str:
    """Türkçeye uygun ilk harf büyütme (i -> İ); geri kalanına dokunmaz (SQL, iOS gibi)."""
    if not s:
        return s
    ilk = {"i": "İ", "ı": "I"}.get(s[0], s[0].upper())
    return ilk + s[1:]


def normalize_et(beceri: str, tur: str = "teknik") -> str | None:
    """Tek beceri adını standartlaştırır; atılması gerekiyorsa None döndürür."""
    beceri = re.sub(r"\s+", " ", str(beceri)).strip().strip(".,;:-•·")
    if not beceri:
        return None
    k = anahtar(beceri)
    if k in ESANLAMLILAR:
        return ESANLAMLILAR[k]
    if tur == "teknik" and k in TEKNIK_KALDIR:
        return None
    kaliplar = {"teknik": TEKNIK_KALIPLAR, "sosyal": SOSYAL_KALIPLAR}.get(tur, [])
    for desen, standart in kaliplar:
        if re.search(desen, k):
            return standart
    return _buyuk_bas(beceri)


def listeleri_normalize_et(listeler, tur: str = "teknik"):
    """Liste-listesi alır; eşanlamlıları ve kalıpları birleştirir, büyük/küçük harf farklarını
    en sık görülen yazıma çevirir, aynı ilandaki tekrarları atar.
    tur: "teknik", "sosyal" veya "dil"."""
    ilk = [[n for n in (normalize_et(b, tur) for b in (l or [])) if n] for l in listeler]
    yazimlar = {}
    for l in ilk:
        for b in l:
            yazimlar.setdefault(anahtar(b), Counter())[b] += 1
    standart = {k: c.most_common(1)[0][0] for k, c in yazimlar.items()}
    sonuc = []
    for l in ilk:
        goruldu, yeni = set(), []
        for b in l:
            s = standart[anahtar(b)]
            if s not in goruldu:
                goruldu.add(s)
                yeni.append(s)
        sonuc.append(yeni)
    return sonuc
