"""Logika tiket: ekstraksi baris sheet, hitung durasi, kirim alert & reminder."""

from datetime import datetime

from .config import SUMBER_TIKET
from .formatter import format_pesan, format_pesan_reminder
from .telegram import kirim_telegram


def ekstrak_tiket(nama_kategori, row):
    """Ambil field tiket dari satu baris sheet sesuai kategorinya."""
    def ambil(i):
        return str(row[i]).strip() if len(row) > i and row[i] else ""

    if nama_kategori == "MANJA":
        return {"no_tiket": ambil(0), "sto": ambil(1), "cust_type": ambil(2),
                "tanggal": ambil(3), "durasi": ambil(4), "pic": ambil(5),
                "no_gangguan": ""}
    if nama_kategori == "FFG":
        return {"sto": ambil(0), "no_tiket": ambil(1), "no_gangguan": ambil(2),
                "cust_type": ambil(3) or "FFG", "tanggal": ambil(4),
                "durasi": ambil(6), "pic": ambil(7)}
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
    return config["batas_jam"].get(cust_type, max(config["batas_jam"].values()))


def sudah_terkirim(no_tiket, nama_kategori, sent_tickets):
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

        if not t["no_tiket"].startswith("INC"):
            continue

        if sudah_terkirim(t["no_tiket"], nama_kategori, sent_tickets):
            continue

        booking = "" if nama_kategori == "MANJA" else peta_booking.get(t["no_tiket"], "")

        pesan = format_pesan(kategori=nama_kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                             no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                             tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                             booking_date=booking)
        hasil = kirim_telegram(pesan, sto=t["sto"])

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
            continue

        pesan = format_pesan_reminder(kategori=nama_kategori, sto=t["sto"], no_tiket=t["no_tiket"],
                                      no_gangguan=t["no_gangguan"], cust_type=t["cust_type"],
                                      tanggal=t["tanggal"], durasi=t["durasi"], pic_list=t["pic"],
                                      booking_date=booking, batas_jam=batas)
        hasil = kirim_telegram(pesan, sto=t["sto"])

        if hasil.get("ok"):
            jumlah += 1
            print(f"[{nama_kategori}] Reminder ({jam_lewat:.0f} jam): {t['no_tiket']}")
        else:
            print(f"[{nama_kategori}] Gagal reminder {t['no_tiket']}: {hasil}")

    return jumlah


def bangun_snapshot_tiket(data):
    """Teks hasil parsing semua tabel -> dict utk fitur /menu."""
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
    return snapshot