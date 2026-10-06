"""Kelola daftar grup/user tujuan alert dari terminal.

Berguna saat bot sedang mati, jadi tidak bisa mendaftarkan grup baru lewat
/id dari dalam Telegram. Kalau bot lagi jalan, /id di dalam grup jauh lebih
cepat - cukup sekali, grup langsung terdaftar.

Contoh:
    python kelola_grup.py daftar
    python kelola_grup.py tambah -1001234567890,-1009876543210
    python kelola_grup.py hapus -1001234567890

Semua perintah menulis ke chat_ids.json. File .env tidak pernah disentuh,
jadi token bot, SHEET_ID, dan jadwal tidak akan tertimpa.
"""

import sys

import requests

try:
    from bot.config import CHAT_IDS_FILE, TOKEN
    from bot.storage import (
        get_wilayah,
        hapus_chat_id,
        is_bot_aktif,
        is_filter_aktif,
        is_filter_tiket_aktif,
        load_chat_ids,
        tambah_chat_id,
    )
except ModuleNotFoundError as exc:
    print("")
    print(f"  [GAGAL] Dependency Python belum lengkap: {exc.name}")
    print("          Jalankan:  pip install -r requirements.txt")
    sys.exit(1)

API = f"https://api.telegram.org/bot{TOKEN}"


def garis(teks=""):
    print("")
    print("-" * 62)
    if teks:
        print(f" {teks}")
        print("-" * 62)


def cek_chat(chat_id):
    """Tanya ke Telegram soal chat ini. Balik (status, nama) atau None."""
    try:
        r = requests.get(f"{API}/getChat",
                         params={"chat_id": chat_id}, timeout=20).json()
    except requests.RequestException as exc:
        print(f"  [GAGAL] {chat_id}: tidak bisa menghubungi Telegram ({exc})")
        return None

    if not r.get("ok"):
        print(f"  [GAGAL] {chat_id}: {r.get('description')}")
        print("          Pastikan bot sudah ada di chat itu, dan ID-nya benar.")
        return None

    d = r["result"]
    nama = d.get("title") or d.get("first_name") or d.get("username") or "?"
    return d.get("type", "?"), nama


def perintah_daftar():
    garis("DAFTAR CHAT TUJUAN ALERT")
    grup = load_chat_ids()
    if not grup:
        print("")
        print("  Belum ada chat yang terdaftar.")
        print("")
        print("  Tambahkan dengan:")
        print("    python kelola_grup.py tambah <id grup>")
        print("  atau kirim /id di dalam grup saat bot sedang jalan.")
        return 0

    print("")
    print(f"  Total {len(grup)} chat. Sumber: {CHAT_IDS_FILE} + env CHAT_IDS")
    print("")
    for cid in grup:
        hasil = cek_chat(cid)
        if hasil is None:
            jenis, nama = "?", "(tidak bisa diakses)"
        else:
            jenis, nama = hasil
        print(f"  {cid}")
        print(f"      {nama}  [{jenis}]")
        status = []
        status.append("bot AKTIF" if is_bot_aktif(cid) else "bot NONAKTIF")
        status.append("filter tiket ON" if is_filter_tiket_aktif(cid) else "filter tiket OFF")
        if is_filter_aktif(cid):
            status.append(f"filter wilayah ON ({get_wilayah(cid) or 'belum dipilih'})")
        else:
            status.append("filter wilayah OFF")
        print(f"      {', '.join(status)}")
    return 0


def perintah_tambah(daftar_id):
    garis("MENAMBAHKAN CHAT TUJUAN")
    print("")
    print("  Memeriksa ke Telegram dulu, baru disimpan.")
    print("")

    gagal = []
    for cid in daftar_id:
        hasil = cek_chat(cid)
        if hasil is None:
            gagal.append(cid)
            continue
        jenis, nama = hasil
        if tambah_chat_id(cid):
            print(f"  [OK] {cid} -> {nama}  [{jenis}]")
        else:
            print(f"  [OK] {cid} -> {nama}  [{jenis}] (sudah terdaftar)")

    if gagal:
        print("")
        print(f"  {len(gagal)} ID gagal diperiksa dan tidak disimpan: "
              f"{', '.join(gagal)}")
        return 1
    print("")
    print("  Selesai. Semua ID valid sudah tersimpan di chat_ids.json.")
    return 0


def perintah_hapus(daftar_id):
    garis("MENGHAPUS CHAT TUJUAN")
    grup = load_chat_ids()
    baru = [cid for cid in daftar_id if cid in grup]
    tidak_ada = [cid for cid in daftar_id if cid not in grup]

    if tidak_ada:
        print("")
        for cid in tidak_ada:
            print(f"  Lewat - ID ini tidak ada di daftar: {cid}")
    if not baru:
        print("")
        print("  Tidak ada yang dihapus.")
        return 0

    print("")
    print("  Bot akan berhenti mengirim ke:")
    for cid in baru:
        print(f"    - {cid}")
    print("")
    jawaban = input("  Yakin mau dihapus? (Y/N): ").strip().lower()
    if jawaban not in ("y", "ya", "yes"):
        print("  Dibatalkan. Tidak ada yang berubah.")
        return 0

    print("")
    for cid in baru:
        if hapus_chat_id(cid):
            print(f"  [OK] Dihapus: {cid}")
        else:
            print(f"  [WARN] Gagal menghapus: {cid}")

    sisa = load_chat_ids()
    if not sisa:
        print("")
        print("  [PERINGATAN] Daftar sekarang kosong. Bot tidak akan")
        print("  mengirim apa pun sampai ada chat yang terdaftar lagi.")
    return 0


def main():
    if len(sys.argv) < 2:
        print("Penggunaan:")
        print("  python kelola_grup.py daftar")
        print("  python kelola_grup.py tambah <id>[,<id>,...]")
        print("  python kelola_grup.py hapus <id>[,<id>,...]")
        print("")
        print("Kalau bot sedang jalan, kirim /id di dalam grup lebih cepat.")
        return 1

    perintah = sys.argv[1].lower()
    sisa = [x.strip() for x in " ".join(sys.argv[2:]).split(",") if x.strip()]

    if perintah == "daftar":
        return perintah_daftar()

    if perintah in ("tambah", "hapus"):
        if not sisa:
            print(f"  [GAGAL] Perintah '{perintah}' butuh minimal satu ID grup.")
            print("          Contoh: python kelola_grup.py tambah -1001234567890")
            return 1
        if perintah == "tambah":
            return perintah_tambah(sisa)
        return perintah_hapus(sisa)

    print(f"  [GAGAL] Perintah tidak dikenal: {perintah}")
    print("          Pilihan: daftar, tambah, hapus")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("")
        print("Dibatalkan.")
        sys.exit(1)