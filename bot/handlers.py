"""Dispatcher pesan masuk dari Telegram (polling getUpdates)."""

import json
import time

import requests

from .config import NAMA_WILAYAH, TOKEN
from .menu import (
    daftar_tiket,
    edit_atau_kirim_main_menu,
    keyboard_aktivasi,
    keyboard_filter,
    keyboard_jenis,
    keyboard_pilih_wilayah,
    keyboard_wilayah,
    kirim_filter_tiket,
    kirim_main_menu,
    kirim_menu,
)
from .storage import (
    hapus_chat_id,
    is_bot_aktif,
    set_filter,
    set_wilayah,
    tambah_chat_id,
    toggle_bot,
)
from .telegram import jawab_callback, kirim_panjang, kirim_pesan


def tangani_update(update):
    """Pesan masuk dari user: perintah /menu atau tombol menu ditekan."""
    if "my_chat_member" in update:
        cm = update["my_chat_member"]
        chat = cm.get("chat", {})
        chat_id = str(chat.get("id", ""))
        status = cm.get("new_chat_member", {}).get("status", "")
        if status in ("member", "administrator"):
            if tambah_chat_id(chat_id):
                nama = chat.get("title", chat_id)
                print(f"[GRUP] Bot ditambahkan ke grup: {nama} ({chat_id})")
                kirim_main_menu(chat_id, pin=True)
        elif status in ("left", "kicked"):
            if hapus_chat_id(chat_id):
                print(f"[GRUP] Bot dihapus dari grup: {chat_id}")
        return

    if "callback_query" in update:
        cb = update["callback_query"]
        jawab_callback(cb["id"])
        data = cb.get("data", "")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")
        if not chat_id:
            return

        if data == "menu:awal":
            kirim_menu(chat_id)
        elif data == "main:home":
            edit_atau_kirim_main_menu(chat_id)
        elif data == "main:menu":
            kirim_pesan(chat_id, "📍 Pilih wilayah:", reply_markup=keyboard_wilayah())
        elif data == "main:filter":
            kirim_pesan(chat_id, "🔍 Pilih jenis tiket:", reply_markup=keyboard_filter())
        elif data == "main:pilwil":
            kirim_pesan(chat_id, "🌍 Pilih wilayah bot (filter alert & reminder):",
                        reply_markup=keyboard_pilih_wilayah())
        elif data == "main:toggle":
            toggle_bot(chat_id)
            edit_atau_kirim_main_menu(chat_id)
            if not is_bot_aktif(chat_id):
                kirim_pesan(chat_id,
                            "Terima kasih telah menggunakan bot ini.\n"
                            "Jika ingin mengaktifkan bot silahkan ketik /aktivasiBot\n\n"
                            "Bot created by: Okto Ramadhantyo (ig: _oktrmdnn)\n"
                            "Silahkan hubungi kontak diatas jika berkepentingan")
        elif data.startswith("pilwil:"):
            w = data.split(":", 1)[1]
            set_wilayah(chat_id, w)
            set_filter(chat_id, True)
            edit_atau_kirim_main_menu(chat_id)
            nama = NAMA_WILAYAH.get(w, w)
            kirim_pesan(chat_id,
                        f"✅ Filter wilayah AKTIF — set ke {nama}. "
                        f"Alert & reminder hanya tiket wilayah tersebut.")
        elif data == "bot:toggle":
            toggle_bot(chat_id)
            teks, markup = keyboard_aktivasi(chat_id)
            kirim_pesan(chat_id, teks, reply_markup=markup)
        elif data.startswith("wilayah:"):
            wilayah = data.split(":", 1)[1]
            nama = NAMA_WILAYAH.get(wilayah, wilayah)
            kirim_pesan(chat_id, f"Wilayah {nama} — pilih jenis tiket:",
                        reply_markup=keyboard_jenis(wilayah))
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
        if teks in ("/start", "/mainmenu"):
            kirim_main_menu(msg["chat"]["id"], pin=True)
        elif teks == "/menu":
            kirim_menu(msg["chat"]["id"])
        elif teks == "/aktivasibot":
            cid = msg["chat"]["id"]
            teks_status, markup = keyboard_aktivasi(cid)
            kirim_pesan(cid, teks_status, reply_markup=markup)
        elif teks == "/pilihticketwilayah":
            kirim_pesan(msg["chat"]["id"], "🌍 Pilih wilayah bot (filter alert & reminder):",
                        reply_markup=keyboard_pilih_wilayah())
        elif teks == "/filteroff":
            cid = msg["chat"]["id"]
            set_filter(cid, False)
            edit_atau_kirim_main_menu(cid)
            kirim_pesan(cid,
                        "✅ Mode normal telah kembali aktif — grup menerima notif & alert "
                        "wilayah Jakarta Utara dan Jakarta Barat (Northren).")
        elif teks == "/filterticket":
            kirim_pesan(msg["chat"]["id"], "🔍 Pilih jenis tiket:",
                        reply_markup=keyboard_filter())
        elif teks == "/id":
            kirim_pesan(msg["chat"]["id"],
                        f"🆔 ID chat grup ini:\n<code>{msg['chat']['id']}</code>",
                        parse_mode="HTML")
        elif teks == "/tes":
            teks_menu = (
                "📋 <b>DAFTAR MENU BOT</b>\n\n"
                "/start atau /mainmenu\n"
                "→ Tampilkan menu utama bot\n\n"
                "/menu\n"
                "→ Lihat daftar tiket open per wilayah & jenis\n\n"
                "/filterTicket\n"
                "→ Filter & lihat detail tiket per jenis (bisa dicopy)\n\n"
                "/pilihTicketWilayah\n"
                "→ Pilih wilayah bot untuk filter alert & reminder\n\n"
                "/aktivasiBot\n"
                "→ Nyalakan/matikan bot di grup ini\n\n"
                "/id\n"
                "→ Tampilkan ID chat grup ini\n\n"
                "💡 Ketik perintah di atas atau gunakan tombol di menu utama."
            )
            kirim_pesan(msg["chat"]["id"], teks_menu, parse_mode="HTML")


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