"""Klien low-level Telegram API: kirim/edit/pin pesan, kirim alert ke grup."""

import time

import requests

from .config import STO_KE_WILAYAH, TOKEN
from .storage import get_wilayah, is_bot_aktif, is_filter_aktif, is_filter_tiket_aktif, load_chat_ids


def _post(endpoint, **kwargs):
    url = f"https://api.telegram.org/bot{TOKEN}/{endpoint}"
    return requests.post(url, json=kwargs).json()


def kirim_telegram(pesan, sto=None):
    """Kirim pesan ke semua grup terdaftar sesuai status bot & filter wilayah."""
    ticket_wilayah = STO_KE_WILAYAH.get((sto or "").upper()) if sto else None

    chat_ids = []
    for cid in load_chat_ids():
        if not is_bot_aktif(cid):
            continue
        if is_filter_tiket_aktif(cid):
            continue
        gw = get_wilayah(cid)
        if not is_filter_aktif(cid) or gw is None \
                or ticket_wilayah is None or gw == ticket_wilayah:
            chat_ids.append(cid)

    if not chat_ids:
        return {"ok": False, "description": "tidak ada grup tujuan"}

    hasil_semua = []
    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "HTML"}
        hasil = _post("sendMessage", **payload)
        retry_after = hasil.get("parameters", {}).get("retry_after")
        if not hasil.get("ok") and retry_after:
            print(f"   Batas laju Telegram, tunggu {retry_after} detik...")
            time.sleep(retry_after)
            hasil = _post("sendMessage", **payload)
        hasil_semua.append(hasil)
        time.sleep(1)
    return hasil_semua[0] if hasil_semua else {"ok": False}


def kirim_panjang(chat_id, teks):
    """Kirim teks panjang dengan pecah per pesan (batas Telegram 4096 karakter)."""
    batas = 3800
    while len(teks) > batas:
        potong = teks.rfind("\n", 0, batas)
        if potong == -1:
            potong = batas
        _post("sendMessage", chat_id=chat_id, text=teks[:potong])
        time.sleep(1)
        teks = teks[potong:].lstrip("\n")
    if teks:
        _post("sendMessage", chat_id=chat_id, text=teks)


def kirim_pesan(chat_id, teks, **kwargs):
    return _post("sendMessage", chat_id=chat_id, text=teks, **kwargs)


def edit_pesan(chat_id, message_id, teks, **kwargs):
    return _post("editMessageText", chat_id=chat_id, message_id=message_id,
                 text=teks, **kwargs)


def pin_pesan(chat_id, message_id):
    return _post("pinChatMessage", chat_id=chat_id, message_id=message_id,
                 disable_notification=True)


def jawab_callback(callback_query_id):
    return _post("answerCallbackQuery", callback_query_id=callback_query_id)