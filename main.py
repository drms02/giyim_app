import gc
import os
import sys
import shutil

# ==========================================
# 🛑 BURAYI DİKKATLİ YAPISTIR (EN TEPEYE)
# ==========================================

# 1. Ana dizini bul
base_path = os.path.dirname(os.path.abspath(__file__))

# 2. U2NET_HOME değişkenini KESİN olarak ayarla
# Kütüphane modelleri burada arayacak
u2net_home_path = os.path.join(base_path, ".u2net")
os.environ["U2NET_HOME"] = u2net_home_path

# 3. Klasörü oluştur (Yoksa yarat)
if not os.path.exists(u2net_home_path):
    os.makedirs(u2net_home_path, exist_ok=True)

# 4. Dosya Kaynak ve Hedef Yolları
source_file = os.path.join(base_path, "u2netp.onnx")       # Senin yüklediğin
target_file = os.path.join(u2net_home_path, "u2netp.onnx") # Onun aradığı

# 5. Dosyayı yerine zorla taşı/kopyala
print(f"🔍 Model kontrol ediliyor...")
print(f"   Kaynak: {source_file}")
print(f"   Hedef:  {target_file}")

if os.path.exists(source_file):
    # Eğer hedefte yoksa veya boyutu farklıysa kopyala
    if not os.path.exists(target_file) or os.path.getsize(target_file) != os.path.getsize(source_file):
        print("📦 Model dosyası kopyalanıyor (İndirmeyi engellemek için)...")
        shutil.copy(source_file, target_file)
        print("✅ Kopyalama TAMAMLANDI.")
    else:
        print("✅ Model zaten doğru yerde ve boyutta.")
else:
    print("🚨 HATA: 'u2netp.onnx' ana dizinde bulunamadı! GitHub'a yüklememiş olabilirsin.")

# ==========================================
# 📚 İMPORTLAR (BU KISIM KESİNLİKLE AŞAĞIDA KALMALI)
# ==========================================
from rembg import remove, new_session 
from dotenv import load_dotenv 
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# ... diğer importların aynı kalsın ...
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
import io
import uuid
import sqlite3
import math
import colorsys
import json
import random
import bcrypt
import numpy as np
import re
import imagehash 
from collections import Counter
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from groq import Groq

# --- AYARLAR ---
load_dotenv() # .env dosyasını oku

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("UYARI: GROQ_API_KEY bulunamadı! .env dosyasını kontrol et.")

client = Groq(api_key=GROQ_API_KEY)


def verify_password(plain_password, hashed_password):
    # Düz şifreyi ve hashli şifreyi karşılaştırır
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    # Şifreyi hashler
    # gensalt() tuzu ekler, hashpw şifreler
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

class UserLoginSchema(BaseModel):
    username: str
    password: str # Yeni eklendi

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = BASE_DIR 
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "dolap_v41_clean.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

static_path = os.path.join(BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# ... Kodun geri kalanı (class OutfitSchema vs.) buradan aşağısı aynen kalsın ...

class OutfitSchema(BaseModel):
    top_id: int
    bottom_id: int
    shoe_id: int = None
    username: str 

class WearConfirmSchema(BaseModel):
    top_id: int
    bottom_id: int
    shoe_id: int = None

class TravelRequest(BaseModel):
    days: int
    season: str
    destination: str = "Seyahat"
    username: str 

class PlanSchema(BaseModel):
    date_str: str
    top_id: int
    bottom_id: int
    shoe_id: int = None
    username: str 

class ItemUpdateSchema(BaseModel):
    id: int
    category: str
    season: str
    style: str
    sub_category: str = None

class ShareSchema(BaseModel):
    user_name: str
    username_handle: str
    top_id: int
    bottom_id: int
    shoe_id: int = None

class UserRegisterSchema(BaseModel):
    full_name: str
    username: str
    password: str # Yeni eklendi
    email: str = None
    city: str = None
    gender: str = None

class UserUpdateSchema(BaseModel):
    current_username: str
    new_username: str
    new_full_name: str

class FollowSchema(BaseModel):
    follower: str 
    followed: str

class LikeSchema(BaseModel):
    post_id: int
    liker_user: str 

class CommentSchema(BaseModel):
    post_id: int
    username: str
    text: str
    
class WashListSchema(BaseModel):
    item_ids: list[int]

def calculate_league(xp):
    xp = xp or 0
    if xp >= 1500:
        return {"name": "Elmas Ligi", "icon": "💎", "class": "diamond", "next_xp": None, "progress": 100}
    elif xp >= 500:
        needed = 1500 - xp
        percent = int(((xp - 500) / 1000) * 100)
        return {"name": "Altın Ligi", "icon": "🏆", "class": "gold", "next_xp": needed, "progress": percent}
    elif xp >= 150:
        needed = 500 - xp
        percent = int(((xp - 150) / 350) * 100)
        return {"name": "Gümüş Ligi", "icon": "🥈", "class": "silver", "next_xp": needed, "progress": percent}
    else:
        needed = 150 - xp
        percent = int((xp / 150) * 100)
        return {"name": "Bronz Ligi", "icon": "🥉", "class": "bronze", "next_xp": needed, "progress": percent}

def update_user_xp(username, points):
    """Kullanıcıya XP kazandırır"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE users SET xp = xp + ? WHERE username = ?", (points, username))
        conn.commit()
        conn.close()
    except:
        pass

def calculate_compatibility_score(color1, color2):
    COLOR_HARMONY = {
        "Siyah": ["Beyaz", "Gri", "Kırmızı", "Mavi", "Siyah", "Bej", "Haki", "Sarı"],
        "Beyaz": ["Siyah", "Mavi", "Bej", "Kahverengi", "Gri", "Yeşil", "Kırmızı", "Lacivert", "Mor"],
        "Gri": ["Siyah", "Beyaz", "Mavi", "Kırmızı", "Pembe", "Mor", "Sarı"],
        "Lacivert": ["Bej", "Beyaz", "Gri", "Haki", "Sarı", "Kırmızı", "Turuncu"],
        "Mavi": ["Beyaz", "Bej", "Kahverengi", "Siyah", "Gri", "Turuncu"],
        "Bej": ["Lacivert", "Mavi", "Siyah", "Beyaz", "Haki", "Yeşil", "Kahverengi", "Bordo"],
        "Kahverengi": ["Bej", "Mavi", "Beyaz", "Yeşil", "Turkuaz"],
        "Kırmızı": ["Siyah", "Beyaz", "Lacivert", "Gri", "Bej"],
        "Yeşil": ["Bej", "Siyah", "Beyaz", "Kahverengi", "Lacivert", "Gri"],
        "Haki": ["Siyah", "Beyaz", "Bej", "Lacivert", "Turuncu"],
        "Sarı": ["Lacivert", "Siyah", "Gri", "Beyaz", "Mor"],
        "Pembe": ["Gri", "Beyaz", "Siyah", "Lacivert", "Yeşil"],
        "Turuncu": ["Mavi", "Lacivert", "Beyaz", "Siyah", "Haki"],
        "Mor": ["Gri", "Beyaz", "Siyah", "Sarı", "Bej"],
        "Antrasit": ["Beyaz", "Siyah", "Kırmızı", "Mavi", "Sarı"],
        "Turkuaz": ["Beyaz", "Siyah", "Kahverengi", "Bej"],
        "Bilinmiyor": []
    }
    c1 = color1 if color1 else "Bilinmiyor"
    c2 = color2 if color2 else "Bilinmiyor"
    score = 0
    if c2 in COLOR_HARMONY.get(c1, []): score += 10
    if c1 in COLOR_HARMONY.get(c2, []): score += 10
    if c1 in ["Siyah", "Beyaz", "Gri"] or c2 in ["Siyah", "Beyaz", "Gri"]: score += 5
    if c1 == c2: score += 3
    return score

def format_date_tr(date_obj):
    months = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    return f"{date_obj.day} {months[date_obj.month]}"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. CLOTHES TABLOSU (Mevcut)
    cursor.execute('''CREATE TABLE IF NOT EXISTS clothes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT, 
        url TEXT, 
        category TEXT, 
        season TEXT, 
        style TEXT, 
        color_name TEXT, 
        wear_count INTEGER DEFAULT 0, 
        is_clean INTEGER DEFAULT 1,
        sub_category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 2. OUTFITS TABLOSU (!!! EKSİK OLAN BUYDU, EKLENDİ !!!)
    # İstatistiklerin ve favorilerin çalışması için bu şart.
    # Ayrıca yeni 'accessory_id' alanını da ekledik.
    cursor.execute('''CREATE TABLE IF NOT EXISTS outfits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        top_id INTEGER,
        bottom_id INTEGER,
        shoe_id INTEGER,
        accessory_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 3. DİĞER MEVCUT TABLOLAR (Dokunulmadı, aynen korundu)
    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_outfits (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, top_id INTEGER, bottom_id INTEGER, shoe_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')  
    cursor.execute('''CREATE TABLE IF NOT EXISTS disliked_outfits (id INTEGER PRIMARY KEY AUTOINCREMENT, top_id INTEGER, bottom_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, full_name TEXT, email TEXT, city TEXT, gender TEXT, avatar_url TEXT, xp INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS planned_outfits (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, plan_date TEXT, top_id INTEGER, bottom_id INTEGER, shoe_id INTEGER, UNIQUE(username, plan_date))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS social_feed (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, username_handle TEXT, top_url TEXT, bottom_url TEXT, shoe_url TEXT, top_id INTEGER, bottom_id INTEGER, shoe_id INTEGER, likes INTEGER DEFAULT 0, duel_wins INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower_username TEXT, followed_username TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(follower_username, followed_username))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_to TEXT, user_from TEXT, type TEXT, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, title TEXT, data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS wear_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT, 
        top_id INTEGER, 
        bottom_id INTEGER, 
        shoe_id INTEGER, 
        wear_date TEXT, 
        is_reviewed INTEGER DEFAULT 0 
    )''')
    
    # 4. AFFILIATE TABLOSU (YENİ - Linkleri burada tutacağız)
    cursor.execute('''CREATE TABLE IF NOT EXISTS affiliate_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE,  -- Örn: "Beyaz Sneaker"
        link TEXT,            -- Örn: "https://ty.gl/..."
        click_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

# Uygulama başlarken çalıştır
init_db()

def get_color_name_from_hsv(h, s, v):
    if v < 15: return "Siyah"
    if v > 90 and s < 10: return "Beyaz"
    if s < 15: return "Antrasit" if v < 40 else "Gri"
    if (h >= 0 and h < 15) or (h >= 345 and h <= 360): return "Kırmızı"
    if h >= 15 and h < 40: return "Kahverengi" if v < 60 else "Turuncu"
    if h >= 40 and h < 70: return "Bej" if s < 50 else "Sarı"
    if h >= 70 and h < 160: return "Haki" if s < 40 else "Yeşil"
    if h >= 160 and h < 190: return "Turkuaz"
    if h >= 190 and h < 250: return "Lacivert" if v < 35 else "Mavi"
    if h >= 250 and h < 290: return "Mor"
    if h >= 290 and h < 345: return "Pembe"
    return "Bilinmiyor"

def analyze_clothing_color(img: Image.Image):
    img = img.copy(); img.thumbnail((150, 150)); img = img.convert("RGBA")
    pixels = img.getdata(); color_votes = []
    for r, g, b, a in pixels:
        if a < 200: continue
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        color_votes.append(get_color_name_from_hsv(h*360, s*100, v*100))
    if not color_votes: return "Bilinmiyor"
    vote_counts = Counter(color_votes)
    most = vote_counts.most_common(1)[0][0]
    if most in ["Siyah", "Gri", "Antrasit"] and len(vote_counts) > 1:
        sec = vote_counts.most_common(2)[1]
        if sec[1] > len(color_votes) * 0.20 and sec[0] not in ["Siyah", "Gri", "Beyaz"]: return sec[0]
    return most

def crop_image(img: Image.Image):
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img

def is_duplicate_image(username, img_obj):
    """
    Kullanıcının daha önce aynı görseli yükleyip yüklemediğini kontrol eder.
    pHash algoritması kullanır (Renk/Boyut değişimine dirençlidir).
    """
    try:
        current_hash = imagehash.phash(img_obj)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Kullanıcının önceki resimlerinin hashlerini çek
        cursor.execute("SELECT image_hash FROM clothes WHERE username = ? AND image_hash IS NOT NULL", (username,))
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            db_hash_str = row[0]
            if db_hash_str:
                db_hash = imagehash.hex_to_hash(db_hash_str)
                # Hamming Distance: İki hash arasındaki fark.
                # 0 = Birebir aynı, < 5 = Çok benzer
                if (current_hash - db_hash) < 5: 
                    return True, str(current_hash) # Kopya bulundu
        
        return False, str(current_hash)
    except Exception as e:
        print(f"Hash Hatası: {e}")
        return False, None

def check_daily_xp_cap(username, action_type, limit=5):
    """
    Kullanıcının o gün o işlemden kaç kez puan kazandığını sayar.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM xp_logs WHERE username = ? AND action_type = ? AND log_date = ?", 
                   (username, action_type, today))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count < limit # Limit aşılmadıysa True döner

# --- PREMIUM KONTROL SİSTEMİ ---

def check_premium_status(username):
    """Kullanıcının Premium olup olmadığını döner"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    row = c.execute("SELECT is_premium FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row and row[0] == 1

def check_limits(username, feature_type):
    """
    Özelliğe göre limit kontrolü yapar.
    feature_type: 'upload' (Dolap Limiti) veya 'ai_gen' (Kombin Limiti)
    Dönüş: (İzin Var mı?, Hata Mesajı)
    """
    is_prem = check_premium_status(username)
    
    # Eğer Premium ise sınır yok!
    if is_prem:
        return True, None

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if feature_type == 'upload':
        # FREE LİMİTİ: 30 Parça
        count = c.execute("SELECT COUNT(*) FROM clothes WHERE username = ?", (username,)).fetchone()[0]
        limit = 30
        if count >= limit:
            conn.close()
            return False, f"Free pakette en fazla {limit} kıyafet yükleyebilirsin. Sınırsız dolap için Premium'a geç! 👑"

    elif feature_type == 'ai_gen':
        # FREE LİMİTİ: Günde 1 Kombin
        today = datetime.now().strftime("%Y-%m-%d")
        # xp_logs tablosunu kullanarak sayaç yapabiliriz veya basitçe o anlık kontrol
        # Şimdilik basit tutalım, log tablosundan sayalım (action_type='ai_gen' diye kaydedeceğiz)
        count = c.execute("SELECT COUNT(*) FROM xp_logs WHERE username = ? AND action_type = 'ai_gen' AND log_date = ?", 
                          (username, today)).fetchone()[0]
        limit = 1
        if count >= limit:
            conn.close()
            return False, "Günlük kombin hakkın doldu. Sınırsız stilist için Premium'a geç! 👑"
            
    conn.close()
    return True, None

# --- ✅ SİTE AÇILIŞ VE RENDER KONTROLÜ ---
@app.get("/")
@app.head("/") # <--- BU SATIR ŞART! Render'ın "Yaşıyor musun?" kontrolü için.
async def read_root():
    # index.html dosyasını kullanıcıya gönder
    return FileResponse("static/index.html")
# ----------------------------------------
    
    # 2. Olmadıysa direkt 'index.html' yolunu dene (Belki dışarıdadır)
    path2 = "index.html"
    if os.path.exists(path2):
        return FileResponse(path2)

    # 3. İkisi de yoksa, bana etrafında ne gördüğünü söyle (HATA RAPORU)
    import os
    current_dir = os.getcwd()
    files = os.listdir(current_dir)
    static_files = os.listdir("static") if os.path.exists("static") else "Static klasörü yok!"
    
    return {
        "HATA": "Dosya bulunamadı!",
        "Benim_Konumum": current_dir,
        "Yanımdaki_Dosyalar": files,
        "Static_Klasörünün_İçi": static_files
    }

@app.get("/favicon.ico")
async def get_favicon():
    path = os.path.join(BASE_DIR, "static", "logo.png")
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "logo yok"}

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = os.path.join(BASE_DIR, "manifest.json")
    
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    return {"error": "manifest.json dosyası bulunamadı"}

@app.get("/sw.js")
async def get_sw():
    sw_path = os.path.join(BASE_DIR, "sw.js")
    
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return {"error": "sw.js dosyası bulunamadı"}

@app.get("/fix_database_now")
async def fix_database_now():
    conn = sqlite3.connect(DB_FILE)
    log = []
    try:
        # --- 1. KRİTİK DÜZELTME: ŞİFRE SÜTUNU ---
        try:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            log.append("✅ Şifre Kutusu (password_hash) Eklendi! 🔒")
        except:
            pass # Zaten varsa sorun yok, devam et.

        # --- 2. DİĞER EKSİKLERİ TAMAMLA ---
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            log.append("Email Eklendi")
        except: pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN city TEXT")
            log.append("City Eklendi")
        except: pass

        try:
            conn.execute("ALTER TABLE users ADD COLUMN gender TEXT")
            log.append("Gender Eklendi")
        except: pass
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
            log.append("XP Sütunu Kontrol Edildi")
        except: pass
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE users ADD COLUMN premium_expiry TEXT")
            log.append("Premium Özellikleri Eklendi")
        except: pass

        try:
            conn.execute("ALTER TABLE social_feed ADD COLUMN duel_wins INTEGER DEFAULT 0")
        except: pass

        try:
            conn.execute("ALTER TABLE social_feed ADD COLUMN user_name TEXT")
        except: pass

        try:
            conn.execute("ALTER TABLE social_feed ADD COLUMN username_handle TEXT")
        except: pass
        
        try:
            conn.execute("ALTER TABLE clothes ADD COLUMN is_clean INTEGER DEFAULT 1")
        except: pass

        try:
            conn.execute("ALTER TABLE clothes ADD COLUMN sub_category TEXT")
        except: pass
        
        try:
            conn.execute("ALTER TABLE clothes ADD COLUMN image_hash TEXT")
        except: pass
        
        # --- 3. EKSİK TABLOLAR VARSA OLUŞTUR (Yedek) ---
        # Eğer tablolar hiç yoksa hata vermesin diye burayı da ekliyoruz
        conn.execute('''CREATE TABLE IF NOT EXISTS xp_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action_type TEXT, xp_amount INTEGER, log_date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Affiliate tablosunu da garantiye alalım
        conn.execute('''CREATE TABLE IF NOT EXISTS affiliate_links (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT UNIQUE, link TEXT, click_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
        return {"durum": "TAMAMLANDI", "yapilan_islemler": log}
    
    except Exception as e:
        return {"durum": "HATA", "error": str(e)}
    finally:
        conn.close()

@app.post("/user/register")
async def register_user(user: UserRegisterSchema):
    conn = sqlite3.connect(DB_FILE)
    try:
        # Şifreyi hashle (kriptola)
        hashed_pw = get_password_hash(user.password)
        
        conn.execute("INSERT INTO users (username, full_name, email, city, gender, xp, password_hash) VALUES (?, ?, ?, ?, ?, 0, ?)", 
                     (user.username, user.full_name, user.email, user.city, user.gender, hashed_pw))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış.")

@app.post("/user/update")
async def update_user(data: UserUpdateSchema):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if data.new_username != data.current_username:
        exist = cur.execute("SELECT 1 FROM users WHERE username = ?", (data.new_username,)).fetchone()
        if exist: conn.close(); raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor.")
    try:
        cur.execute("UPDATE users SET username = ?, full_name = ? WHERE username = ?", (data.new_username, data.new_full_name, data.current_username))
        if data.new_username != data.current_username:
            tables = ["clothes", "saved_outfits", "user_plans", "planned_outfits"]
            for t in tables: cur.execute(f"UPDATE {t} SET username = ? WHERE username = ?", (data.new_username, data.current_username))
            cur.execute("UPDATE social_feed SET username_handle = ?, user_name = ? WHERE username_handle = ?", (data.new_username, data.new_full_name, data.current_username))
            cur.execute("UPDATE follows SET follower_username = ? WHERE follower_username = ?", (data.new_username, data.current_username))
            cur.execute("UPDATE follows SET followed_username = ? WHERE followed_username = ?", (data.new_username, data.current_username))
            cur.execute("UPDATE notifications SET user_to = ? WHERE user_to = ?", (data.new_username, data.current_username))
            cur.execute("UPDATE notifications SET user_from = ? WHERE user_from = ?", (data.new_username, data.current_username))
            cur.execute("UPDATE comments SET username = ? WHERE username = ?", (data.new_username, data.current_username))
        conn.commit(); conn.close()
        return {"status": "success", "username": data.new_username, "full_name": data.new_full_name}
    except Exception as e: conn.close(); return {"error": str(e)}

@app.post("/user/upload-avatar")
async def upload_avatar(file: UploadFile = File(...), username: str = Form(...)):
    unique_id = str(uuid.uuid4()); path = os.path.join(UPLOAD_DIR, f"avatar_{unique_id}.jpg")
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    w, h = img.size; new_size = min(w, h)
    img = img.crop(((w-new_size)/2, (h-new_size)/2, (w+new_size)/2, (h+new_size)/2))
    img.thumbnail((300, 300)); img.save(path, quality=85)
    url = f"/uploads/avatar_{unique_id}.jpg"
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE users SET avatar_url = ? WHERE username = ?", (url, username))
    conn.commit(); conn.close()
    return {"status": "success", "avatar_url": url}

@app.get("/user/search")
async def search_users(q: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    search_term = f"%{q}%"
    cur.execute("SELECT username, full_name, avatar_url FROM users WHERE username LIKE ? OR full_name LIKE ? LIMIT 10", (search_term, search_term))
    rows = cur.fetchall(); conn.close()
    return rows

@app.get("/user/profile/{username}")
async def get_user_profile_stats(username: str, viewer: str = None):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    user_row = cur.execute("SELECT full_name, avatar_url, xp FROM users WHERE username = ?", (username,)).fetchone()
    if not user_row: conn.close(); return {"error": "User not found"}
    followers = cur.execute("SELECT COUNT(*) FROM follows WHERE followed_username = ?", (username,)).fetchone()[0]
    following = cur.execute("SELECT COUNT(*) FROM follows WHERE follower_username = ?", (username,)).fetchone()[0]
    posts_count = cur.execute("SELECT COUNT(*) FROM social_feed WHERE username_handle = ?", (username,)).fetchone()[0]
    user_posts = cur.execute("SELECT * FROM social_feed WHERE username_handle = ? ORDER BY id DESC", (username,)).fetchall()
    is_following = False
    if viewer:
        if cur.execute("SELECT 1 FROM follows WHERE follower_username = ? AND followed_username = ?", (viewer, username)).fetchone(): is_following = True
    conn.close()
    # --- get_user_profile_stats fonksiyonunun return kısmı ---
    
    # Lig Hesapla
    user_xp = user_row['xp'] if user_row['xp'] else 0
    league_info = calculate_league(user_xp)

    return { 
        "username": username, 
        "full_name": user_row['full_name'], 
        "avatar_url": user_row['avatar_url'], 
        "xp": user_xp, 
        "league": league_info, # <-- YENİ EKLENEN
        "followers": followers, 
        "following": following, 
        "posts": posts_count, 
        "is_following": is_following, 
        "feed_posts": user_posts 
    }

@app.get("/user/followers/{username}")
async def get_followers_list(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    query = "SELECT u.username, u.full_name, u.avatar_url FROM follows f JOIN users u ON f.follower_username = u.username WHERE f.followed_username = ?"
    rows = cur.execute(query, (username,)).fetchall(); conn.close()
    return rows

@app.get("/user/following/{username}")
async def get_following_list(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    query = "SELECT u.username, u.full_name, u.avatar_url FROM follows f JOIN users u ON f.followed_username = u.username WHERE f.follower_username = ?"
    rows = cur.execute(query, (username,)).fetchall(); conn.close()
    return rows

@app.get("/social/feed")
async def get_social_feed(username: str = None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        # SQL JOIN İLE VERİ ÇEKME (Daha Hızlı ve Sıralanabilir)
        # social_feed tablosunu users tablosuyla birleştiriyoruz.
        # Böylece XP'ye göre sıralama yapabiliriz.
        base_query = """
            SELECT s.*, u.xp, u.avatar_url, u.full_name as user_real_name
            FROM social_feed s 
            LEFT JOIN users u ON s.username_handle = u.username
        """
        
        params = ()
        
        if username:
            # Profil sayfası içinse sadece o kişinin postları (Tarihe göre)
            query = base_query + " WHERE s.username_handle = ? ORDER BY s.id DESC"
            params = (username,)
        else:
            # KEŞFET SAYFASI İÇİN ÖDÜL MEKANİZMASI BURADA:
            # 1. Kural: (CASE WHEN...) XP'si 150 ve üzeri olanları (Gümüş+) "1" grubuna al ve öne koy.
            # 2. Kural: Diğerlerini "0" grubuna al.
            # 3. Kural: Her grup kendi içinde en yeniden en eskiye sıralansın.
            query = base_query + " ORDER BY (CASE WHEN u.xp >= 150 THEN 1 ELSE 0 END) DESC, s.id DESC LIMIT 50"
            
        rows = conn.execute(query, params).fetchall()
        
        results = []
        for row in rows:
            item = dict(row)
            
            # Veri güvenliği kontrolleri
            if 'duel_wins' not in item: item['duel_wins'] = 0
            if item.get('xp') is None: item['xp'] = 0
            
            # Tablodaki eski ismi, users tablosundaki güncel isimle güncelle
            if item.get('user_real_name'): 
                item['user_name'] = item['user_real_name']
            
            results.append(item)
            
        return results

    except Exception as e:
        print(f"FEED HATASI: {e}")
        return []
    finally:
        conn.close()

@app.get("/social/leaderboard")
async def get_leaderboard():
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    try:
        query = "SELECT * FROM social_feed WHERE duel_wins > 0 ORDER BY duel_wins DESC LIMIT 10"
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]
    except: return []
    finally: conn.close()

@app.get("/duel/pair")
async def get_duel_pair(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM social_feed ORDER BY RANDOM() LIMIT 2").fetchall()
    conn.close()
    if len(rows) < 2: return {"error": "Düello için yeterli kombin yok. İlk paylaşımı sen yap!"}
    return {"left": dict(rows[0]), "right": dict(rows[1])}

@app.post("/duel/vote")
async def vote_duel(winner_id: int = Form(...)):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    try:
        post = conn.execute("SELECT username_handle FROM social_feed WHERE id = ?", (winner_id,)).fetchone()
        if post:
            conn.execute("UPDATE social_feed SET duel_wins = duel_wins + 1 WHERE id = ?", (winner_id,))
            conn.execute("UPDATE users SET xp = xp + 3 WHERE username = ?", (post['username_handle'],))
            conn.commit()
    except Exception as e: print(e)
    finally: conn.close()
    return {"status": "voted"}

@app.get("/clothes/showcase/{showcase_type}")
def get_showcase_items(showcase_type: str, username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"--> Showcase İsteği Geldi: Tip={showcase_type}, Kullanıcı={username}")

    try:
        if showcase_type == 'new':
            c.execute("SELECT * FROM clothes WHERE username = ? ORDER BY id DESC LIMIT 20", (username,))
        
        elif showcase_type == 'dusty':
            c.execute("SELECT * FROM clothes WHERE username = ? ORDER BY COALESCE(wear_count, 0) ASC, id ASC LIMIT 20", (username,))
            
        else:
            print("--> Geçersiz Showcase Tipi")
            return []

        rows = c.fetchall()
        print(f"--> Bulunan Kıyafet Sayısı: {len(rows)}") # Sonucu konsola yaz
        
        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "url": f"/uploads/{r['filename']}" if 'filename' in r.keys() else r['url'], # Eski/Yeni url yapısını destekle
                "category": r["category"],
                "wear_count": r["wear_count"] if r["wear_count"] is not None else 0,
                "color_name": r["color_name"],
                "season": r["season"],
                "style": r["style"]
            })
            
        return items

    except Exception as e:
        print(f"!!! Showcase Hatası !!!: {e}")
        return []
    finally:
        conn.close()
@app.get("/clothes/")
async def get_clothes(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM clothes WHERE username = ? ORDER BY id DESC", (username,))
        rows = c.fetchall()
    
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Listeleme Hatası: {e}")
        return []
    finally:
        conn.close()

@app.delete("/clothes/{item_id}")
async def delete_item(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM clothes WHERE id = ?", (item_id,))
    conn.execute("DELETE FROM saved_outfits WHERE top_id = ? OR bottom_id = ? OR shoe_id = ?", (item_id, item_id, item_id))
    conn.commit(); conn.close()
    return {"status": "deleted"}

@app.post("/clothes/update")
async def update_clothing_item(data: ItemUpdateSchema):
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("UPDATE clothes SET category = ?, season = ?, style = ?, sub_category = ? WHERE id = ?", 
                     (data.category, data.season, data.style, data.sub_category, data.id))
        conn.commit()
        return {"status": "success", "message": "Parça başarıyla güncellendi."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@app.post("/process/")
async def process_image(
    file: UploadFile = File(...), 
    category: str = Form(...), 
    season: str = Form(...), 
    style: str = Form(...), 
    username: str = Form(...),
    sub_category: str = Form(None)
): 
    # 1. Limit Kontrolü
    allowed, msg = check_limits(username, 'upload')
    if not allowed:
        return {"error": msg}
    
    # 2. Resmi Okuma
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB") # RGB'ye çevirip hafızayı rahatlat
    
    # 📉 SÜPER EKO MOD: Resmi 600px'e düşür (RAM tasarrufu)
    img.thumbnail((600, 600)) 
    
    # Hafıza temizliği 1
    del contents
    gc.collect()

    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}.png"
    
    # Klasör kontrolü
    upload_folder = os.path.join(base_path, "static", "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, filename)
    
    try:
        # ✅ Yapay Zeka İşlemi
        print("🤖 AI İşlemi Başlıyor...")
        
        # Session'ı burada oluşturuyoruz
        my_session = new_session("u2netp") 
        out = remove(img, session=my_session) 
        
        # Rengi analiz et
        color_name = analyze_clothing_color(out)
        
        # Kaydet
        out.save(path, format="PNG", optimize=True)
        print("✅ İşlem Başarılı!")

    except Exception as e:
        print(f"🚨 AI Hatası: {e}")
        # Hata olursa orijinalin küçültülmüş halini kaydet
        img.save(path, format="PNG")
        color_name = "Bilinmiyor"
    
    finally:
        # 🧹 TEMİZLİK ZAMANI (Çok Önemli)
        # Değişkenleri sil ve hafızayı boşalt
        if 'out' in locals(): del out
        if 'my_session' in locals(): del my_session
        del img
        gc.collect() # Çöp toplayıcıyı zorla çalıştır

    url = f"/static/uploads/{filename}"
    
    # 4. Veritabanı Kayıt
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO clothes (username, url, category, season, style, color_name, wear_count, is_clean, sub_category, image_hash) VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)", 
                (username, url, category, season, style, color_name, sub_category, '0'))
    conn.commit()
    conn.close()
    
    # 5. XP Verme
    message = "Kıyafet eklendi!"
    if check_daily_xp_cap(username, 'upload', limit=5):
        update_user_xp(username, 5)
        try:
            conn = sqlite3.connect(DB_FILE)
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute("INSERT INTO xp_logs (username, action_type, xp_amount, log_date) VALUES (?, ?, ?, ?)", 
                         (username, 'upload', 5, today))
            conn.commit(); conn.close()
        except: pass
        message += " (+5 XP)"

    return {"url": url, "color": color_name, "message": message}
@app.get("/recommend/")
async def recommend_outfit(season: str, style: str, username: str, event: str = None, outfit_type: str = "normal", force: bool = False):
    
    # --- 1. PREMIUM LİMİT KONTROLÜ (YENİ EKLENEN KISIM) ---
    allowed, msg = check_limits(username, 'ai_gen')
    if not allowed:
        return {"error": msg} # Frontend bu hatayı görünce uyarı verecek
    # ------------------------------------------------------

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT id, category, sub_category, color_name, season, style, url FROM clothes WHERE username = ? AND is_clean = 1", (username,))
    wardrobe = [dict(row) for row in c.fetchall()]
    conn.close()

    if not wardrobe:
        return {"error": "Dolabın boş veya temiz kıyafetin kalmamış! 🧺"}

    import random
    random.shuffle(wardrobe)

    inventory_text = ""
    for item in wardrobe:
        detay = item['sub_category'] if item['sub_category'] else item['style']
        inventory_text += f"- ID:{item['id']} | Renk:{item['color_name']} | Tip:{item['category']} ({detay}) | Mevsim:{item['season']}\n"

    prompt = f"""
    Sen moda uzmanısın. Aşağıdaki gardıroptan {season} mevsimine ve {style} tarzına uygun bir kombin yap.
    
    KURALLAR:
    1. Alt, Üst ve Ayakkabı seç.
    2. Ayrıca uygun bir AKSESUAR seç (accessory_id). Yoksa null yap.
    3. Sadece JSON formatında cevap ver.
    
    ENVANTER:
    {inventory_text}
    
    İSTENEN JSON FORMATI:
    {{
        "top_id": 123,
        "bottom_id": 456,
        "shoe_id": 789,
        "accessory_id": 101,
        "message": "Kısa stil notu"
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        res = json.loads(response_text)
        
        def find_item(iid):
            return next((x for x in wardrobe if x['id'] == iid), None) if iid else None

        # --- 2. İŞLEM BAŞARILI, SAYACI İŞLE (YENİ EKLENEN KISIM) ---
        try:
            conn = sqlite3.connect(DB_FILE)
            today = datetime.now().strftime("%Y-%m-%d")
            # XP vermiyoruz (0), sadece log tutuyoruz ki sayabilelim
            conn.execute("INSERT INTO xp_logs (username, action_type, xp_amount, log_date) VALUES (?, ?, ?, ?)", 
                         (username, 'ai_gen', 0, today))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Log Hatası: {e}")
        # -----------------------------------------------------------

        return {
            "message": res.get("message", "Hazır!"),
            "ust": find_item(res.get("top_id")),
            "alt": find_item(res.get("bottom_id")),
            "ayakkabi": find_item(res.get("shoe_id")),
            "aksesuar": find_item(res.get("accessory_id")),
            "dress": find_item(res.get("top_id")) if outfit_type == 'elbise' else None
        }

    except Exception as e:
        print(f"HATA: {e}")
        return {"error": "Stilist şu an meşgul."}

@app.post("/outfits/save")
async def save_outfit(outfit: OutfitSchema):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO saved_outfits (username, top_id, bottom_id, shoe_id) VALUES (?, ?, ?, ?)", (outfit.username, outfit.top_id, outfit.bottom_id, outfit.shoe_id))
    conn.commit(); conn.close()
    update_user_xp(outfit.username, 2)
    return {"status": "saved"}

@app.get("/outfits/")
async def get_saved_outfits(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    query = '''SELECT s.id, s.top_id, s.bottom_id, s.shoe_id, t.url as top_url, t.color_name as top_color, b.url as bottom_url, b.color_name as bottom_color, sh.url as shoe_url, sh.color_name as shoe_color FROM saved_outfits s LEFT JOIN clothes t ON s.top_id = t.id LEFT JOIN clothes b ON s.bottom_id = b.id LEFT JOIN clothes sh ON s.shoe_id = sh.id WHERE s.username = ? ORDER BY s.id DESC'''
    cur.execute(query, (username,)); rows = cur.fetchall(); conn.close()
    return rows

@app.delete("/outfits/{id}")
async def delete_outfit(id: int):
    conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM saved_outfits WHERE id = ?", (id,)); conn.commit(); conn.close()
    return {"status": "deleted"}

@app.post("/calendar/add")
async def add_to_calendar(plan: PlanSchema):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    
    ids = [plan.top_id]
    if plan.bottom_id and plan.bottom_id > 0: ids.append(plan.bottom_id)
    if plan.shoe_id: ids.append(plan.shoe_id)
    
    placeholders = ','.join('?' for _ in ids)
    cur.execute(f"SELECT url FROM clothes WHERE id IN ({placeholders})", ids)
    urls = [r['url'] for r in cur.fetchall()]
    conn.close()
    
    try: dt = datetime.strptime(plan.date_str, "%Y-%m-%d"); title = f"{format_date_tr(dt)} Planı"
    except: title = "Günlük Plan"
    
    plan_data = { "top_id": plan.top_id, "bottom_id": plan.bottom_id, "shoe_id": plan.shoe_id, "preview_urls": urls }
    
    conn = sqlite3.connect(DB_FILE)
    conn.execute("REPLACE INTO planned_outfits (username, plan_date, top_id, bottom_id, shoe_id) VALUES (?, ?, ?, ?, ?)", 
                 (plan.username, plan.date_str, plan.top_id, plan.bottom_id, plan.shoe_id))
    
    conn.execute("INSERT INTO user_plans (username, type, title, data) VALUES (?, ?, ?, ?)", (plan.username, 'calendar', title, json.dumps(plan_data)))
    conn.commit(); conn.close()
    
    return {"status": "planned"}
@app.get("/calendar/check/{username}/{date_str}")
async def check_calendar(username: str, date_str: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    query = '''SELECT p.id, t.url as top_url, t.id as top_id, b.url as bottom_url, b.id as bottom_id, sh.url as shoe_url, sh.id as shoe_id FROM planned_outfits p LEFT JOIN clothes t ON p.top_id = t.id LEFT JOIN clothes b ON p.bottom_id = b.id LEFT JOIN clothes sh ON p.shoe_id = sh.id WHERE p.plan_date = ? AND p.username = ?'''
    cur.execute(query, (date_str, username)); row = cur.fetchone(); conn.close()
    if row: return dict(row)
    return {"empty": True}

@app.post("/travel/pack")
async def pack_suitcase(req: TravelRequest):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    
    cur.execute("SELECT * FROM clothes WHERE username = ? AND (season = ? OR season = 'mevsimlik' OR season = '4 Mevsim')", (req.username, req.season))
    items = cur.fetchall()
    
    ustler = [x for x in items if x['category'] == 'ust_giyim']
    altlar = [x for x in items if x['category'] == 'alt_giyim']
    elbiseler = [x for x in items if x['category'] == 'elbise'] # Elbiseleri de alıyoruz
    ayakkabilar = [x for x in items if x['category'] == 'ayakkabi']
    
    if (len(ustler) < 1 or len(altlar) < 1) and len(elbiseler) < 1: 
        conn.close(); return {"error": "Bavul için yeterli kıyafetin yok."}
    
    days = min(req.days, 14); plan = [] # Max 14 gün sınırı koyalım
    
    for i in range(days):
        want_dress = (random.random() < 0.3) and (len(elbiseler) > 0)
        
        selected_shoe = random.choice(ayakkabilar) if ayakkabilar else None
        
        if want_dress:
            dress = random.choice(elbiseler)
            plan.append({
                "day": i + 1,
                "type": "dress", # Türü belirttik
                "ust_url": dress['url'],
                "ust_id": dress['id'],
                "alt_url": None, # Alt giyim yok
                "alt_id": 0,
                "shoe_url": selected_shoe['url'] if selected_shoe else None,
                "shoe_id": selected_shoe['id'] if selected_shoe else None
            })
        else:
            if not ustler or not altlar: continue 
            
            u = random.choice(ustler)
            a = random.choice(altlar)
            plan.append({
                "day": i + 1,
                "type": "normal",
                "ust_url": u['url'],
                "ust_id": u['id'],
                "alt_url": a['url'],
                "alt_id": a['id'],
                "shoe_url": selected_shoe['url'] if selected_shoe else None,
                "shoe_id": selected_shoe['id'] if selected_shoe else None
            })

    today = datetime.now(); start_date = today + timedelta(days=1); end_date = start_date + timedelta(days=req.days - 1)
    date_str = format_date_tr(start_date) if req.days == 1 else f"{format_date_tr(start_date)} - {format_date_tr(end_date)}"
    
    plan_json = json.dumps(plan)
    title = f"{req.destination} ({date_str})"
    
    conn.execute("INSERT INTO user_plans (username, type, title, data) VALUES (?, ?, ?, ?)", (req.username, 'travel', title, plan_json))
    conn.commit(); conn.close()
    
    return {"plan": plan}

@app.get("/plans/")
async def get_user_plans(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    cur.execute("SELECT * FROM user_plans WHERE username = ? ORDER BY id DESC", (username,)); rows = cur.fetchall(); conn.close()
    return rows

@app.delete("/plans/{id}")
async def delete_plan(id: int):
    conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM user_plans WHERE id = ?", (id,)); conn.commit(); conn.close()
    return {"status": "deleted"}

@app.post("/user/follow")
async def follow_user(data: FollowSchema):
    if data.follower == data.followed: return {"status": "error", "message": "Kendini takip edemezsin"}
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("INSERT INTO follows (follower_username, followed_username) VALUES (?, ?)", (data.follower, data.followed))
        msg = f"@{data.follower} seni takip etmeye başladı."
        conn.execute("INSERT INTO notifications (user_to, user_from, type, message) VALUES (?, ?, ?, ?)", (data.followed, data.follower, 'follow', msg))
        conn.commit(); conn.close(); return {"status": "success"}
    except sqlite3.IntegrityError:
        conn.close(); return {"status": "already_following"}

@app.post("/user/unfollow")
async def unfollow_user(data: FollowSchema):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM follows WHERE follower_username = ? AND followed_username = ?", (data.follower, data.followed))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.post("/social/share")
async def share_outfit(data: ShareSchema):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    ids = [data.top_id, data.bottom_id]
    if data.shoe_id: ids.append(data.shoe_id)
    placeholders = ','.join('?' for _ in ids)
    cur.execute(f"SELECT id, url FROM clothes WHERE id IN ({placeholders})", ids)
    items = {row['id']: row['url'] for row in cur.fetchall()}
    top_url = items.get(data.top_id); bottom_url = items.get(data.bottom_id); shoe_url = items.get(data.shoe_id) if data.shoe_id else None
    
    conn.execute("INSERT INTO social_feed (user_name, username_handle, top_url, bottom_url, shoe_url, top_id, bottom_id, shoe_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                 (data.user_name, data.username_handle, top_url, bottom_url, shoe_url, data.top_id, data.bottom_id, data.shoe_id))
    conn.commit(); conn.close()
    return {"status": "shared", "message": "Kombinin Keşfet'e düştü!"}

@app.post("/social/like")
async def like_post(data: LikeSchema):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    conn.execute("UPDATE social_feed SET likes = likes + 1 WHERE id = ?", (data.post_id,))
    post = conn.execute("SELECT username_handle FROM social_feed WHERE id = ?", (data.post_id,)).fetchone()
    if post and post['username_handle'] != data.liker_user:
        msg = f"@{data.liker_user} senin kombinini beğendi ❤️"
        conn.execute("INSERT INTO notifications (user_to, user_from, type, message) VALUES (?, ?, ?, ?)", (post['username_handle'], data.liker_user, 'like', msg))
    conn.commit(); conn.close()
    return {"status": "liked"}

@app.get("/init_comments_db")
async def init_comments_db():
    return {"status": "deprecated, use /fix_database_now"}

@app.get("/social/comments/{post_id}")
async def get_comments(post_id: int):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    query = "SELECT c.*, u.avatar_url, u.full_name FROM comments c LEFT JOIN users u ON c.username = u.username WHERE c.post_id = ? ORDER BY c.id ASC"
    rows = conn.execute(query, (post_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/social/comment")
async def add_comment(data: CommentSchema):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO comments (post_id, username, text) VALUES (?, ?, ?)", (data.post_id, data.username, data.text))
    conn.commit(); conn.close()
    update_user_xp(data.username, 1)
    return {"status": "added"}

@app.get("/notifications/{username}")
async def get_notifications(username: str):
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM notifications WHERE user_to = ? ORDER BY id DESC LIMIT 20", (username,)).fetchall()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_to = ?", (username,))
    conn.commit(); conn.close()
    return rows

# main.py dosyasındaki get_stats fonksiyonunu bununla değiştir:

@app.get("/stats/")
async def get_stats(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Toplam Parça Sayısı
    c.execute("SELECT COUNT(*) FROM clothes WHERE username = ?", (username,))
    total_clothes = c.fetchone()[0]

    # 2. Toplam Kombin Sayısı
    c.execute("SELECT COUNT(*) FROM outfits WHERE username = ?", (username,))
    total_outfits = c.fetchone()[0]

    # 3. Kategori Dağılımı (DÜZELTME BURADA)
    c.execute("SELECT category, COUNT(*) as cnt FROM clothes WHERE username = ? GROUP BY category", (username,))
    cat_rows = c.fetchall()
    
    # Varsayılan değerleri tanımlıyoruz ki boş olsa bile 0 dönsün
    categories = {
        "ust_giyim": 0, 
        "alt_giyim": 0, 
        "elbise": 0, 
        "ayakkabi": 0,
        "aksesuar": 0  # <--- EKSİK OLAN BU SATIRDI!
    }
    
    for row in cat_rows:
        # Veritabanındaki kategori ismini alıp sayıya eşitliyoruz
        if row['category'] in categories:
            categories[row['category']] = row['cnt']
        else:
            # Eğer tanımlı olmayan bir kategori varsa (örn: eski veri), onu da ekleyelim
            categories[row['category']] = row['cnt']

    # 4. Stil Dağılımı (Grafik için)
    c.execute("SELECT style, COUNT(*) as cnt FROM clothes WHERE username = ? GROUP BY style", (username,))
    style_rows = c.fetchall()
    styles = {row['style']: row['cnt'] for row in style_rows if row['style']}

    # 5. Mevsim Dağılımı (Grafik için)
    c.execute("SELECT season, COUNT(*) as cnt FROM clothes WHERE username = ? GROUP BY season", (username,))
    season_rows = c.fetchall()
    seasons = {row['season']: row['cnt'] for row in season_rows if row['season']}

    conn.close()

    return {
        "clothes": total_clothes,
        "outfits": total_outfits,
        "categories": categories, # Güncellenmiş kategori listesi
        "styles": styles,
        "seasons": seasons
    }


class ChatRequest(BaseModel):
    username: str
    message: str

import re  

@app.post("/ai/ask")
async def ask_stylist(req: ChatRequest):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, category, color_name FROM clothes WHERE username = ?", (req.username,))
    clothes = cur.fetchall()

    if not clothes:
        conn.close()
        return {"response": "Dolabın boş! Önce kıyafet yüklemelisin.", "items": []}

    inventory_str = ", ".join([f"{c['color_name']} {c['category']} (ID:{c['id']})" for c in clothes])
    
    system_prompt = f"""
    Sen yardımsever bir stilistsin. Kullanıcının dolabındaki kıyafetleri kullanarak sorularını yanıtla.
    DOLAP: {inventory_str}
    
    ÖNEMLİ: Eğer bir kıyafet önerirsen parantez içinde ID'sini yaz. Örnek: (ID:55).
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        ai_text = completion.choices[0].message.content
        
        found_ids = re.findall(r"ID:(\d+)", ai_text)
        suggested_items = []
        if found_ids:
            ids = tuple(set(map(int, found_ids)))
            if ids:
                placeholders = ','.join('?' * len(ids))
                rows = conn.execute(f"SELECT id, url, category, color_name FROM clothes WHERE id IN ({placeholders})", ids).fetchall()
                suggested_items = [dict(r) for r in rows]

        conn.close()
        return {"response": ai_text, "items": suggested_items}
    except Exception as e:
        print(f"Chat Hatası: {e}")
        conn.close()
        return {"response": "Bağlantı hatası.", "items": []}
    
@app.get("/clothes/dirty/{username}")
async def get_dirty_clothes(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM clothes WHERE username = ? AND is_clean = 0 ORDER BY id DESC", (username,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/clothes/dirty_selected")
async def dirty_selected_items(data: WashListSchema):
    if not data.item_ids:
        return {"status": "success", "message": "Her şey temiz kaldı!"}
    
    conn = sqlite3.connect(DB_FILE)
    placeholders = ','.join('?' * len(data.item_ids))
    sql = f"UPDATE clothes SET is_clean = 0 WHERE id IN ({placeholders})"
    conn.execute(sql, data.item_ids)
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"{len(data.item_ids)} parça kirli sepetine ayrıldı. 🧺"}

@app.post("/clothes/wash_selected")
async def wash_selected_items(data: WashListSchema):
    if not data.item_ids:
        return {"status": "error", "message": "Yıkanacak bir şey seçmedin."}
    
    conn = sqlite3.connect(DB_FILE)
    placeholders = ','.join('?' * len(data.item_ids))
    sql = f"UPDATE clothes SET is_clean = 1 WHERE id IN ({placeholders})"
    conn.execute(sql, data.item_ids)
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Seçilenler yıkandı ve ütülendi! ✨"}

@app.post("/user/login")
async def login_user(user: UserLoginSchema):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # Kullanıcıyı bul
    db_user = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    conn.close()
    
    if not db_user:
        raise HTTPException(status_code=400, detail="Kullanıcı bulunamadı.")
    
    # Şifre kontrolü
    # Not: Eski kullanıcıların şifresi olmadığı için hata verebilir, bu yüzden kontrol ediyoruz.
    if not db_user['password_hash']:
         # Eğer eski kullanıcıysa ve şifresi yoksa, geçici olarak izin verelim veya şifre oluşturmaya zorlayalım.
         # Şimdilik "123456" varsayalım veya direkt reddedelim. Güvenlik için reddediyoruz:
         raise HTTPException(status_code=400, detail="Eski hesap! Lütfen yönetici ile iletişime geçin.")

    if not verify_password(user.password, db_user['password_hash']):
        raise HTTPException(status_code=400, detail="Şifre hatalı!")
        
    return {
        "status": "success", 
        "data": {
            "username": db_user["username"],
            "full_name": db_user["full_name"],
            "city": db_user["city"],
            "gender": db_user["gender"]
        }
    }
     
@app.get("/clothes/showcase/{showcase_type}")
async def get_showcase(showcase_type: str, username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    
    try:
        if showcase_type == 'new':
            query = "SELECT * FROM clothes WHERE username = ? ORDER BY id DESC LIMIT 10"
        
        elif showcase_type == 'dusty':
            query = "SELECT * FROM clothes WHERE username = ? ORDER BY wear_count ASC, id ASC LIMIT 10"
            
        else:
            return []

        rows = conn.execute(query, (username,)).fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        print(f"Showcase Error: {e}")
        return []
    finally:
        conn.close() 
        
@app.post("/wear/confirm")
async def confirm_wear_count(data: WearConfirmSchema):
    conn = sqlite3.connect(DB_FILE)
    
    ids = [data.top_id, data.bottom_id]
    if data.shoe_id: ids.append(data.shoe_id)
    placeholders = ','.join('?' for _ in ids)
    conn.execute(f"UPDATE clothes SET wear_count = wear_count + 1 WHERE id IN ({placeholders})", ids)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO wear_logs (username, top_id, bottom_id, shoe_id, wear_date, is_reviewed) VALUES (?, ?, ?, ?, ?, 0)",
        (data.username, data.top_id, data.bottom_id, data.shoe_id, today_str)
    )
    
    conn.commit()
    conn.close()
    return {"status": "updated", "message": "Kombin giyildi olarak işaretlendi! Yarın görüşürüz. 👋"}

@app.get("/wear/pending_review/{username}")
async def check_pending_review(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    query = '''
        SELECT w.*, 
               t.url as top_url, 
               b.url as bottom_url, 
               s.url as shoe_url 
        FROM wear_logs w
        LEFT JOIN clothes t ON w.top_id = t.id
        LEFT JOIN clothes b ON w.bottom_id = b.id
        LEFT JOIN clothes s ON w.shoe_id = s.id
        WHERE w.username = ? AND w.is_reviewed = 0 AND w.wear_date < ?
        ORDER BY w.id DESC LIMIT 1
    '''
    row = conn.execute(query, (username, today_str)).fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {"status": "no_pending"}

class DirtyReviewSchema(BaseModel):
    log_id: int
    dirty_ids: list[int]

@app.post("/wear/submit_review")
async def submit_wear_review(data: DirtyReviewSchema):
    conn = sqlite3.connect(DB_FILE)
    
    conn.execute("UPDATE wear_logs SET is_reviewed = 1 WHERE id = ?", (data.log_id,))
    
    if data.dirty_ids:
        placeholders = ','.join('?' for _ in data.dirty_ids)
        conn.execute(f"UPDATE clothes SET is_clean = 0 WHERE id IN ({placeholders})", data.dirty_ids)
    
    conn.commit()
    conn.close()
    return {"status": "success"}   
class ImportUrlSchema(BaseModel):
    url: str
    username: str
    category: str = None

def scrape_product_metadata(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        image_url = ""
        og_image = soup.find("meta", property="og:image")
        if og_image: image_url = og_image["content"]
        else:
            img_tag = soup.find("img")
            if img_tag: image_url = img_tag.get("src")
            
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title: title = og_title["content"]
        else:
            if soup.title: title = soup.title.string

        if not image_url: return {"error": "Resim bulunamadı."}
        return {"image_url": image_url, "title": title}
    except Exception as e: return {"error": str(e)}

@app.post("/import/url")
async def import_from_url(data: ImportUrlSchema):
    # Linkten bilgileri çek
    meta = scrape_product_metadata(data.url)
    if "error" in meta: raise HTTPException(status_code=400, detail=meta["error"])
    
    try:
        img_response = requests.get(meta["image_url"])
        img = Image.open(io.BytesIO(img_response.content))
    except: raise HTTPException(status_code=400, detail="Resim indirilemedi.")

    # Resmi işle (Arka plan sil, kırp, renk bul)
    unique_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{unique_id}.png")
    out = remove(img)
    out = crop_image(out)
    color_name = analyze_clothing_color(out)
    out.save(path)
    url = f"/uploads/{unique_id}.png"
    
    # --- MANTIK: KATEGORİ BELİRLEME ---
    final_category = "ust_giyim" # Varsayılan

    # Eğer Frontend'den kategori geldiyse (Örn: Kullanıcı Aksesuar sekmesindeyse) onu KİLİTLE.
    if data.category and data.category in ["ust_giyim", "alt_giyim", "elbise", "ayakkabi", "aksesuar"]:
        final_category = data.category
    else:
        # Kategori gelmediyse başlığa bakarak tahmin et (Eski yöntem)
        title_lower = str(meta["title"]).lower()
        if any(x in title_lower for x in ["pantolon", "şort", "etek", "jean", "tayt"]): final_category = "alt_giyim"
        elif any(x in title_lower for x in ["elbise", "tulum", "dress"]): final_category = "elbise"
        elif any(x in title_lower for x in ["ayakkabı", "bot", "çizme", "sneaker"]): final_category = "ayakkabi"
        elif any(x in title_lower for x in ["çanta", "saat", "gözlük", "kolye", "küpe", "şapka", "toka"]): final_category = "aksesuar"

    # --- MANTIK: ALT KATEGORİ (SUB_CATEGORY) BULMA ---
    # Linki ve Başlığı birleştirip içinde kelime avına çıkıyoruz.
    search_text = (str(meta["title"]) + " " + data.url).lower()
    final_sub_category = None

    if final_category == "aksesuar":
        if any(x in search_text for x in ["gözlük", "gozluk", "sunglass", "eyewear"]): final_sub_category = "gozluk"
        elif any(x in search_text for x in ["çanta", "canta", "bag", "backpack", "cuzdan", "wallet", "clutch"]): final_sub_category = "canta"
        elif any(x in search_text for x in ["saat", "watch", "kordon"]): final_sub_category = "saat"
        elif any(x in search_text for x in ["şapka", "sapka", "cap", "hat", "bere", "beanie"]): final_sub_category = "sapka"
        elif any(x in search_text for x in ["kolye", "küpe", "bileklik", "yüzük", "taki", "jewelry", "ring", "necklace", "earring"]): final_sub_category = "taki"
        elif any(x in search_text for x in ["kemer", "belt", "askı"]): final_sub_category = "kemer"
        else: final_sub_category = "diger"
    
    elif final_category == "ust_giyim":
        if any(x in search_text for x in ["gömlek", "shirt"]): final_sub_category = "gomlek"
        elif any(x in search_text for x in ["tişört", "t-shirt", "tshirt"]): final_sub_category = "tisort"
        elif any(x in search_text for x in ["kazak", "hırka", "sweat"]): final_sub_category = "kislik_ust"

    # Veritabanına Kaydet
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO clothes (username, url, category, season, style, color_name, wear_count, is_clean, sub_category) VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?)", 
                 (data.username, url, final_category, "mevsimlik", "gunluk", color_name, final_sub_category))
    conn.commit()
    conn.close()
    
    update_user_xp(data.username, 15)
    
    return {
        "status": "success", 
        "url": url, 
        "title": meta["title"], 
        "category": final_category, 
        "sub_category": final_sub_category, 
        "color": color_name
    }
    
    # --- TEMİZLENMİŞ AFFILIATE KODLARI (Sadece bunu yapıştır) ---

@app.get("/affiliate/suggest-missing-piece")
async def suggest_missing_piece(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT gender FROM users WHERE username = ?", (username,))
    user_row = c.fetchone()
    user_gender = user_row['gender'] if user_row and user_row['gender'] else "Belirsiz"

    c.execute("SELECT category, color_name, style FROM clothes WHERE username = ?", (username,))
    items = [dict(row) for row in c.fetchall()]

    if not items:
        conn.close()
        return {"error": "Dolabın boş!"}

    inventory_summary = "\n".join([f"- {i['color_name']} {i['category']}" for i in items])

    prompt = f"""
    Sen profesyonel bir stilistsin.
    MÜŞTERİ: {user_gender}
    DOLAP: {inventory_summary}
    GÖREV: Bu dolapta eksik olan TEK BİR parça öner.
    CEVAP (JSON): {{ "item_name": "...", "reason": "...", "search_query": "..." }}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        ai_data = json.loads(completion.choices[0].message.content)
        product_name = ai_data.get("item_name", "Ürün")
        search_query = ai_data.get("search_query", product_name)

        final_link = ""
        all_links = c.execute("SELECT id, keyword, link FROM affiliate_links").fetchall()
        
        found_match = None
        
        # Döngüyle her satırı kontrol et
        for row in all_links:
            # Veritabanındaki "Ceket, Mont, Kaban" verisini virgülle ayır
            keywords_list = [k.strip().lower() for k in row['keyword'].split(',')]
            
            # AI'nın önerdiği ürün isminde bu kelimelerden biri geçiyor mu?
            for k in keywords_list:
                if k in product_name.lower():
                    found_match = row
                    break
            if found_match:
                break
        
        if found_match:
            final_link = found_match['link']
            # Tıklanma sayısını artır
            c.execute("UPDATE affiliate_links SET click_count = click_count + 1 WHERE id = ?", (found_match['id'],))
            conn.commit()
            print(f"💰 Veritabanından Link Çekildi: {found_match['keyword']}")
        else:
            # Yoksa Otomatik Arama Linki
            encoded_query = requests.utils.quote(search_query)
            final_link = f"https://www.trendyol.com/sr?q={encoded_query}"

        conn.close()
        return {
            "item_name": product_name,
            "reason": ai_data.get("reason"),
            "affiliate_link": final_link,
            "search_query": search_query
        }

    except Exception as e:
        print(f"Hata: {e}")
        conn.close()
        fallback_query = "erkek beyaz tişört" if user_gender == "Erkek" else "kadın beyaz tişört"
        return {
            "item_name": "Basic Tişört",
            "reason": "Hata oluştu.",
            "affiliate_link": f"https://www.trendyol.com/sr?q={requests.utils.quote(fallback_query)}",
            "search_query": fallback_query
        }

# --- YÖNETİCİ FONKSİYONLARI ---

class LinkAddSchema(BaseModel):
    keyword: str
    link: str

@app.post("/affiliate/add-link")
async def add_affiliate_link(data: LinkAddSchema):
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("INSERT INTO affiliate_links (keyword, link) VALUES (?, ?)", (data.keyword, data.link))
        conn.commit()
        return {"status": "success", "message": "Link eklendi!"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Bu kelime zaten var."}
    finally:
        conn.close()

@app.get("/affiliate/list")
async def list_affiliate_links():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, keyword, link, click_count FROM affiliate_links ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.delete("/affiliate/delete/{link_id}")
async def delete_affiliate_link(link_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM affiliate_links WHERE id = ?", (link_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

class LinkUpdateSchema(BaseModel):
    id: int
    keyword: str
    link: str

@app.post("/affiliate/update")
async def update_affiliate_link(data: LinkUpdateSchema):
    conn = sqlite3.connect(DB_FILE)
    try:
        # ID'ye göre güncelle
        conn.execute("UPDATE affiliate_links SET keyword = ?, link = ? WHERE id = ?", (data.keyword, data.link, data.id))
        conn.commit()
        return {"status": "success", "message": "Link güncellendi!"}
    except Exception as e:
        return {"status": "error", "message": f"Hata: {str(e)}"}
    finally:
        conn.close()
        
     # --- PREMIUM SATIN ALMA SİMÜLASYONU ---

class UpgradeSchema(BaseModel):
    username: str

@app.post("/user/upgrade")
async def upgrade_to_premium(data: UpgradeSchema):
    conn = sqlite3.connect(DB_FILE)
    try:
        # 1 Yıllık Premium verelim
        expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        conn.execute("UPDATE users SET is_premium = 1, premium_expiry = ? WHERE username = ?", (expiry, data.username))
        conn.commit()
        return {"status": "success", "message": "Hoş geldin VIP üye! Artık sınırsızsın. 💎"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()   
        
@app.delete("/social/post/{post_id}")
async def delete_social_post(post_id: int):
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("DELETE FROM social_feed WHERE id = ?", (post_id,))
        conn.commit()
        return {"status": "success", "message": "Paylaşım silindi."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()    
        
# --- BAŞKASININ PROFİLİNİ GÖRÜNTÜLEME ---
@app.get("/user/public_profile/{username}")
async def get_public_profile(username: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Kullanıcı Bilgileri
        user = conn.execute("SELECT username, bio, profile_pic_url, is_premium FROM users WHERE username = ?", (username,)).fetchone()
        
        if not user:
            return {"status": "error", "message": "Kullanıcı bulunamadı"}

        # 2. Takipçi Sayısı
        followers = conn.execute("SELECT COUNT(*) as count FROM follows WHERE user_to = ?", (username,)).fetchone()['count']
        
        # 3. Takip Edilen Sayısı
        following = conn.execute("SELECT COUNT(*) as count FROM follows WHERE user_from = ?", (username,)).fetchone()['count']

        return {
            "status": "success",
            "username": user["username"],
            "bio": user["bio"] if user["bio"] else "Merhaba, ben yeni bir kullanıcıyım.",
            "profile_pic": user["profile_pic_url"], # Eğer yoksa frontend varsayılan koyacak
            "is_premium": user["is_premium"],
            "followers": followers,
            "following": following
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:

        conn.close()           




















