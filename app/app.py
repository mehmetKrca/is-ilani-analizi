"""Web arayüzü (Streamlit).

Çalıştırmak için proje klasöründe:  streamlit run app/app.py
Tema ayarları: .streamlit/config.toml
"""
import html
import json
import sys
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from llm.normalize import listeleri_normalize_et  # noqa: E402

st.set_page_config(page_title="İş Piyasası Analizi", page_icon="📊", layout="wide")

# ------------------------------------------------------------------ görünüm
ANA = "#2F5BD3"        # tek ana renk (config.toml'daki primaryColor ile aynı)
ANA_ACIK = "#E8EEFB"
METIN = "#1F2937"
SOLUK = "#5B6474"
IZGARA = "#EEF1F6"
FONT = '"Source Sans Pro", "Source Sans 3", "Segoe UI", sans-serif'

CSS = f"""
<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stAppDeployButton"], .stDeployButton {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1280px; }}
h1 {{ font-size: 1.85rem !important; font-weight: 700 !important; padding-bottom: 0 !important; }}
.alt-baslik {{ color: {SOLUK}; font-size: 1.02rem; margin: -0.35rem 0 1.1rem 0; }}
[data-testid="stMetric"] {{ background: #FFFFFF; padding: 0.7rem 1rem 0.6rem 1rem; min-height: 0; }}
[data-testid="stMetricLabel"] p {{ font-size: 0.86rem; color: {SOLUK}; }}
[data-testid="stMetricValue"] {{ font-size: 1.65rem; font-weight: 700; color: {METIN}; }}
.stTabs [data-baseweb="tab"] p {{ font-size: 0.98rem; font-weight: 600; }}
.kart-baslik {{ font-weight: 650; font-size: 1.02rem; color: {METIN}; margin: 0 0 0.2rem 0; }}
.cikarim {{ background: #F3F6FD; border-left: 3px solid {ANA}; border-radius: 6px;
           padding: 0.45rem 0.75rem; margin: 0.15rem 0 0.4rem 0; color: #334155; font-size: 0.93rem; }}
.chip {{ display: inline-block; padding: 0.2rem 0.65rem; margin: 0.15rem 0.3rem 0.15rem 0;
        border-radius: 999px; font-size: 0.87rem; font-weight: 500; line-height: 1.5; }}
.chip-teknik {{ background: #E6ECFB; color: #1E3F9A; }}
.chip-sosyal {{ background: #E3F4EC; color: #17694A; }}
.chip-dil    {{ background: #FDF1DC; color: #8A5A00; }}
.chip-yok    {{ color: {SOLUK}; font-size: 0.9rem; }}
.bilgi-kart {{ border: 1px solid #E3E7EE; border-radius: 10px; padding: 0.8rem 1rem; height: 100%; background: #FFF; }}
.bilgi-kart .etiket {{ font-size: 0.84rem; color: {SOLUK}; margin-bottom: 0.15rem; }}
.bilgi-kart .deger  {{ font-size: 1.2rem; font-weight: 650; color: {METIN}; line-height: 1.3; }}
.ozet {{ width: 100%; font-size: 0.9rem; border-collapse: collapse; border: none !important; }}
.ozet tr {{ border: none !important; border-bottom: 1px solid #E3E7EE !important; background: transparent !important; }}
.ozet tr:last-child {{ border-bottom: none !important; }}
.ozet td {{ padding: 0.35rem 0 !important; vertical-align: top; border: none !important; background: transparent !important; }}
.ozet td:first-child {{ color: {SOLUK}; padding-right: 0.6rem; white-space: nowrap; }}
.ozet td:last-child {{ font-weight: 600; text-align: right; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

GRAFIK_AYAR = {"displayModeBar": False}


def stil(fig, yukseklik: int):
    """Tüm grafiklere ortak görünüm: aynı font, az ızgara, eksen başlığı yok, sade hover."""
    fig.update_layout(
        template="plotly_white", height=yukseklik, showlegend=False,
        font=dict(family=FONT, size=13, color=METIN),
        margin=dict(l=0, r=24, t=6, b=0), bargap=0.32,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="white", bordercolor="#D5DBE6", font=dict(family=FONT, size=13)),
    )
    fig.update_xaxes(title=None, showgrid=False, zeroline=False, showline=False, ticks="")
    fig.update_yaxes(title=None, showgrid=False, zeroline=False, showline=False, ticks="")
    return fig


def yatay_bar(t: pd.DataFrame, deger: str, etiket: str, birim: str = "ilan"):
    """Yatay çubuk grafik. t yukarıdan aşağıya gösterilecek sırada verilir."""
    t = t.iloc[::-1]
    fig = px.bar(t, x=deger, y=etiket, orientation="h", color_discrete_sequence=[ANA])
    if birim == "%":
        yazi, hover = t[deger].map(lambda v: f"%{v:.0f}"), "%{x:.1f}% ilan"
    elif birim == "sn":
        yazi, hover = t[deger].map(lambda v: f"{ondalik(v, 2)} sn"), "%{x:.2f} sn"
    else:
        yazi, hover = t[deger].map(lambda v: f"{v:.0f}"), "%{x} ilan"
    fig.update_traces(text=yazi, textposition="outside", cliponaxis=False, marker_line_width=0,
                      textfont=dict(size=12, color=SOLUK),
                      hovertemplate="<b>%{y}</b><br>" + hover + "<extra></extra>")
    stil(fig, max(110, 32 * len(t) + 24))  # az çubuk varsa grafik de kısa olsun, çubuklar şişmesin
    fig.update_xaxes(showticklabels=False, range=[0, t[deger].max() * 1.15 if len(t) else 1])
    return fig


def dikey_bar(t: pd.DataFrame, deger: str, etiket: str):
    fig = px.bar(t, x=etiket, y=deger, color_discrete_sequence=[ANA],
                 text=t[deger].map(lambda v: str(v) if v else ""))
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0,
                      textfont=dict(size=12, color=SOLUK),
                      hovertemplate="<b>%{x}</b><br>%{y} ilan<extra></extra>")
    stil(fig, 320)
    fig.update_yaxes(showgrid=True, gridcolor=IZGARA, showticklabels=False)
    fig.update_xaxes(type="category")
    return fig


def grafik_karti(baslik: str, cikarim: str | None, fig=None):
    """Kenarlıklı kart: başlık + otomatik çıkarım cümlesi + grafik."""
    with st.container(border=True):
        st.markdown(f'<div class="kart-baslik">{baslik}</div>', unsafe_allow_html=True)
        if cikarim:
            st.markdown(f'<div class="cikarim">💡 {cikarim}</div>', unsafe_allow_html=True)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", config=GRAFIK_AYAR)


def sayfa_basligi(baslik: str, aciklama: str):
    st.title(baslik)
    st.markdown(f'<div class="alt-baslik">{aciklama}</div>', unsafe_allow_html=True)


def kpi(sutun, etiket: str, deger, yardim: str | None = None):
    sutun.metric(etiket, deger, help=yardim, border=True)


def e(metin) -> str:
    """Veriden gelen metni HTML içine güvenle koymak için."""
    return html.escape(str(metin))


def ondalik(x: float, basamak: int = 1) -> str:
    return f"{x:.{basamak}f}".replace(".", ",")


# Türkçe yüzde ekleri: "%32'si", "%32'sinde", "%30'unu" (sayının okunuşuna göre ses uyumu)
_BIRLER = {1: "i", 2: "si", 3: "ü", 4: "ü", 5: "i", 6: "sı", 7: "si", 8: "i", 9: "u"}
_ONLAR = {0: "ı", 10: "u", 20: "si", 30: "u", 40: "ı", 50: "si", 60: "ı", 70: "i", 80: "i", 90: "ı"}


def yuzde(oran: float, hal: str = "") -> str:
    """oran: 0-100. hal: '' -> %32'si, 'de' -> %32'sinde, 'i' -> %32'sini."""
    n = int(round(oran))
    if n == 100:
        ek = "ü"
    elif n % 10:
        ek = _BIRLER[n % 10]
    else:
        ek = _ONLAR[n % 100]
    unlu = ek[-1]
    if hal == "de":
        ek += "n" + ("da" if unlu in "ıu" else "de")
    elif hal == "i":
        ek += "n" + unlu
    return f"%{n}'{ek}"


def chipler(liste, sinif: str) -> str:
    if not liste:
        return '<span class="chip-yok">Belirtilmemiş</span>'
    return "".join(f'<span class="chip chip-{sinif}">{e(b)}</span>' for b in liste)


# ------------------------------------------------------------------ veri
def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0


JSONL_ADI = config.ANA_MODEL.replace(":", "_").replace("/", "_") + ".jsonl"
# Yerelde tam veri (data/raw + data/processed) varsa o kullanılır. Yoksa (ör. Streamlit Cloud)
# repodaki ilan metni içermeyen hafif kopya: data/public (python -m llm.disa_aktar ile üretilir).
if (config.RAW_DIR / "ilanlar.csv").exists() and (config.PROCESSED_DIR / JSONL_ADI).exists():
    VERI_KAYNAGI = "yerel"
    RAW_DOSYA = config.RAW_DIR / "ilanlar.csv"
    JSONL = config.PROCESSED_DIR / JSONL_ADI
    IST_DOSYA = config.RAW_DIR / "scraping_istatistik.csv"
else:
    VERI_KAYNAGI = "public"
    RAW_DOSYA = config.PUBLIC_DIR / "ilanlar.csv"
    JSONL = config.PUBLIC_DIR / JSONL_ADI
    IST_DOSYA = config.PUBLIC_DIR / "scraping_istatistik.csv"
BILGI_DOSYA = config.PUBLIC_DIR / "bilgi.json"
SEVIYE_SIRA = ["Stajyer", "Junior", "Mid", "Senior", "Yönetici", "Belirtilmemiş"]


@st.cache_data
def veri_yukle(raw_mtime: float, jsonl_mtime: float) -> pd.DataFrame | None:
    if not RAW_DOSYA.exists() or not JSONL.exists():
        return None
    ham = pd.read_csv(RAW_DOSYA, encoding="utf-8-sig", dtype=str).fillna("")
    satirlar = []
    with open(JSONL, encoding="utf-8") as f:
        for s in f:
            if not s.strip():
                continue
            r = json.loads(s)
            if r["gecerli"]:
                satirlar.append({"ilan_id": r["ilan_id"], **r["sonuc"]})
    if not satirlar:
        return None
    llm = pd.DataFrame(satirlar).drop_duplicates("ilan_id", keep="last")
    df = ham[["ilan_id", "baslik", "sirket", "sehir", "url", "yayin_tarihi"]].merge(llm, on="ilan_id")
    df["sehir"] = (df["sehir"].str.split("(").str[0].str.strip()
                   .replace("", "Belirtilmemiş"))
    df["teknik_beceriler"] = listeleri_normalize_et(df["teknik_beceriler"])
    df["sosyal_beceriler"] = listeleri_normalize_et(df["sosyal_beceriler"])
    df["yabanci_dil"] = listeleri_normalize_et(df["yabanci_dil"])
    return df


@st.cache_data
def veri_ozeti(raw_mtime: float, jsonl_mtime: float) -> dict:
    ozet = {"toplanan": 0, "analiz": 0, "siteler": "—", "son": "—"}
    if RAW_DOSYA.exists():
        ham = pd.read_csv(RAW_DOSYA, encoding="utf-8-sig", dtype=str).fillna("")
        ozet["toplanan"] = len(ham)
        adlar = [config.SITELER.get(s, {}).get("taban_url", s) for s in ham["site"].unique() if s]
        ozet["siteler"] = ", ".join(a.replace("https://", "").replace("www.", "") for a in adlar) or "—"
    if JSONL.exists():
        with open(JSONL, encoding="utf-8") as f:
            ozet["analiz"] = len({json.loads(s)["ilan_id"] for s in f if s.strip()})
    zamanlar = [m for m in (raw_mtime, jsonl_mtime) if m]
    if VERI_KAYNAGI == "public" and BILGI_DOSYA.exists():
        # bulutta dosya tarihleri repo klonlanma anıdır; gerçek tarih bilgi.json'da
        ozet["son"] = json.loads(BILGI_DOSYA.read_text(encoding="utf-8")).get("guncelleme", "—")
    elif zamanlar:
        ozet["son"] = datetime.fromtimestamp(max(zamanlar)).strftime("%d.%m.%Y %H:%M")
    return ozet


def beceri_sikligi(seri: pd.Series, n: int) -> pd.DataFrame:
    sayac = Counter(b for liste in seri for b in liste)
    t = pd.DataFrame(sayac.most_common(n), columns=["beceri", "ilan"])
    t["oran"] = (t["ilan"] / max(len(seri), 1) * 100).round(1)
    return t


# ------------------------------------------------------------------ sayfalar
def sayfa_genel(df):
    sayfa_basligi("📊 Genel Bakış",
                  "Toplanan iş ilanlarının sektör, şehir, seviye ve çalışma şekline göre dağılımı.")
    iller = df.loc[df["sehir"] != "Belirtilmemiş", "sehir"]
    c = st.columns(4)
    kpi(c[0], "Analiz edilen ilan", len(df))
    kpi(c[1], "Farklı şirket", df["sirket"].replace("", pd.NA).nunique())
    kpi(c[2], "Farklı il", iller.nunique())
    uzak = df["calisma_sekli"].isin(["Uzaktan", "Hibrit"]).mean() * 100
    kpi(c[3], "Uzaktan / Hibrit", f"%{uzak:.0f}", "Uzaktan veya hibrit çalışma sunan ilanların oranı")

    t1, t2, t3 = st.tabs(["Sektör ve Şehir", "Seviye ve Çalışma Şekli", "İlan Listesi"])
    with t1:
        sol, sag = st.columns(2)
        with sol:
            sek = df["sektor"].value_counts().reset_index()
            p = sek["count"].iloc[0] / len(df) * 100
            grafik_karti("Sektörlere göre ilan sayısı",
                         f"En çok ilan <b>{e(sek['sektor'].iloc[0])}</b> sektöründe: ilanların {yuzde(p)}.",
                         yatay_bar(sek, "count", "sektor"))
        with sag:
            seh = iller.value_counts().head(10).reset_index()
            if seh.empty:
                grafik_karti("En çok ilan olan 10 il", "İl bilgisi olan ilan yok.")
            else:
                p1 = seh["count"].iloc[0] / len(df) * 100
                p3 = seh["count"].head(3).sum() / len(df) * 100
                ilk3 = ", ".join(e(x) for x in seh["sehir"].head(3))
                grafik_karti("En çok ilan olan 10 il",
                             f"İlanların {yuzde(p1)} <b>{e(seh['sehir'].iloc[0])}</b> ilinde; ilk üç il "
                             f"({ilk3}) toplamın {yuzde(p3, 'i')} oluşturuyor.",
                             yatay_bar(seh, "count", "sehir"))
    with t2:
        sol, sag = st.columns(2)
        with sol:
            sev = df["seviye"].value_counts().reindex(SEVIYE_SIRA, fill_value=0).reset_index()
            belirsiz = (df["seviye"] == "Belirtilmemiş").mean() * 100
            belirli = df.loc[df["seviye"] != "Belirtilmemiş", "seviye"]
            cumle = f"İlanların {yuzde(belirsiz, 'de')} seviye belirtilmemiş."
            if not belirli.empty:
                cumle += f" Belirtilenler arasında en yaygın seviye: <b>{e(belirli.mode()[0])}</b>."
            grafik_karti("Pozisyon seviyesi", cumle, yatay_bar(sev, "count", "seviye"))
        with sag:
            cal = df["calisma_sekli"].value_counts().reset_index()
            p = cal["count"].iloc[0] / len(df) * 100
            grafik_karti("Çalışma şekli",
                         f"En yaygın çalışma şekli <b>{e(cal['calisma_sekli'].iloc[0])}</b>: ilanların "
                         f"{yuzde(p)}. Uzaktan ve hibrit ilanların toplam payı %{uzak:.0f}.",
                         yatay_bar(cal, "count", "calisma_sekli"))
    with t3:
        ara = st.text_input("Ara", placeholder="Pozisyon, şirket veya beceri yaz...",
                            label_visibility="collapsed")
        t = df
        if ara:
            m = (df["baslik"].str.contains(ara, case=False, regex=False)
                 | df["sirket"].str.contains(ara, case=False, regex=False)
                 | df["teknik_beceriler"].apply(lambda l: any(ara.lower() in b.lower() for b in l)))
            t = df[m]
        st.caption(f"{len(t)} ilan")
        st.dataframe(t[["baslik", "sirket", "sehir", "sektor", "seviye", "calisma_sekli", "url"]],
                     width="stretch", hide_index=True, height=460,
                     column_config={"baslik": "Pozisyon", "sirket": "Şirket", "sehir": "İl",
                                    "sektor": "Sektör", "seviye": "Seviye",
                                    "calisma_sekli": "Çalışma şekli",
                                    "url": st.column_config.LinkColumn("Link", display_text="aç")})


def beceri_filtreleri(df):
    """Beceri Analizi filtreleri (kenar çubuğunda)."""
    st.sidebar.markdown("**Filtreler**")
    sektor = st.sidebar.multiselect("Sektör", sorted(df["sektor"].unique()), placeholder="Tümü")
    sehir = st.sidebar.multiselect("İl", df["sehir"].value_counts().index.tolist(), placeholder="Tümü")
    seviye = st.sidebar.multiselect("Seviye", [s for s in SEVIYE_SIRA if s in set(df["seviye"])],
                                    placeholder="Tümü")
    t = df
    if sektor:
        t = t[t["sektor"].isin(sektor)]
    if sehir:
        t = t[t["sehir"].isin(sehir)]
    if seviye:
        t = t[t["seviye"].isin(seviye)]
    return t


def sayfa_beceri(t):
    sayfa_basligi("🧠 Beceri Analizi",
                  "İlanlarda en çok aranan teknik ve sosyal beceriler, diller ve deneyim beklentisi. "
                  "Filtreler kenar çubuğunda.")
    if t.empty:
        st.warning("Bu filtreye uyan ilan yok. Kenar çubuğundaki filtreleri gevşet.")
        return
    dil_orani = (t["yabanci_dil"].str.len() > 0).mean() * 100
    c = st.columns(4)
    kpi(c[0], "Filtreye uyan ilan", len(t))
    kpi(c[1], "Farklı teknik beceri", len({b for l in t["teknik_beceriler"] for b in l}))
    kpi(c[2], "İlan başına teknik beceri", ondalik(t["teknik_beceriler"].str.len().mean()))
    kpi(c[3], "Yabancı dil isteyen", f"%{dil_orani:.0f}")

    tek = beceri_sikligi(t["teknik_beceriler"], 20)
    t1, t2, t3, t4 = st.tabs(["Teknik", "Sosyal & Dil", "Birlikte İstenenler", "Deneyim"])
    with t1:
        if tek.empty:
            grafik_karti("En çok aranan teknik beceriler", "Bu ilanlarda teknik beceri bulunamadı.")
        else:
            cumle = (f"En çok aranan teknik beceri: <b>{e(tek['beceri'].iloc[0])}</b>, "
                     f"ilanların {yuzde(tek['oran'].iloc[0], 'de')}.")
            if len(tek) >= 3:
                cumle += f" Onu <b>{e(tek['beceri'].iloc[1])}</b> ve <b>{e(tek['beceri'].iloc[2])}</b> izliyor."
            grafik_karti("En çok aranan 20 teknik beceri (ilanların yüzdesi)", cumle,
                         yatay_bar(tek, "oran", "beceri", "%"))
    with t2:
        sol, sag = st.columns(2)
        with sol:
            sos = beceri_sikligi(t["sosyal_beceriler"], 10)
            if sos.empty:
                grafik_karti("En çok aranan sosyal beceriler", "Bu ilanlarda sosyal beceri bulunamadı.")
            else:
                grafik_karti("En çok aranan sosyal beceriler (%)",
                             f"En sık istenen sosyal beceri: <b>{e(sos['beceri'].iloc[0])}</b>, "
                             f"ilanların {yuzde(sos['oran'].iloc[0], 'de')}.",
                             yatay_bar(sos, "oran", "beceri", "%"))
        with sag:
            dil = beceri_sikligi(t["yabanci_dil"], 6)
            if dil.empty:
                grafik_karti("Yabancı dil isteme oranı", "Bu ilanların hiçbirinde yabancı dil istenmiyor.")
            else:
                grafik_karti("Yabancı dil isteme oranı (%)",
                             f"İlanların {yuzde(dil_orani, 'de')} yabancı dil isteniyor; en çok "
                             f"<b>{e(dil['beceri'].iloc[0])}</b>.",
                             yatay_bar(dil, "oran", "beceri", "%"))
    with t3:
        ust = tek["beceri"].head(12).tolist()
        if len(ust) < 2:
            grafik_karti("Birlikte istenen beceriler", "Karşılaştırma için yeterli teknik beceri yok.")
        else:
            matris = pd.DataFrame(0, index=ust, columns=ust)
            for liste in t["teknik_beceriler"]:
                for a, b in combinations([x for x in liste if x in ust], 2):
                    matris.loc[a, b] += 1
                    matris.loc[b, a] += 1
            ciftler = [(matris.loc[a, b], a, b) for a, b in combinations(ust, 2)]
            en = max(ciftler)
            cumle = (f"En sık birlikte istenen ikili: <b>{e(en[1])} + {e(en[2])}</b> ({en[0]} ilan)."
                     if en[0] else "Bu beceriler aynı ilanda pek birlikte geçmiyor.")
            yazi = matris.astype(object).where(matris > 0, "").astype(str)
            fig = px.imshow(matris, color_continuous_scale=[[0, "#FFFFFF"], [1, ANA]], aspect="auto")
            fig.update_traces(text=yazi.values, texttemplate="%{text}", xgap=2, ygap=2,
                              hovertemplate="<b>%{y} + %{x}</b><br>%{z} ilan<extra></extra>")
            stil(fig, 470)
            fig.update_layout(coloraxis_showscale=False)
            fig.update_xaxes(side="bottom", tickangle=-35)
            sol, sag = st.columns([3, 2])
            with sol:
                grafik_karti("Aynı ilanda birlikte geçme sayısı (en sık 12 beceri)", cumle, fig)
            with sag:
                with st.container(border=True):
                    st.markdown('<div class="kart-baslik">Bir beceriyi isteyenler başka ne istiyor?</div>',
                                unsafe_allow_html=True)
                    secim = st.selectbox("Beceri", ust, label_visibility="collapsed")
                    alt = t[t["teknik_beceriler"].apply(lambda l: secim in l)]
                    yan = beceri_sikligi(alt["teknik_beceriler"].apply(
                        lambda l: [b for b in l if b != secim]), 8)
                    if yan.empty:
                        st.markdown(f'<div class="cikarim">💡 <b>{e(secim)}</b> isteyen ilanlarda başka '
                                    'teknik beceri geçmiyor.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="cikarim">💡 <b>{e(secim)}</b> isteyen {len(alt)} ilanda '
                                    f'en sık eşlik eden beceri: <b>{e(yan["beceri"].iloc[0])}</b> '
                                    f'({yuzde(yan["oran"].iloc[0], "de")}).</div>', unsafe_allow_html=True)
                        st.plotly_chart(yatay_bar(yan, "oran", "beceri", "%"), width="stretch",
                                        config=GRAFIK_AYAR)
    with t4:
        yil = t["deneyim_yil"].astype(int)
        sartli = yil[yil > 0]
        if sartli.empty:
            grafik_karti("İstenen minimum deneyim", "Bu ilanların hiçbirinde deneyim şartı belirtilmemiş.")
        else:
            dag = (sartli.clip(upper=10).map(lambda v: "10+" if v >= 10 else str(v))
                   .value_counts().reindex([str(i) for i in range(1, 10)] + ["10+"], fill_value=0)
                   .rename_axis("yil").reset_index(name="ilan"))  # 1..10+ hepsi, eksen tutarlı kalsın
            sartsiz = (yil == 0).mean() * 100
            grafik_karti("İstenen minimum deneyim (yıl, deneyim şartı olan ilanlar)",
                         f"İlanların {yuzde(sartsiz, 'de')} deneyim şartı yok; şart koyanlarda ortanca "
                         f"beklenti <b>{ondalik(sartli.median(), 0)} yıl</b>.",
                         dikey_bar(dag, "ilan", "yil"))


def sayfa_yontem():
    sayfa_basligi("⚖️ Yöntem Karşılaştırması",
                  "İki web scraping yönteminin, Selenium ve BeautifulSoup'un, aynı ilanlar üzerinde "
                  "hız ve başarı karşılaştırması.")
    st.warning("**Not: Kariyer.net iki yöntemi de engelledi.** BeautifulSoup isteği HTTP 403 "
               "(erişim reddedildi) ile yanıtlandı; Selenium ile açılan tarayıcıda \"robot musun\" "
               "doğrulaması çıktı ve elle geçilmeye çalışılmasına rağmen ilanlar yüklenmedi. "
               "Sitenin bot korumasını atlatmaya çalışılmadı; veri, robots.txt kurallarına uyularak "
               "isbul.net'ten toplandı.", icon="🛡️")
    if not IST_DOSYA.exists():
        st.info("Scraping istatistiği yok. Scraper'lar çalışınca otomatik oluşur.")
        return
    ham = pd.read_csv(IST_DOSYA, encoding="utf-8-sig")
    s = ham[(ham["site"] != "kariyer") & (ham["deneme"] > 0)]  # Kariyer.net yukarıdaki notta
    if s.empty:
        st.info("Henüz başarılı bir scraping çalışması yok.")
        return
    ozet = s.groupby("yontem").agg(deneme=("deneme", "sum"), basarili=("basarili", "sum"),
                                   hata=("hata", "sum"), engellenen=("engellenen", "sum"),
                                   sure=("toplam_sure_sn", "sum")).reset_index()
    ozet["basari"] = (ozet["basarili"] / ozet["deneme"].clip(lower=1) * 100).round(1)
    ozet["ilan_basina_sn"] = (ozet["sure"] / ozet["basarili"].clip(lower=1)).round(2)
    ozet["yontem"] = ozet["yontem"].map({"beautifulsoup": "BeautifulSoup", "selenium": "Selenium"}) \
        .fillna(ozet["yontem"])
    hiz = ozet.set_index("yontem")["ilan_basina_sn"]

    c = st.columns(4)
    kpi(c[0], "Toplanan benzersiz ilan", len(pd.read_csv(RAW_DOSYA, encoding="utf-8-sig"))
        if RAW_DOSYA.exists() else 0)
    kpi(c[1], "BeautifulSoup · ilan başına", f"{ondalik(hiz.get('BeautifulSoup', 0), 2)} sn")
    kpi(c[2], "Selenium · ilan başına", f"{ondalik(hiz.get('Selenium', 0), 2)} sn")
    kat = hiz.get("Selenium", 0) / hiz.get("BeautifulSoup", 1) if hiz.get("BeautifulSoup") else 0
    kpi(c[3], "Hız farkı", f"{ondalik(kat)} kat" if kat else "—", "Selenium süresi / BeautifulSoup süresi")

    t1, t2 = st.tabs(["Karşılaştırma", "Çalışma Kayıtları"])
    with t1:
        sol, sag = st.columns(2)
        with sol:
            cumle = (f"BeautifulSoup aynı ilanları Selenium'dan <b>{ondalik(kat)} kat</b> hızlı çekti "
                     f"(ilan başına {ondalik(hiz['BeautifulSoup'], 2)} sn'ye karşı "
                     f"{ondalik(hiz['Selenium'], 2)} sn)." if kat else None)
            grafik_karti("İlan başına süre (sn, bekleme hariç)", cumle,
                         yatay_bar(ozet, "ilan_basina_sn", "yontem", "sn"))  # iki grafikte aynı sıra
        with sag:
            if (ozet["basari"] == 100).all() and ozet["engellenen"].sum() == 0:
                cumle = "İki yöntem de isbul.net'te <b>%100 başarıya</b> ulaştı; hiçbir istek engellenmedi."
            else:
                en = ozet.sort_values("basari", ascending=False).iloc[0]
                cumle = f"En yüksek başarı oranı: <b>{e(en['yontem'])}</b> (%{en['basari']:.0f})."
            grafik_karti("Başarı oranı (%)", cumle, yatay_bar(ozet, "basari", "yontem", "%"))
        with st.container(border=True):
            st.markdown('<div class="kart-baslik">Yöntemlerin özellikleri</div>', unsafe_allow_html=True)
            st.markdown(
                "| | BeautifulSoup | Selenium |\n|---|---|---|\n"
                "| Nasıl çalışır | HTML'i doğrudan indirir ve ayrıştırır | Gerçek Chrome tarayıcısını kodla yönetir |\n"
                "| JavaScript ile yüklenen içerik | Göremez | Görür |\n"
                "| Hız ve kaynak kullanımı | Hızlı, hafif | Yavaş, tarayıcı açtığı için ağır |\n"
                "| Bot korumaları | Kolay engellenir | Daha dayanıklı, ama doğrulama ekranında durur |\n"
                "| Kariyer.net sonucu | HTTP 403 | \"Robot musun\" doğrulaması |\n"
                "| isbul.net sonucu | Başarılı | Başarılı |")
    with t2:
        st.caption(f"Her scraper çalışmasının kaydı (`data/{IST_DOSYA.parent.name}/{IST_DOSYA.name}`). Kariyer.net "
                   "denemeleri 0 ilanla kayıtlı.")
        st.dataframe(ham.rename(columns={"zaman": "Zaman", "yontem": "Yöntem", "site": "Site",
                                         "deneme": "Deneme", "basarili": "Başarılı", "hata": "Hata",
                                         "engellenen": "Engellenen", "toplam_sure_sn": "Toplam süre (sn)",
                                         "ilan_basina_sn": "İlan başına (sn)"}),
                     width="stretch", hide_index=True)


ORNEK_ILAN = (
    "Yazılım Geliştirici (Backend)\n\nİstanbul Maslak'taki ofisimizde, hibrit çalışma modeliyle "
    "ekibimize katılacak Backend Geliştirici arıyoruz.\n\nAranan nitelikler:\n"
    "- Bilgisayar Mühendisliği veya ilgili bölümlerden lisans mezunu\n"
    "- Python ve Django ile en az 3 yıl deneyimli\n- PostgreSQL ve REST API geliştirme tecrübesi\n"
    "- Docker ve Git kullanımına hâkim\n- İyi derecede İngilizce\n"
    "- Takım çalışmasına yatkın, analitik düşünebilen, iletişim becerileri güçlü"
)


def _ornek_yukle():
    st.session_state["ilan_metni"] = ORNEK_ILAN


def bilgi_karti(sutun, etiket: str, deger: str):
    sutun.markdown(f'<div class="bilgi-kart"><div class="etiket">{e(etiket)}</div>'
                   f'<div class="deger">{e(deger)}</div></div>', unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner=False)
def ollama_durumu() -> str | None:
    """Ollama'ya ulaşılabiliyorsa None, yoksa kısa bir hata açıklaması döndürür."""
    try:
        import ollama
        modeller = {m.model for m in ollama.Client(timeout=2).list().models}
    except Exception:
        return "sunucu"
    return None if config.ANA_MODEL in modeller else "model"


def sayfa_canli():
    sayfa_basligi("⚡ Canlı İlan Analizi",
                  "Bir iş ilanının metnini yapıştır, yerel LLM ilanı okuyup yapılandırılmış bilgiye çevirsin.")
    durum = ollama_durumu()
    if durum == "sunucu":
        st.info("**Bu özellik yerel kurulumda çalışır.** Canlı analiz, bilgisayarda çalışan bir Ollama "
                "sunucusuna ihtiyaç duyar; bu ortamda Ollama'ya ulaşılamadı. Projeyi kendi bilgisayarında "
                "çalıştırmak için README'deki kurulum adımlarını izle ve `ollama serve` ile sunucuyu başlat. "
                "Diğer sayfalar hazır analiz sonuçlarını gösterir.", icon="💻")
    elif durum == "model":
        st.warning(f"Ollama çalışıyor ama `{config.ANA_MODEL}` modeli yok. "
                   f"İndirmek için: `ollama pull {config.ANA_MODEL}`")
    with st.container(border=True):
        ust_sol, ust_sag = st.columns([3, 1])
        if len(config.MODELLER) > 1:
            model = ust_sol.selectbox("Model", config.MODELLER)
        else:
            model = config.MODELLER[0]
            ust_sol.markdown(f'<div class="alt-baslik" style="margin:0.4rem 0 0 0">Model: '
                             f'<b>{e(model)}</b> (Ollama, yerel)</div>', unsafe_allow_html=True)
        ust_sag.button("Örnek ilan yükle", on_click=_ornek_yukle, width="stretch")
        metin = st.text_area("İlan metni", height=220, key="ilan_metni", label_visibility="collapsed",
                             placeholder="İlan metnini buraya yapıştır (en az 30 karakter)...")
        tikla = st.button("Analiz et", type="primary", disabled=len(metin.strip()) < 30 or durum is not None)

    if tikla:
        try:
            from llm.sema import analiz_et
            with st.spinner(f"{model} ilanı okuyor..."):
                sonuc, sure, gecerli = analiz_et(metin, model)
        except Exception as hata:  # Ollama kapalı / model yok
            st.error(f"LLM'e bağlanılamadı: {hata}\n\nOllama açık mı? `ollama list` ile modeli kontrol et.")
            return
        if not gecerli:
            st.error("Model geçerli bir çıktı üretemedi, tekrar dene.")
            return
        st.session_state["canli_sonuc"] = (sonuc, sure)

    if "canli_sonuc" not in st.session_state:
        return
    sonuc, sure = st.session_state["canli_sonuc"]
    st.markdown(f'<div class="cikarim">✅ {ondalik(sure)} saniyede analiz edildi.</div>',
                unsafe_allow_html=True)
    c = st.columns(4)
    bilgi_karti(c[0], "Pozisyon", sonuc["pozisyon"])
    bilgi_karti(c[1], "Sektör", sonuc["sektor"])
    bilgi_karti(c[2], "Seviye", sonuc["seviye"])
    bilgi_karti(c[3], "Deneyim", f"{sonuc['deneyim_yil']} yıl" if sonuc["deneyim_yil"] else "Belirtilmemiş")
    st.write("")
    c = st.columns(4)
    bilgi_karti(c[0], "Eğitim", sonuc["egitim"])
    bilgi_karti(c[1], "Çalışma şekli", sonuc["calisma_sekli"])
    bilgi_karti(c[2], "Teknik beceri sayısı", str(len(sonuc["teknik_beceriler"])))
    bilgi_karti(c[3], "Sosyal beceri sayısı", str(len(sonuc["sosyal_beceriler"])))
    st.write("")
    sol, orta, sag = st.columns([2, 2, 1])
    for sutun, baslik, anahtar, sinif in [(sol, "Teknik beceriler", "teknik_beceriler", "teknik"),
                                          (orta, "Sosyal beceriler", "sosyal_beceriler", "sosyal"),
                                          (sag, "Yabancı dil", "yabanci_dil", "dil")]:
        with sutun.container(border=True):
            st.markdown(f'<div class="kart-baslik">{baslik}</div>{chipler(sonuc[anahtar], sinif)}',
                        unsafe_allow_html=True)
    with st.expander("Ham JSON çıktısı"):
        st.json(sonuc)


# ------------------------------------------------------------------ ana
raw_m, jsonl_m = _mtime(RAW_DOSYA), _mtime(JSONL)
df = veri_yukle(raw_m, jsonl_m)
oz = veri_ozeti(raw_m, jsonl_m)

with st.sidebar:
    st.markdown("### 📊 İş Piyasası Analizi")
    st.caption("Türkiye'deki iş ilanları web scraping ile toplandı ve yerel bir büyük dil modeliyle "
               "(LLM) analiz edildi.")
    sayfa = st.radio("Sayfa", ["Genel Bakış", "Beceri Analizi", "Yöntem Karşılaştırması", "Canlı Analiz"],
                     label_visibility="collapsed")
    st.divider()

filtreli = beceri_filtreleri(df) if sayfa == "Beceri Analizi" and df is not None else None

with st.sidebar:
    if filtreli is not None:
        st.divider()
    analiz = f"{oz['analiz']} / {oz['toplanan']}" if oz["analiz"] < oz["toplanan"] else str(oz["analiz"])
    st.markdown(
        '<div class="kart-baslik">Veri özeti</div><table class="ozet">'
        f"<tr><td>Analiz edilen ilan</td><td>{e(analiz)}</td></tr>"
        f"<tr><td>Kaynak site</td><td>{e(oz['siteler'])}</td></tr>"
        f"<tr><td>Son güncelleme</td><td>{e(oz['son'])}</td></tr>"
        f"<tr><td>Model</td><td>{e(config.ANA_MODEL)}</td></tr></table>",
        unsafe_allow_html=True)

if sayfa in ("Genel Bakış", "Beceri Analizi") and df is None:
    sayfa_basligi("Henüz veri yok", "Bu sayfa için önce ilanları toplayıp LLM'den geçirmen gerekiyor.")
    st.info("1. `python -m scrapers.selenium_scraper --sayfa 10 --limit 400`\n"
            "2. `python -m scrapers.birlestir`\n"
            "3. `python -m llm.cikar`\n\n"
            "Canlı Analiz sayfası veri olmadan da çalışır.")
elif sayfa == "Genel Bakış":
    sayfa_genel(df)
elif sayfa == "Beceri Analizi":
    sayfa_beceri(filtreli)
elif sayfa == "Yöntem Karşılaştırması":
    sayfa_yontem()
else:
    sayfa_canli()
