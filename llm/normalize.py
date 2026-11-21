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


def anahtar(s: str) -> str:
    s = s.strip().replace("İ", "i").lower().replace("̇", "")
    return re.sub(r"\s+", " ", s)


def normalize_et(beceri: str) -> str:
    beceri = str(beceri).strip().strip(".,;:-•·")
    return ESANLAMLILAR.get(anahtar(beceri), beceri)


def listeleri_normalize_et(listeler):
    """Liste-listesi alır; eşanlamlıları birleştirir, büyük/küçük harf farklarını
    en sık görülen yazıma çevirir, aynı ilandaki tekrarları atar."""
    ilk = [[normalize_et(b) for b in (l or []) if str(b).strip()] for l in listeler]
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
