"""Koneksi & pembacaan data dari Google Spreadsheet."""

import json
import os

import gspread
from google.oauth2.service_account import Credentials

from .config import (
    CREDENTIAL_FILE,
    KATEGORI_MONITORING,
    SCOPES,
    SHEET_ID,
    SUMBER_TIKET,
)

cred_json = os.getenv("GOOGLE_CREDENTIALS")
if cred_json:
    info = json.loads(cred_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
else:
    creds = Credentials.from_service_account_file(CREDENTIAL_FILE, scopes=SCOPES)

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
    """Peta no tiket -> booking date dari tabel manja."""
    peta = {}
    for row in rows_manja:
        if not row:
            continue
        no_tiket = str(row[0]).strip() if row[0] else ""
        tanggal = str(row[3]).strip() if len(row) > 3 and row[3] else ""
        if no_tiket.startswith("INC") and tanggal:
            peta[no_tiket] = tanggal.split(".")[0]
    return peta