import gspread
import requests
import json
import os
import time
import threading
from datetime import datetime
from google.oauth2.service_account import Credentials

# ==================== KONFIGURASI ====================
TOKEN = "8828118024:AAEUqSOABc2U5QJidjdrmlbvFFqodE-Broc"
CHAT_IDS_FILE = "chat_ids.json"
AWAL_CHAT_IDS = ["-5587626942"]

SHEET_ID = "1dXZpM8aqtalwxSImF4H34Q9_zwtIuGB7cGzpZx0_2VA"
CREDENTIAL_FILE = "modern-triumph-506502-u0-2b11a7b4943a.json"
CATATAN_FILE = "sent_tickets.json"

INTERVAL_MENIT = 5   # interval cek tiket baru (menit)
REMINDER_JAM = 1     # interval reminder tiket yang masih open (jam)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Range kolom tiap tabel rekap, sesuai struktur yang sudah dikonfirmasi.
SUMBER_TIKET = {
    "HVC": {
        "sheet_tab": "MONITORING TTR",  # tab utama
        "range": "P35:V200",
        # kolom: STO, NO TIKET, NO GANGGUAN, CUSTOMER TYPE, REPORT DATE, DURASI TTR, PIC
        "batas_jam": {"HVC_DIAMOND": 3, "HVC_PLATINUM": 6},
    },
    "HVC_GOLD": {
        "sheet_tab": "MONITORING TTR",
        "range": "X35:AD200",
        # kolom: STO, TIKET, NO GANGGUAN, CUSTOMER TYPE, REPORDATE, DURASI, PIC
        "batas_jam": {"HVC_GOLD": 12},
    },
    "REGULER": {
        "sheet_tab": "MONITORING TTR",
        "range": "AF35:AL200",
        # kolom: STO, TIKET, NO GANGGUAN, CUSTOMER TYPE, REPORDATE, DURASI, PIC
        "batas_jam": {"REGULER": 24},
    },
    "MANJA": {
        "sheet_tab": "MONITORING TTR",
        "range": "AN35:AS200",
        # kolom: NO TIKET, STO, CUSTOMER TYPE, BOOKING DATE, DURASI MANJA, PIC
        "batas_jam": {"MANJA": 3},
    },
    "FFG": {
        "sheet_tab": "FFG",  # tab terpisah
        "range": "H5:O200",
        # kolom: STO, NO TIKET, INET GANGGUAN, FLAGGING, REPORTED DATE, TANGGAL MANJA, Durasi TTR, PIC
        "batas_jam": {"FFG": 3},
    },
}

# urutan tabel di tab MONITORING TTR (dibaca sekaligus lewat batch_get)
KATEGORI_MONITORING = ["HVC", "HVC_GOLD", "REGULER", "MANJA"]

# ==================== SETUP KONEKSI SPREADSHEET ====================
cred_json = os.getenv("GOOGLE_CREDENTIALS")
if cred_json:
    info = json.loads(cred_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    print("Kredensial dimuat dari environment variable GOOGLE_CREDENTIALS")
else:
    creds = Credentials.from_service_account_file(CREDENTIAL_FILE, scopes=SCOPES)
    print(f"Kredensial dimuat dari file: {CREDENTIAL_FILE}")
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)


def ambil_worksheet(nama_tab):
    return sheet.worksheet(nama_tab)


def baca_data():
    """Baca SEMUA tabel sekali per siklus (hemat panggilan API):
    4 tabel MONITORING TTR dalam 1 batch_get + 1 panggilan untuk FFG."""
    ws_monitoring = ambil_worksheet("MONITORING TTR")
    rentang = [SUMBER_TIKET[k]["range"] for k in KATEGORI_MONITORING]
    data = dict(zip(KATEGORI_MONITORING, ws_monitoring.batch_get(rentang)))
    data["FFG"] = ambil_worksheet("FFG").get(SUMBER_TIKET["FFG"]["range"])
    return data


def bangun_peta_booking(rows_manja):
    """Peta no tiket -> booking date dari tabel manja (baris yang sama
    dipakai untuk kategori MANJA, jadi tidak perlu baca ulang ke sheet)."""
    peta = {}
    for row in rows_manja:
        if not row:
            continue
        no_tiket = str(row[0]).strip() if row[0] else ""
        tanggal = str(row[3]).strip() if len(row) > 3 and row[3] else ""
        if no_tiket.startswith("INC") and tanggal:
            peta[no_tiket] = tanggal.split(".")[0]
    return peta


# ==================== CATATAN GRUP YANG TERDAFTAR ====================
def load_chat_ids():
    env_ids = os.getenv("CHAT_IDS", "")
    env_list = [cid.strip() for cid in env_ids.split(",") if cid.strip()] if env_ids else []

    file_ids = []
    if os.path.exists(CHAT_IDS_FILE):
        with open(CHAT_IDS_FILE, "r") as f:
            file_ids = json.load(f)

    merged = list(dict.fromkeys(env_list + file_ids + AWAL_CHAT_IDS))
    if merged != file_ids:
        with open(CHAT_IDS_FILE, "w") as f:
            json.dump(merged, f)
    return merged


def save_chat_ids(ids):
    with open(CHAT_IDS_FILE, "w") as f:
        json.dump(ids, f)


def tambah_chat_id(chat_id):
    chat_id = str(chat_id)
    ids = load_chat_ids()
    if chat_id not in ids:
        ids.append(chat_id)
        save_chat_ids(ids)
        print(f"[GRUP] Grup baru terdaftar: {chat_id}")
        return True
    return False


def hapus_chat_id(chat_id):
    chat_id = str(chat_id)
    ids = load_chat_ids()
    if chat_id in ids:
        ids.remove(chat_id)
        save_chat_ids(ids)
        print(f"[GRUP] Grup dihapus: {chat_id}")
        return True
    return False


# ==================== CATATAN TIKET YANG SUDAH DIKIRIM ====================
def load_sent_tickets():
    if os.path.exists(CATATAN_FILE):
        with open(CATATAN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_sent_tickets(sent_set):
    with open(CATATAN_FILE, "w") as f:
        json.dump(list(sent_set), f)


# ==================== FORMAT PESAN ====================
def esc(teks):
    # escape karakter khusus HTML agar tidak merusak format pesan
    return str(teks).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal, durasi, pic_list, booking_date=""):
    label_tanggal = "BOOKING DATE" if kategori == "MANJA" else "REPORT DATE"
    # tiket ffg pakai label FLAGGING, jenis lain tetap CUSTOMER TYPE
    label_jenis = "FLAGGING" if kategori == "FFG" else "CUSTOMER TYPE"

    baris = [
        f"INCIDENT      : {esc(no_tiket)}",
        f"STO           : {esc(sto)}",
        f"NO GANGGUAN   : {esc(no_gangguan) if no_gangguan else '-'}",
        f"{label_jenis:<14}: {esc(cust_type)}",
        f"{label_tanggal:<14}: {esc(tanggal)}",
    ]
    # booking date hanya ditampilkan kalau tiketnya tercatat di tabel manja
    if booking_date:
        baris.append(f"{'BOOKING DATE':<14}: {esc(booking_date)}")
    baris.append(f"TTR           : {esc(durasi)}")

    return "<pre>\n" + "\n".join(baris) + f"\n</pre>\nPIC: {esc(pic_list)}"


def format_pesan(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal, durasi, pic_list, booking_date=""):
    judul = f"Tiket Open {cust_type} Northren" if kategori != "MANJA" else "Tiket Open Manja Northren"
    isi = blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal, durasi, pic_list, booking_date)
    return f"🚨 {esc(judul)}\n\n{isi}"


def format_pesan_reminder(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal,
                          durasi, pic_list, booking_date, batas_jam):
    judul = "⏰ Reminder Ticket Manja Northren" if kategori == "MANJA" \
        else f"⏰ Reminder Ticket {cust_type} Northren"
    isi = blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal, durasi, pic_list, booking_date)
    catatan = (f"\n\nnotes: Durasi ticket sudah lebih dari {batas_jam} jam. "
               f"mohon segera dikerjakan dan diprioritaskan sampai tuntas")
    return f"{esc(judul)}\n\n{isi}{catatan}"


# ==================== KIRIM KE TELEGRAM ====================
def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    chat_ids = load_chat_ids()
    hasil_semua = []
    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "HTML"}
        hasil = requests.post(url, data=payload).json()
        retry_after = hasil.get("parameters", {}).get("retry_after")
        if not hasil.get("ok") and retry_after:
            print(f"   Batas laju Telegram, tunggu {retry_after} detik...")
            time.sleep(retry_after)
            hasil = requests.post(url, data=payload).json()
        hasil_semua.append(hasil)
        time.sleep(1)
    return hasil_semua[0] if hasil_semua else {"ok": False}


# ==================== PROSES PER KATEGORI ====================
def ekstrak_tiket(nama_kategori, row):
    """Ambil field tiket dari satu baris sheet sesuai kategorinya."""
    def ambil(i):
        return str(row[i]).strip() if len(row) > i and row[i] else ""

    if nama_kategori == "MANJA":
        # kolom: NO TIKET, STO, CUSTOMER TYPE, BOOKING DATE, DURASI MANJA, PIC
        return {"no_tiket": ambil(0), "sto": ambil(1), "cust_type": ambil(2),
                "tanggal": ambil(3), "durasi": ambil(4), "pic": ambil(5),
                "no_gangguan": ""}
    if nama_kategori == "FFG":
        # kolom: STO, NO TIKET, INET GANGGUAN, FLAGGING, REPORTED DATE,
        #        TANGGAL MANJA, DURASI TTR, PIC
        # customer type diisi dari kolom FLAGGING (biasanya isinya "FFG")
        return {"sto": ambil(0), "no_tiket": ambil(1), "no_gangguan": ambil(2),
                "cust_type": ambil(3) or "FFG", "tanggal": ambil(4),
                "durasi": ambil(6), "pic": ambil(7)}
    # HVC / HVC_GOLD / REGULER, kolom: STO, TIKET, NO GANGGUAN, CUSTOMER TYPE,
    # REPORDATE, DURASI, PIC
    return {"sto": ambil(0), "no_tiket": ambil(1), "no_gangguan": ambil(2),
            "cust_type": ambil(3), "tanggal": ambil(4), "durasi": ambil(5),
            "pic": ambil(6)}


def hitung_jam_lewat(tanggal, booking_date):
    """Jam sejak tiket dibuat. Basis waktunya booking date kalau ada,
    kalau tidak ada pakai order/report date."""
    basis = booking_date or tanggal
    if not basis:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            mulai = datetime.strptime(basis.split(".")[0].strip(), fmt)
            return (datetime.now() - mulai).total_seconds() / 3600
        except ValueError:
            continue
    return None


def ambil_batas_jam(config, cust_type):
    # batas jam sesuai jenis tiket; kalau jenis tak dikenal pakai batas tertinggi
    return config["batas_jam"].get(cust_type, max(config["batas_jam"].values()))


def sudah_terkirim(no_tiket, nama_kategori, sent_tickets):
    # cek dengan prefix kategori + format catatan lama (polos, tanpa prefix)
    return f"{nama_kategori}:{no_tiket}" in sent_tickets or no_tiket in sent_tickets


def proses_kategori(nama_kategori, config, rows, sent_tickets, peta_booking=None):
    """Alert tiket baru: hanya dikirim sekali saat pertama terlihat."""
    if peta_booking is None:
        peta_booking = {}

    baru = 0
    for row in rows:
        if not row or len(row) < 2:
            continue

        t = ekstrak_tiket(nama_kategori, row)

        # hanya proses baris tiket asli (no tiket diawali "INC"),
        # supaya judul tabel / angka ringkasan tidak ikut terkirim
        if not t["no_tiket"].startswith("INC"):
            continue

        if sudah_terkirim(t["no_tiket"], nama_kategori, sent_tickets):
            continue

        # kategori MANJA sudah menampilkan booking date sebagai tanggal utamanya
        booking = "" if nama_kategori == "MANJA" else peta_booking.get(t["no_tiket"], "")

        pesan = format_pesan(kategori=nama_kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                             no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                             tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                             booking_date=booking)
        hasil = kirim_telegram(pesan)

        if hasil.get("ok"):
            sent_tickets.add(f"{nama_kategori}:{t['no_tiket']}")
            baru += 1
            print(f"[{nama_kategori}] Terkirim: {t['no_tiket']}")
        else:
            print(f"[{nama_kategori}] Gagal kirim {t['no_tiket']}: {hasil}")

    return baru


def proses_reminder(nama_kategori, config, rows, peta_booking=None):
    """Reminder: tiket yang MASIH ada di sheet dan durasinya sudah melewati
    batas jam jenisnya, dikirim ulang tiap siklus reminder."""
    if peta_booking is None:
        peta_booking = {}

    jumlah = 0
    for row in rows:
        if not row or len(row) < 2:
            continue

        t = ekstrak_tiket(nama_kategori, row)
        if not t["no_tiket"].startswith("INC"):
            continue

        booking = "" if nama_kategori == "MANJA" else peta_booking.get(t["no_tiket"], "")
        batas = ambil_batas_jam(config, t["cust_type"])

        jam_lewat = hitung_jam_lewat(t["tanggal"], booking)
        if jam_lewat is None or jam_lewat <= batas:
            continue  # belum lewat batas / tanggal tidak terbaca -> belum perlu reminder

        pesan = format_pesan_reminder(kategori=nama_kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                                      no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                                      tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                                      booking_date=booking, batas_jam=batas)
        hasil = kirim_telegram(pesan)

        if hasil.get("ok"):
            jumlah += 1
            print(f"[{nama_kategori}] Reminder ({jam_lewat:.0f} jam): {t['no_tiket']}")
        else:
            print(f"[{nama_kategori}] Gagal reminder {t['no_tiket']}: {hasil}")

    return jumlah


# ==================== MENU /MENU (FILTER TIKET PER WILAYAH & JENIS) ====================
# hasil parsing siklus terakhir: {kategori: [tiket, ...]} -> dipakai /menu
SIMPANAN_TIKET = {}

# pembagian STO per wilayah, sesuai tabel ringkasan di tab MONITORING TTR
WILAYAH_STO = {
    "JAKUT": {"CIL", "MRD", "KLG", "KTX", "KTZ", "MKR", "PDM", "STR", "TPR"},
    "JAKBAR": {"CKG", "TGA", "KPK", "JIA", "KSB", "PLM", "KDY", "MRY", "SLP",
               "SMI", "DTG", "SDM"},
}
NAMA_WILAYAH = {"JAKUT": "Jakarta Utara", "JAKBAR": "Jakarta Barat",
                "SEMUA": "Northren (semua)"}


def keyboard_wilayah():
    return json.dumps({"inline_keyboard": [
        [{"text": "🌆 Jakarta Utara", "callback_data": "wilayah:JAKUT"},
         {"text": "🌆 Jakarta Barat", "callback_data": "wilayah:JAKBAR"}],
        [{"text": "🌐 Semua (Northren)", "callback_data": "wilayah:SEMUA"}],
    ]})


HVC_JENIS = {
    "HVC_DIAMOND": "HVC Diamond",
    "HVC_PLATINUM": "HVC Platinum",
}


def keyboard_jenis(wilayah):
    return json.dumps({"inline_keyboard": [
        [{"text": "HVC Diamond", "callback_data": f"tiket:HVC_DIAMOND:{wilayah}"},
         {"text": "HVC Platinum", "callback_data": f"tiket:HVC_PLATINUM:{wilayah}"}],
        [{"text": "HVC_GOLD", "callback_data": f"tiket:HVC_GOLD:{wilayah}"}],
        [{"text": "REGULER", "callback_data": "tiket:REGULER:" + wilayah},
         {"text": "MANJA", "callback_data": "tiket:MANJA:" + wilayah}],
        [{"text": "FFG", "callback_data": "tiket:FFG:" + wilayah}],
        [{"text": "⬅️ Ganti wilayah", "callback_data": "menu:awal"}],
    ]})


# ==================== MENU /filterTicket ====================
def keyboard_filter():
    return json.dumps({"inline_keyboard": [
        [{"text": "HVC Diamond", "callback_data": "filter:HVC_DIAMOND"},
         {"text": "HVC Platinum", "callback_data": "filter:HVC_PLATINUM"}],
        [{"text": "HVC_GOLD", "callback_data": "filter:HVC_GOLD"}],
        [{"text": "REGULER", "callback_data": "filter:REGULER"},
         {"text": "MANJA", "callback_data": "filter:MANJA"}],
        [{"text": "FFG", "callback_data": "filter:FFG"}],
    ]})


def kirim_filter_tiket(chat_id, kategori):
    """Kirim semua tiket open per jenis sebagai pesan terpisah (bisa dicopy)."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    if kategori in HVC_JENIS:
        tiket = SIMPANAN_TIKET.get("HVC", [])
        tiket = [t for t in tiket if t.get("cust_type", "").upper().replace(" ", "_") == kategori]
    else:
        tiket = SIMPANAN_TIKET.get(kategori, [])

    nama_tampil = HVC_JENIS.get(kategori, kategori)

    if not tiket:
        requests.post(url, data={"chat_id": chat_id,
                                 "text": f"✅ Tidak ada tiket {nama_tampil} yang open saat ini."})
        return

    for t in tiket:
        booking = "" if kategori == "MANJA" else t.get("booking_date", "")
        isi = blok_isi(kategori=kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                       no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                       tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                       booking_date=booking)
        pesan = f"Filtering Ticket {esc(nama_tampil)}\n\n{isi}"
        requests.post(url, data={"chat_id": chat_id, "text": pesan, "parse_mode": "HTML"})
        time.sleep(1)


def kirim_menu(chat_id):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={
        "chat_id": chat_id,
        "text": "📍 Pilih wilayah:",
        "reply_markup": keyboard_wilayah(),
    })


def daftar_tiket(kategori, wilayah=""):
    """Teks daftar tiket open sesuai jenis (+wilayah), dari siklus terakhir."""
    # HVC subtypes diambil dari data HVC yang sama
    if kategori in HVC_JENIS:
        tiket = SIMPANAN_TIKET.get("HVC", [])
        cust_target = kategori
        tiket = [t for t in tiket if t.get("cust_type", "").upper().replace(" ", "_") == cust_target]
    else:
        tiket = SIMPANAN_TIKET.get(kategori)

    if tiket is None:
        return f"Jenis tiket '{kategori}' tidak dikenal."

    if wilayah in WILAYAH_STO:
        daftar_sto = WILAYAH_STO[wilayah]
        tiket = [t for t in tiket if t["sto"].upper() in daftar_sto]

    nama = NAMA_WILAYAH.get(wilayah, wilayah or "-")
    nama_tampil = HVC_JENIS.get(kategori, kategori)
    if not tiket:
        return f"✅ Tidak ada tiket {nama_tampil} wilayah {nama} saat ini."

    baris = [f"📋 Tiket {nama_tampil} wilayah {nama} masih open ({len(tiket)} tiket):"]
    for i, t in enumerate(tiket, 1):
        if kategori == "MANJA":
            baris.append(f"{i}. {t['no_tiket']} | STO {t['sto'] or '-'} | {t['tanggal'] or '-'}")
        else:
            baris.append(f"{i}. {t['no_tiket']} | STO {t['sto'] or '-'} | TTR {t['durasi'] or '-'}")
    return "\n".join(baris)


def kirim_panjang(chat_id, teks):
    """Kirim teks panjang dengan pecah per pesan (batas Telegram 4096 karakter)."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    batas = 3800
    while len(teks) > batas:
        potong = teks.rfind("\n", 0, batas)
        if potong == -1:
            potong = batas
        requests.post(url, data={"chat_id": chat_id, "text": teks[:potong]})
        time.sleep(1)
        teks = teks[potong:].lstrip("\n")
    if teks:
        requests.post(url, data={"chat_id": chat_id, "text": teks})


def tangani_update(update):
    """Pesan masuk dari user: perintah /menu atau tombol menu ditekan."""
    # deteksi bot di-add/di-kick dari grup
    if "my_chat_member" in update:
        cm = update["my_chat_member"]
        chat = cm.get("chat", {})
        chat_id = str(chat.get("id", ""))
        status = cm.get("new_chat_member", {}).get("status", "")
        if status in ("member", "administrator"):
            if tambah_chat_id(chat_id):
                nama = chat.get("title", chat_id)
                print(f"[GRUP] Bot ditambahkan ke grup: {nama} ({chat_id})")
        elif status in ("left", "kicked"):
            if hapus_chat_id(chat_id):
                print(f"[GRUP] Bot dihapus dari grup: {chat_id}")
        return

    if "callback_query" in update:
        cb = update["callback_query"]
        # matikan indikator loading pada tombol
        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                      data={"callback_query_id": cb["id"]})
        data = cb.get("data", "")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")
        if not chat_id:
            return

        if data == "menu:awal":
            kirim_menu(chat_id)

        elif data.startswith("wilayah:"):
            wilayah = data.split(":", 1)[1]
            nama = NAMA_WILAYAH.get(wilayah, wilayah)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={
                "chat_id": chat_id,
                "text": f"Wilayah {nama} — pilih jenis tiket:",
                "reply_markup": keyboard_jenis(wilayah),
            })

        elif data.startswith("tiket:"):
            _, kategori, wilayah = data.split(":", 2)
            kirim_panjang(chat_id, daftar_tiket(kategori, wilayah))

        elif data.startswith("filter:"):
            kategori = data.split(":", 1)[1]
            kirim_filter_tiket(chat_id, kategori)
        return

    if "message" in update:
        msg = update["message"]
        teks = (msg.get("text") or "").split("@")[0].strip().lower()
        # split('@') supaya /menu@NamaBot di grup tetap dikenali
        if teks == "/menu":
            kirim_menu(msg["chat"]["id"])
        elif teks == "/filterticket":
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={
                "chat_id": msg["chat"]["id"],
                "text": "🔍 Pilih jenis tiket:",
                "reply_markup": keyboard_filter(),
            })


def telegram_polling():
    """Thread pendengar pesan masuk (long polling getUpdates)."""
    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": offset + 1, "timeout": 30,
                        "allowed_updates": json.dumps(["message", "callback_query", "my_chat_member"])},
                timeout=35,
            ).json()
            for u in r.get("result", []):
                offset = u["update_id"]
                tangani_update(u)
        except Exception as e:
            print(f"[MENU] Error polling: {e}")
            time.sleep(5)


def simpan_snapshot_tiket(data):
    """Simpan hasil parsing semua tabel ke SIMPANAN_TIKET untuk fitur /menu."""
    global SIMPANAN_TIKET
    snapshot = {}
    for nama_kategori in SUMBER_TIKET:
        daftar = []
        for row in data[nama_kategori]:
            if not row or len(row) < 2:
                continue
            t = ekstrak_tiket(nama_kategori, row)
            if t["no_tiket"].startswith("INC"):
                daftar.append(t)
        snapshot[nama_kategori] = daftar
    SIMPANAN_TIKET.clear()
    SIMPANAN_TIKET.update(snapshot)


# ==================== SIKLUS UTAMA ====================
def jalankan_siklus(kirim_reminder=False):
    """Satu siklus lengkap: baca sheet sekali, lalu proses alert tiket baru
    dan (kalau waktunya) reminder dari data yang sama."""
    sent_tickets = load_sent_tickets()

    try:
        data = baca_data()
    except Exception as e:
        print(f"[{datetime.now():%d-%m-%Y %H:%M:%S}] Gagal baca spreadsheet: {e}")
        return

    peta_booking = bangun_peta_booking(data["MANJA"])
    simpan_snapshot_tiket(data)

    print(f"\n[{datetime.now():%d-%m-%Y %H:%M:%S}] Mengecek tiket baru...")
    total_baru = 0
    for nama_kategori, config in SUMBER_TIKET.items():
        try:
            total_baru += proses_kategori(nama_kategori, config,
                                          data[nama_kategori], sent_tickets, peta_booking)
        except Exception as e:
            # kalau satu kategori gagal (mis. koneksi putus), kategori lain tetap jalan
            print(f"[{nama_kategori}] Error: {e}")

    # catatan hanya ditulis kalau ada tiket baru (hemat IO)
    if total_baru:
        save_sent_tickets(sent_tickets)
    print(f"Selesai. Total tiket baru terkirim: {total_baru}")

    if not kirim_reminder:
        return

    print(f"[{datetime.now():%d-%m-%Y %H:%M:%S}] Mengirim reminder...")
    total_reminder = 0
    for nama_kategori, config in SUMBER_TIKET.items():
        try:
            total_reminder += proses_reminder(nama_kategori, config,
                                              data[nama_kategori], peta_booking)
        except Exception as e:
            print(f"[{nama_kategori}] Error reminder: {e}")
    print(f"Selesai. Total reminder terkirim: {total_reminder}")


def main():
    print(f"Bot berjalan. Tiket baru tiap {INTERVAL_MENIT} menit, "
          f"reminder tiap {REMINDER_JAM} jam. (Ctrl+C untuk stop)")

    # daftarkan perintah /menu ke telegram (biar muncul di tombol menu bot)
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/setMyCommands",
                      json={"commands": [{"command": "menu",
                                          "description": "Tampilkan tiket per jenis"},
                                         {"command": "filterTicket",
                                          "description": "Filter tiket per jenis (detail)"}]},
                      timeout=10)
    except Exception:
        pass

    # jalankan thread pendengar perintah /menu dari user
    threading.Thread(target=telegram_polling, daemon=True).start()

    reminder_berikutnya = time.time() + REMINDER_JAM * 3600

    while True:
        waktunya_reminder = time.time() >= reminder_berikutnya
        jalankan_siklus(waktunya_reminder)
        if waktunya_reminder:
            reminder_berikutnya = time.time() + REMINDER_JAM * 3600
        time.sleep(INTERVAL_MENIT * 60)


if __name__ == "__main__":
    main()
