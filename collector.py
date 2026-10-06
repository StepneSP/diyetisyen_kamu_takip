
import sqlite3, os, re, json, hashlib, html
from datetime import datetime
from urllib.parse import quote
import requests, feedparser
from bs4 import BeautifulSoup

DB_PATH = os.getenv("DB_PATH", "data/ilanlar.db")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DietitianPublicJobsMonitor/1.0)"}

def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, institution TEXT NOT NULL,
        city TEXT, employment TEXT, kpss TEXT, quota INTEGER,
        published TEXT, deadline TEXT, url TEXT NOT NULL, source TEXT,
        source_url TEXT, description TEXT, matched_keywords TEXT,
        is_new INTEGER DEFAULT 1, first_seen TEXT, last_seen TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT,
        source_count INTEGER, new_count INTEGER, status TEXT)""")
    c.commit()
    return c

def clean(x):
    return re.sub(r"\s+", " ", BeautifulSoup(str(x or ""), "html.parser").get_text(" ", strip=True)).strip()

def domain_ok(url, domain):
    return domain.lower() in (url or "").lower()

def guess_city(text):
    cities = ["İstanbul","Ankara","İzmir","Bursa","Antalya","Adana","Konya","Kocaeli","Kayseri","Mersin","Gaziantep","Sakarya","Eskişehir","Samsun","Trabzon"]
    low = text.lower()
    for c in cities:
        if c.lower() in low:
            return c
    return ""

def guess_kpss(text):
    m = re.search(r"KPSS\s*P?3|KPSSP3|KPSS\s*B", text, re.I)
    return "KPSS P3" if m and ("p3" in m.group(0).lower() or "b" in m.group(0).lower()) else (m.group(0) if m else "")

def guess_quota(text):
    patterns = [
        r"(\d+)\s+(?:adet\s+)?diyetisyen",
        r"diyetisyen[^0-9]{0,80}(\d+)\s*(?:kişi|personel|pozisyon)",
        r"toplam\s+(\d+)\s+.*diyetisyen"
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try: return int(m.group(1))
            except: pass
    return None

def guess_deadline(text):
    patterns = [
        r"(\d{1,2})[./](\d{1,2})[./](20\d{2}).{0,80}(?:sona|son|kadar)",
        r"(?:son başvuru|başvurular).{0,120}?(\d{1,2})[./](\d{1,2})[./](20\d{2})"
    ]
    for p in patterns:
        m = re.search(p, text, re.I|re.S)
        if m:
            d,mn,y = m.group(1),m.group(2),m.group(3)
            return f"{y}-{int(mn):02d}-{int(d):02d}"
    return ""

def fetch_google_news(q, domain):
    url = "https://news.google.com/rss/search?q="+quote(q)+"&hl=tr&gl=TR&ceid=TR:tr"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    out=[]
    for e in feed.entries:
        link=e.get("link","")
        title=clean(e.get("title",""))
        summary=clean(e.get("summary",""))
        source_href=""
        try:
            source_href=e.get("source",{}).get("href","")
        except Exception:
            pass
        if domain_ok(link, domain) or domain_ok(source_href, domain) or domain.lower() in summary.lower():
            out.append({
                "title": title,
                "url": link,
                "published": e.get("published",""),
                "description": summary,
                "source_href": source_href
            })
    return out

def enrich(url, fallback_title, fallback_desc):
    try:
        r=requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        txt=clean(soup.get_text(" ", strip=True))
        title=clean(soup.title.get_text()) if soup.title else fallback_title
        desc=(txt[:2500] if txt else fallback_desc)
        return title, desc
    except Exception:
        return fallback_title, fallback_desc

def save_job(c, item, source_name, source_domain):
    full=(item["title"]+" "+item["description"])
    title, desc = enrich(item["url"], item["title"], item["description"])
    full = title+" "+desc
    # Only keep relevant public-job content.
    low=full.lower()
    if not any(k in low for k in ["diyetisyen","beslenme ve diyetetik","diyetetik"]):
        return False
    city=guess_city(full)
    kpss=guess_kpss(full)
    quota=guess_quota(full)
    deadline=guess_deadline(full)
    ident=hashlib.sha256((item["url"]+"|"+title).encode()).hexdigest()[:24]
    now=datetime.utcnow().isoformat()
    old=c.execute("SELECT id FROM jobs WHERE id=?",(ident,)).fetchone()
    c.execute("""INSERT OR REPLACE INTO jobs
        (id,title,institution,city,employment,kpss,quota,published,deadline,url,source,source_url,description,matched_keywords,is_new,first_seen,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        ident,title,source_name,city,"Sözleşmeli" if "sözleş" in low else "",
        kpss,quota,item.get("published",""),deadline,item["url"],source_name,
        "https://"+source_domain,desc,"diyetisyen;beslenme ve diyetetik",1 if not old else 0,
        now if not old else None,now
    ))
    return not bool(old)

def seed(c):
    seeds=[
      {
       "id":"seed-gsb-2026","title":"2026 Yılı Sözleşmeli Diyetisyen, Psikolog ve Sosyal Çalışmacı Alımı",
       "institution":"Gençlik ve Spor Bakanlığı","city":"Türkiye","employment":"Sözleşmeli","kpss":"2024 KPSS P3",
       "quota":100,"published":"2026-07-17","deadline":"2026-07-24",
       "url":"https://www.gsb.gov.tr/tr/haber-detay/300998-genclik-spor-bakanligi-550-personel-alimi-yapacak",
       "source":"GSB","source_url":"https://gsb.gov.tr","description":"Gençlik ve Spor Bakanlığı taşra teşkilatı için 100 sözleşmeli diyetisyen alımı. 2024 KPSS P3 puanı esas alındı; boş kontenjanın üç katı aday sözlü sınava çağrıldı."
      },
      {
       "id":"seed-cte-2026","title":"334 Sözleşmeli Pozisyon İçin Personel Alımı — Diyetisyen",
       "institution":"Adalet Bakanlığı / CTE","city":"Türkiye","employment":"Sözleşmeli","kpss":"2024 KPSS P3",
       "quota":21,"published":"2026-06-05","deadline":"2026-06-22",
       "url":"https://cte.adalet.gov.tr/Home/SayfaDetay/334-sozlesmeli-personel-komisyon-alim-ilani05062026051122",
       "source":"Adalet CTE","source_url":"https://cte.adalet.gov.tr","description":"Ceza ve Tevkifevleri Genel Müdürlüğü 21 diyetisyen dahil 334 sözleşmeli personel aldı. Diyetisyen için Beslenme ve Diyetetik lisans mezuniyeti ve 2024 KPSS P3 şartı."
      },
      {
       "id":"seed-meb-2026-istanbul-1","title":"Sözleşmeli Diyetisyen — İstanbul Ataşehir Zübeyde Hanım Eğitim ve Uygulama Merkezi",
       "institution":"Millî Eğitim Bakanlığı Eğitim ve Uygulama Merkezleri","city":"İstanbul","employment":"Sözleşmeli","kpss":"KPSS P3",
       "quota":1,"published":"2026-02-26","deadline":"",
       "url":"https://personel.meb.gov.tr/meb_iys_dosyalar/2026_02/69a15476b5aff124767001_Akademi_S%C3%B6zlesmeli_Alim_Kilavuz.pdf",
       "source":"MEB","source_url":"https://personel.meb.gov.tr","description":"2026 MEB Akademi sözleşmeli personel kılavuzunda İstanbul Ataşehir Zübeyde Hanım Eğitim ve Uygulama Merkezi için 1 diyetisyen pozisyonu. KPSS P3; Beslenme ve Diyetetik lisans mezuniyeti; 35 yaş şartı ve vardiyalı çalışma koşulu."
      },
      {
       "id":"seed-meb-2026-istanbul-2","title":"Sözleşmeli Diyetisyen — İstanbul Sultanahmet Eğitim ve Uygulama Merkezi",
       "institution":"Millî Eğitim Bakanlığı Eğitim ve Uygulama Merkezleri","city":"İstanbul","employment":"Sözleşmeli","kpss":"KPSS P3",
       "quota":1,"published":"2026-02-26","deadline":"",
       "url":"https://personel.meb.gov.tr/meb_iys_dosyalar/2026_02/69a15476b5aff124767001_Akademi_S%C3%B6zlesmeli_Alim_Kilavuz.pdf",
       "source":"MEB","source_url":"https://personel.meb.gov.tr","description":"2026 MEB Akademi sözleşmeli personel kılavuzunda İstanbul Sultanahmet Eğitim ve Uygulama Merkezi için 1 diyetisyen pozisyonu. KPSS P3; Beslenme ve Diyetetik lisans mezuniyeti; 35 yaş şartı ve vardiyalı çalışma koşulu."
      },
      {
       "id":"seed-meb-2026-istanbul-3","title":"Sözleşmeli Diyetisyen — İstanbul Haydarpaşa Eğitim ve Uygulama Merkezi",
       "institution":"Millî Eğitim Bakanlığı Eğitim ve Uygulama Merkezleri","city":"İstanbul","employment":"Sözleşmeli","kpss":"KPSS P3",
       "quota":1,"published":"2026-02-26","deadline":"",
       "url":"https://personel.meb.gov.tr/meb_iys_dosyalar/2026_02/69a15476b5aff124767001_Akademi_S%C3%B6zlesmeli_Alim_Kilavuz.pdf",
       "source":"MEB","source_url":"https://personel.meb.gov.tr","description":"2026 MEB Akademi sözleşmeli personel kılavuzunda İstanbul Haydarpaşa Eğitim ve Uygulama Merkezi için 1 diyetisyen pozisyonu. KPSS P3; Beslenme ve Diyetetik lisans mezuniyeti; 35 yaş şartı ve vardiyalı çalışma koşulu."
      },
      {
       "id":"seed-medeniyet-2025","title":"4/B Sözleşmeli Personel Alımı — Diyetisyen",
       "institution":"İstanbul Medeniyet Üniversitesi","city":"İstanbul","employment":"Sözleşmeli","kpss":"KPSS P3",
       "quota":1,"published":"2025-10-26","deadline":"",
       "url":"https://personel.medeniyet.edu.tr/tr/duyurular/26102025-tarihli-4b-sozlesmeli-personel-alim-ilani-sonuclari",
       "source":"İstanbul Medeniyet Üniversitesi","source_url":"https://personel.medeniyet.edu.tr","description":"26.10.2025 tarihli 4/B sözleşmeli personel alımı sonuçlarında Diyetisyen pozisyonu yer aldı. Üniversitenin personel ilanları ayrıca takip edilmelidir."
      }
    ]
    for s in seeds:
        c.execute("""INSERT OR IGNORE INTO jobs
        (id,title,institution,city,employment,kpss,quota,published,deadline,url,source,source_url,description,matched_keywords,is_new,first_seen,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        s["id"],s["title"],s["institution"],s["city"],s["employment"],s["kpss"],s["quota"],s["published"],s["deadline"],s["url"],s["source"],s["source_url"],s["description"],"diyetisyen;beslenme ve diyetetik",1,s["published"],s["published"]))
    c.commit()

def run():
    c=db()
    seed(c)
    with open("sources.json","r",encoding="utf-8") as f: cfg=json.load(f)
    new=0; ok=0; errors=[]
    for s in cfg["google_news_queries"]:
        try:
            items=fetch_google_news(s["query"],s["domain"])
            ok+=1
            for item in items[:30]:
                try:
                    if save_job(c,item,s["name"],s["domain"]):
                        new+=1
                except Exception as e:
                    errors.append(f"{s['name']}: {e}")
        except Exception as e:
            errors.append(f"{s['name']}: {e}")
    # Existing rows are no longer "new" after one successful run.
    c.execute("UPDATE jobs SET is_new=0 WHERE is_new=1 AND first_seen < datetime('now','-1 day')")
    status="ok" if not errors else "partial"
    c.execute("INSERT INTO runs(ran_at,source_count,new_count,status) VALUES(?,?,?,?)",
              (datetime.utcnow().isoformat(),ok,new,status))
    c.commit(); c.close()
    print(json.dumps({"sources_ok":ok,"new":new,"errors":errors[:10]},ensure_ascii=False))

if __name__=="__main__":
    run()
