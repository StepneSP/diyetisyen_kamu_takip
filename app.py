
import sqlite3, os, re, html
from datetime import datetime, date
import pandas as pd
import streamlit as st

DB_PATH = os.getenv("DB_PATH", "data/ilanlar.db")
PROFILE_PATH = "data/profile.json"

st.set_page_config(page_title="Diyetisyen Kamu Takip", page_icon="🥗", layout="wide")

def conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        institution TEXT NOT NULL,
        city TEXT,
        employment TEXT,
        kpss TEXT,
        quota INTEGER,
        published TEXT,
        deadline TEXT,
        url TEXT NOT NULL,
        source TEXT,
        source_url TEXT,
        description TEXT,
        matched_keywords TEXT,
        is_new INTEGER DEFAULT 1,
        first_seen TEXT,
        last_seen TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ran_at TEXT,
        source_count INTEGER,
        new_count INTEGER,
        status TEXT
    )""")
    c.commit()
    c.close()

def load_profile():
    import json
    default = {
        "city": "İstanbul",
        "degree_keywords": ["Beslenme ve Diyetetik", "Diyetisyen"],
        "kpss_p3": 92.0,
        "master": "Hacettepe Üniversitesi TBS yüksek lisans",
        "experience_keywords": ["klinik", "kurum diyetisyeni", "menü planlama", "HACCP", "gıda güvenliği"],
        "preferred_institutions": ["GSB", "Adalet", "CTE", "MEB", "İstanbul Üniversitesi", "İstanbul Üniversitesi-Cerrahpaşa", "Marmara Üniversitesi", "İstanbul Medeniyet Üniversitesi", "Sağlık Bilimleri Üniversitesi", "İBB"]
    }
    try:
        import json
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return {**default, **json.load(f)}
    except Exception:
        return default

def norm(s):
    s = str(s or "").lower()
    return s.replace("İ","i").replace("I","i").replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")

def suitability(row, profile):
    text = norm(" ".join([row.get("title",""), row.get("institution",""), row.get("city",""), row.get("description",""), row.get("kpss","")]))
    score = 0
    reasons = []
    if "istanbul" in norm(row.get("city","")) or "istanbul" in text:
        score += 30; reasons.append("İstanbul")
    elif not row.get("city"):
        score += 10
    else:
        score += 0
    if any(norm(k) in text for k in profile["degree_keywords"]):
        score += 25; reasons.append("mezuniyet/unvan uyumu")
    if any(norm(k) in text for k in ["diyetisyen", "beslenme ve diyetetik"]):
        score += 20; reasons.append("diyetisyen pozisyonu")
    kpss = norm(row.get("kpss",""))
    if "p3" in kpss:
        score += 10; reasons.append("KPSS P3")
    elif "kpss" in kpss:
        score += 5
    if any(norm(k) in text for k in profile["preferred_institutions"]):
        score += 10; reasons.append("öncelikli kurum")
    if row.get("deadline"):
        try:
            d = datetime.fromisoformat(row["deadline"]).date()
            days = (d - date.today()).days
            if days >= 0 and days <= 7:
                score += 5; reasons.append("başvuru süresi kısa")
        except Exception:
            pass
    return min(score,100), reasons

def load_jobs():
    c = conn()
    rows = [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY COALESCE(deadline,'9999') ASC, published DESC").fetchall()]
    c.close()
    return rows

def latest_run():
    c = conn()
    r = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    return dict(r) if r else None

init_db()
profile = load_profile()
jobs = load_jobs()
run = latest_run()

st.title("🥗 Diyetisyen Kamu İlan Takip")
st.caption("İstanbul odaklı • KPSS P3 • kurum bazlı kamu ilanları • üniversiteler")

with st.sidebar:
    st.header("Profil")
    kpss = st.number_input("KPSS P3 (tahmini/gerçek)", min_value=0.0, max_value=100.0, value=float(profile.get("kpss_p3") or 0), step=0.01)
    only_istanbul = st.checkbox("İstanbul öncelikli", value=True)
    only_diet = st.checkbox("Diyetisyen/Beslenme ilanları", value=True)
    st.divider()
    st.markdown("**Takip kaynakları**")
    st.markdown("- Kariyer Kapısı\n- GSB\n- Adalet / CTE\n- MEB\n- İstanbul devlet üniversiteleri\n- İBB / belediyeler\n- Resmî Gazete")
    if st.button("🔄 Verileri yenile"):
        st.cache_data.clear()
        st.rerun()

if not jobs:
    st.warning("Henüz ilan verisi yok. İlk taramayı GitHub Actions veya `python collector.py` ile çalıştır.")
    st.info("Kurulum adımları için README.md dosyasına bak.")
    st.stop()

df = pd.DataFrame(jobs)
df["uygunluk"] = 0
df["neden"] = ""
for i, row in df.iterrows():
    s, reasons = suitability(row.to_dict(), {**profile, "kpss_p3": kpss})
    df.at[i,"uygunluk"] = s
    df.at[i,"neden"] = ", ".join(reasons)

if only_istanbul:
    mask = df["city"].fillna("").map(lambda x: "istanbul" in norm(x))
    mask = mask | df["institution"].fillna("").map(lambda x: "istanbul" in norm(x))
    df = df[mask | df["city"].fillna("").eq("")]

if only_diet:
    textcol = (df["title"].fillna("")+" "+df["description"].fillna("")).map(norm)
    df = df[textcol.str.contains("diyetisyen|beslenme ve diyetetik|diyetetik", regex=True, na=False)]

new_count = int(df["is_new"].fillna(0).sum())
c1,c2,c3,c4 = st.columns(4)
c1.metric("Gösterilen ilan", len(df))
c2.metric("Yeni", new_count)
c3.metric("Yüksek uyum (≥80)", int((df["uygunluk"]>=80).sum()))
c4.metric("Son tarama", run["ran_at"][:16].replace("T"," ") if run else "—")

st.subheader("🔥 Sana en uygun ilanlar")
top = df.sort_values(["uygunluk","deadline"], ascending=[False, True]).head(10)
for _, r in top.iterrows():
    badge = "🟢" if r["uygunluk"] >= 80 else ("🟡" if r["uygunluk"] >= 60 else "⚪")
    st.markdown(f"### {badge} {r['title']} — {r['institution']}")
    st.write(f"**Uygunluk:** {r['uygunluk']}/100  • **Şehir:** {r.get('city') or 'Belirtilmemiş'}  • **KPSS:** {r.get('kpss') or 'Belirtilmemiş'}")
    if r.get("deadline"):
        st.write(f"**Son başvuru:** {r['deadline'][:10]}")
    if r.get("neden"):
        st.caption("Neden: " + r["neden"])
    if r.get("description"):
        st.write(r["description"][:500] + ("…" if len(r["description"])>500 else ""))
    st.link_button("Resmî ilana git", r["url"])
    st.divider()

st.subheader("📋 Tüm eşleşmeler")
show_cols = ["institution","title","city","kpss","quota","published","deadline","uygunluk","url"]
table = df[show_cols].copy()
table.columns = ["Kurum","Pozisyon","İl","KPSS","Kontenjan","Yayın","Son başvuru","Uyum","İlan"]
st.dataframe(table, use_container_width=True, hide_index=True, column_config={
    "İlan": st.column_config.LinkColumn("Resmî ilan", display_text="Aç")
})

with st.expander("🏛️ İstanbul üniversiteleri ve kurum takibi"):
    uni = [
        "İstanbul Üniversitesi","İstanbul Üniversitesi-Cerrahpaşa","Marmara Üniversitesi",
        "İstanbul Medeniyet Üniversitesi","Yıldız Teknik Üniversitesi","İstanbul Teknik Üniversitesi",
        "Mimar Sinan Güzel Sanatlar Üniversitesi","Boğaziçi Üniversitesi",
        "Sağlık Bilimleri Üniversitesi","Türk-Alman Üniversitesi"
    ]
    st.write("Bu kurumlar kaynak listesinde izlenir; yeni duyuru bulunduğunda ilan tablosuna düşer.")
    st.write(", ".join(uni))

with st.expander("ℹ️ Sistem nasıl çalışıyor?"):
    st.write("Günlük tarama GitHub Actions tarafından çalıştırılır. Bulunan ilanlar SQLite veritabanına eklenir; Streamlit paneli bu veriyi gösterir. Başvuru işlemi her zaman kurumun resmî sayfasından manuel yapılır.")
