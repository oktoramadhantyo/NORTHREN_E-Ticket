"""Antarmuka pengguna: keyboard, menu utama, daftar tiket, filter."""

import json
import time

from .config import HVC_JENIS, NAMA_WILAYAH, WILAYAH_STO
from .formatter import blok_isi, esc
from .memory import SIMPANAN_TIKET
from .storage import get_pinned, get_wilayah, is_bot_aktif, is_filter_aktif, set_pinned
from .telegram import edit_pesan, kirim_panjang, kirim_pesan, pin_pesan


def keyboard_wilayah():
    return json.dumps({"inline_keyboard": [
        [{"text": "🌆 Jakarta Utara", "callback_data": "wilayah:JAKUT"},
         {"text": "🌆 Jakarta Barat", "callback_data": "wilayah:JAKBAR"}],
        [{"text": "🌐 Semua (Northren)", "callback_data": "wilayah:SEMUA"}],
        [{"text": "⬅️ Menu Utama", "callback_data": "main:home"}],
    ]})


def keyboard_aktivasi(chat_id):
    aktif = is_bot_aktif(chat_id)
    if aktif:
        teks = "🟢 Bot AKTIF — alert & reminder jalan"
        tombol = [{"text": "🔴 Matikan Bot", "callback_data": "bot:toggle"}]
    else:
        teks = "🔴 Bot NONAKTIF — alert & reminder di-pause"
        tombol = [{"text": "🟢 Nyalakan Bot", "callback_data": "bot:toggle"}]
    return teks, json.dumps({"inline_keyboard": [tombol]})


def keyboard_main_menu(chat_id):
    aktif = is_bot_aktif(chat_id)
    status = "🟢 AKTIF" if aktif else "🔴 NONAKTIF"
    w = get_wilayah(chat_id)
    wilayah_txt = NAMA_WILAYAH.get(w, "- (belum dipilih)") if w else "- (belum dipilih)"
    if is_filter_aktif(chat_id):
        filter_txt = f"ON ({wilayah_txt})"
    else:
        filter_txt = "OFF (Northren)"
    teks = (
        "Selamat datang di bot <b>Monitoring TTR Northren</b>\n\n"
        f"Status Bot : {status}\n"
        f"Wilayah    : {wilayah_txt}\n"
        f"Filter     : {filter_txt}\n\n"
        "Berikut adalah menu yang tersedia:\n\n"
        "📋 <b>Lihat Tiket</b> — Lihat daftar tiket open per wilayah & jenis\n"
        "🔍 <b>Filter Tiket</b> — Filter & lihat detail tiket per jenis\n"
        "🌍 <b>Pilih Wilayah</b> — Set wilayah grup (filter alert & reminder)\n"
        "⚙️ <b>ON/OFF</b> — Nyalakan atau matikan bot di grup ini\n\n"
        "Pilih menu:"
    )
    markup = json.dumps({"inline_keyboard": [
        [{"text": "📋 Lihat Tiket", "callback_data": "main:menu"},
         {"text": "🔍 Filter Tiket", "callback_data": "main:filter"}],
        [{"text": "🌍 Pilih Wilayah", "callback_data": "main:pilwil"},
         {"text": "⚙️ ON/OFF", "callback_data": "main:toggle"}],
    ]})
    return teks, markup


def kirim_main_menu(chat_id, pin=False):
    teks, markup = keyboard_main_menu(chat_id)
    r = kirim_pesan(chat_id, teks, reply_markup=markup, parse_mode="HTML")
    if pin and r.get("ok"):
        mid = r.get("result", {}).get("message_id")
        if mid:
            set_pinned(chat_id, mid)
            pin_pesan(chat_id, mid)
    return r


def edit_atau_kirim_main_menu(chat_id):
    """Update pesan main menu yang di-pin kalau ada, kalau gagal kirim baru."""
    teks, markup = keyboard_main_menu(chat_id)
    msg_id = get_pinned(chat_id)
    if msg_id:
        r = edit_pesan(chat_id, msg_id, teks, reply_markup=markup, parse_mode="HTML")
        if r.get("ok"):
            return r
    return kirim_main_menu(chat_id, pin=False)


def keyboard_pilih_wilayah():
    return json.dumps({"inline_keyboard": [
        [{"text": "🌆 Jakarta Utara", "callback_data": "pilwil:JAKUT"},
         {"text": "🌆 Jakarta Barat", "callback_data": "pilwil:JAKBAR"}],
        [{"text": "⬅️ Menu Utama", "callback_data": "main:home"}],
    ]})


def keyboard_jenis(wilayah):
    return json.dumps({"inline_keyboard": [
        [{"text": "HVC Diamond", "callback_data": f"tiket:HVC_DIAMOND:{wilayah}"},
         {"text": "HVC Platinum", "callback_data": f"tiket:HVC_PLATINUM:{wilayah}"}],
        [{"text": "HVC_GOLD", "callback_data": f"tiket:HVC_GOLD:{wilayah}"}],
        [{"text": "REGULER", "callback_data": "tiket:REGULER:" + wilayah},
         {"text": "MANJA", "callback_data": "tiket:MANJA:" + wilayah}],
        [{"text": "FFG", "callback_data": "tiket:FFG:" + wilayah}],
        [{"text": "⬅️ Ganti wilayah", "callback_data": "menu:awal"}],
        [{"text": "⬅️ Menu Utama", "callback_data": "main:home"}],
    ]})


def keyboard_filter():
    return json.dumps({"inline_keyboard": [
        [{"text": "HVC Diamond", "callback_data": "filter:HVC_DIAMOND"},
         {"text": "HVC Platinum", "callback_data": "filter:HVC_PLATINUM"}],
        [{"text": "HVC_GOLD", "callback_data": "filter:HVC_GOLD"}],
        [{"text": "REGULER", "callback_data": "filter:REGULER"},
         {"text": "MANJA", "callback_data": "filter:MANJA"}],
        [{"text": "FFG", "callback_data": "filter:FFG"}],
        [{"text": "⬅️ Menu Utama", "callback_data": "main:home"}],
    ]})


def kirim_filter_tiket(chat_id, kategori):
    """Kirim semua tiket open per jenis sebagai pesan terpisah (bisa dicopy)."""
    if kategori in HVC_JENIS:
        tiket = SIMPANAN_TIKET.get("HVC", [])
        tiket = [t for t in tiket if t.get("cust_type", "").upper().replace(" ", "_") == kategori]
    else:
        tiket = SIMPANAN_TIKET.get(kategori, [])

    wilayah = get_wilayah(chat_id)
    wilayah_dipakai = wilayah if wilayah in WILAYAH_STO else None
    if wilayah_dipakai:
        daftar_sto = WILAYAH_STO[wilayah_dipakai]
        tiket = [t for t in tiket if t.get("sto", "").upper() in daftar_sto]

    nama_tampil = HVC_JENIS.get(kategori, kategori)
    nama_wilayah = NAMA_WILAYAH.get(wilayah_dipakai, "") if wilayah_dipakai else ""
    label = f" — wilayah {nama_wilayah}" if nama_wilayah else ""

    if not tiket:
        kirim_pesan(chat_id,
                    f"✅ Tidak ada tiket {nama_tampil}{label} yang open saat ini.")
        return

    for t in tiket:
        booking = "" if kategori == "MANJA" else t.get("booking_date", "")
        isi = blok_isi(kategori=kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                       no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                       tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                       booking_date=booking)
        pesan = f"Filtering Ticket {esc(nama_tampil)}{label}\n\n{isi}"
        kirim_pesan(chat_id, pesan, parse_mode="HTML")
        time.sleep(1)


def kirim_menu(chat_id):
    kirim_pesan(chat_id, "📍 Pilih wilayah:", reply_markup=keyboard_wilayah())


def daftar_tiket(kategori, wilayah=""):
    """Teks daftar tiket open sesuai jenis (+wilayah), dari siklus terakhir."""
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