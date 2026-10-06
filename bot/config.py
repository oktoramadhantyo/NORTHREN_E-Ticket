import os

from dotenv import load_dotenv

load_dotenv()

# ==================== KONFIGURASI BOT ====================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit(
        "TELEGRAM_BOT_TOKEN belum di-set. "
        "Buat file .env dari .env.example lalu isi token, "
        "atau set environment variable TELEGRAM_BOT_TOKEN."
    )

CHAT_IDS_FILE = "chat_ids.json"
BOT_STATE_FILE = "bot_state.json"
WILAYAH_STATE_FILE = "wilayah_state.json"
FILTER_STATE_FILE = "filter_state.json"
FILTER_TIKET_STATE_FILE = "filter_tiket_state.json"
PINNED_STATE_FILE = "pinned_state.json"
AWAL_CHAT_IDS = ["-5587626942"]

SHEET_ID = os.getenv("SHEET_ID", "1dXZpM8aqtalwxSImF4H34Q9_zwtIuGB7cGzpZx0_2VA").strip()
if not SHEET_ID:
    raise SystemExit(
        "SHEET_ID belum di-set. "
        "Isi env var SHEET_ID dengan ID spreadsheet sumber tiket "
        "(bagian URL di antara /d/ dan /edit)."
    )
CREDENTIAL_FILE = "modern-triumph-506502-u0-2b11a7b4943a.json"
CATATAN_FILE = "sent_tickets.json"

INTERVAL_MENIT = 5
REMINDER_JAM = 1

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ==================== SUMBER TIKET DARI SPREADSHEET ====================
SUMBER_TIKET = {
    "HVC": {
        "sheet_tab": "MONITORING TTR",
        "range": "P35:V200",
        "batas_jam": {"HVC_DIAMOND": 3, "HVC_PLATINUM": 6},
    },
    "HVC_GOLD": {
        "sheet_tab": "MONITORING TTR",
        "range": "X35:AD200",
        "batas_jam": {"HVC_GOLD": 12},
    },
    "REGULER": {
        "sheet_tab": "MONITORING TTR",
        "range": "AF35:AL200",
        "batas_jam": {"REGULER": 24},
    },
    "MANJA": {
        "sheet_tab": "MONITORING TTR",
        "range": "AN35:AS200",
        "batas_jam": {"MANJA": 3},
    },
    "FFG": {
        "sheet_tab": "FFG",
        "range": "H5:O200",
        "batas_jam": {"FFG": 3},
    },
}

KATEGORI_MONITORING = ["HVC", "HVC_GOLD", "REGULER", "MANJA"]

# ==================== WILAYAH & STO ====================
WILAYAH_STO = {
    "JAKUT": {"CIL", "MRD", "KLG", "KTX", "KTZ", "MKR", "PDM", "STR", "TPR"},
    "JAKBAR": {"CKG", "TGA", "KPK", "JIA", "KSB", "PLM", "KDY", "MRY", "SLP",
               "SMI", "DTG", "SDM"},
}
NAMA_WILAYAH = {"JAKUT": "Jakarta Utara", "JAKBAR": "Jakarta Barat",
                "SEMUA": "Northren (semua)"}

HVC_JENIS = {
    "HVC_DIAMOND": "HVC Diamond",
    "HVC_PLATINUM": "HVC Platinum",
}

STO_KE_WILAYAH = {}
for _w, _stos in WILAYAH_STO.items():
    for _s in _stos:
        STO_KE_WILAYAH[_s] = _w