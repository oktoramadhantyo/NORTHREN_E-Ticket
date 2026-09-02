"""Siklus utama bot: baca sheet, kirim alert/reminder, jalankan polling & loop."""

import threading
import time
from datetime import datetime

import requests

from . import handlers
from .config import INTERVAL_MENIT, REMINDER_JAM, SUMBER_TIKET, TOKEN
from .google_sheet import baca_data, bangun_peta_booking
from .menu import kirim_main_menu
from .memory import update_snapshot
from .storage import load_chat_ids, load_sent_tickets, save_sent_tickets
from .ticket import bangun_snapshot_tiket, proses_kategori, proses_reminder


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
    update_snapshot(bangun_snapshot_tiket(data))

    print(f"\n[{datetime.now():%d-%m-%Y %H:%M:%S}] Mengecek tiket baru...")
    total_baru = 0
    for nama_kategori, config in SUMBER_TIKET.items():
        try:
            total_baru += proses_kategori(nama_kategori, config,
                                          data[nama_kategori], sent_tickets, peta_booking)
        except Exception as e:
            print(f"[{nama_kategori}] Error: {e}")

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


def daftar_perintah():
    return [
        {"command": "start", "description": "Tampilkan menu utama bot"},
        {"command": "mainmenu", "description": "Tampilkan menu utama bot"},
        {"command": "listTicket", "description": "Tampilkan tiket per jenis & wilayah"},
        {"command": "aktivasiBot", "description": "Nyalakan/matikan bot di grup ini"},
        {"command": "pilihTicketWilayah", "description": "Pilih wilayah bot (filter alert & reminder)"},
        {"command": "filterOff", "description": "Matikan filter wilayah (mode Northren)"},
        {"command": "filterTicket", "description": "Filter tiket per jenis (detail)"},
        {"command": "id", "description": "Tampilkan ID chat grup ini"},
        {"command": "tes", "description": "Lihat daftar semua menu & cara pakai"},
    ]


def pin_menu_utama():
    for cid in load_chat_ids():
        try:
            kirim_main_menu(cid, pin=True)
        except Exception as e:
            print(f"[MAINMENU] Gagal pin ke {cid}: {e}")


def main():
    print(f"Bot berjalan. Tiket baru tiap {INTERVAL_MENIT} menit, "
          f"reminder tiap {REMINDER_JAM} jam. (Ctrl+C untuk stop)")

    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/setMyCommands",
                      json={"commands": daftar_perintah()}, timeout=10)
    except Exception:
        pass

    pin_menu_utama()

    threading.Thread(target=handlers.telegram_polling, daemon=True).start()

    reminder_berikutnya = time.time() + REMINDER_JAM * 3600

    while True:
        waktunya_reminder = time.time() >= reminder_berikutnya
        jalankan_siklus(waktunya_reminder)
        if waktunya_reminder:
            reminder_berikutnya = time.time() + REMINDER_JAM * 3600
        time.sleep(INTERVAL_MENIT * 60)