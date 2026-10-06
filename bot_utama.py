"""Entry point bot Northren E-Ticket (Monitoring TTR).

Sebelum menjalankan loop, konfigurasi dan daftar grup tujuan dicek dulu.
Kalau ada yang belum siap, bot berhenti dengan pesan jelas - bukan online
diam-diam tanpa mengirim apa pun, dan bukan crash dengan tracebar.

Dipakai di server (Render/Railway) dan bisa juga dijalankan manual di
lokal:  python bot_utama.py
"""

import sys


def main():
    print("")
    print("=" * 62)
    print(" NORTHREN E-TICKET  -  Monitoring TTR")
    print("=" * 62)

    # Import dilakukan di dalam main() supaya file yang hilang atau salah
    # nama muncul sebagai pesan di bawah, bukan tracebar yang membingungkan.
    try:
        from bot.config import diagnosis
        from bot.scheduler import main as jalankan_bot
        from bot.storage import load_chat_ids
    except ModuleNotFoundError as exc:
        print("")
        print(f"  [GAGAL] File bot tidak lengkap: {exc.name} tidak ditemukan.")
        print("          Pastikan folder bot\\ ikut tersalin, lalu jalankan lagi.")
        return 1

    masalah = diagnosis()
    if masalah:
        print("")
        print("  [BELUM SIAP] Konfigurasi belum lengkap:")
        print("")
        for judul, saran in masalah:
            print(f"    X {judul}")
            print(f"      -> {saran}")
        print("")
        print("  Isi dulu, lalu jalankan lagi.")
        return 1
    print("  [OK] Konfigurasi dasar lengkap")

    grup = load_chat_ids()
    if not grup:
        print("")
        print("  [BELUM SIAP] Tidak ada chat tujuan alert yang terdaftar.")
        print("")
        print("    Bot butuh minimal satu grup/channel tujuan supaya tahu")
        print("    mau mengirim ke mana. Tanpa itu bot akan online tapi diam.")
        print("")
        print("    Cara mengisinya, pilih salah satu:")
        print("      1) Tambahkan bot ke grup, lalu di dalam grup ketik /id.")
        print("         Sekali saja, chat itu langsung terdaftar.")
        print("      2) Isi CHAT_IDS di file .env, pisahkan dengan koma.")
        print("      3) Jalankan:  python kelola_grup.py tambah <id grup>")
        return 1
    print(f"  [OK] {len(grup)} chat terdaftar sebagai tujuan alert")

    print("")
    print("Bot berjalan. Tiket dicek berkala, tekan Ctrl+C untuk berhenti.")
    print("")

    try:
        jalankan_bot()
    except KeyboardInterrupt:
        print("")
        print("Bot dihentikan oleh pengguna (Ctrl+C).")
    return 0


if __name__ == "__main__":
    sys.exit(main())