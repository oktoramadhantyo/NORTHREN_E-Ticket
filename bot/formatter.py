"""Format pesan Telegram (escape HTML, blok isi tiket, pesan alert/reminder)."""


def esc(teks):
    return str(teks).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal,
             durasi, pic_list, booking_date=""):
    label_tanggal = "BOOKING DATE" if kategori == "MANJA" else "REPORT DATE"
    label_jenis = "FLAGGING" if kategori == "FFG" else "CUSTOMER TYPE"

    baris = [
        f"INCIDENT      : {esc(no_tiket)}",
        f"STO           : {esc(sto)}",
        f"NO GANGGUAN   : {esc(no_gangguan) if no_gangguan else '-'}",
        f"{label_jenis:<14}: {esc(cust_type)}",
        f"{label_tanggal:<14}: {esc(tanggal)}",
    ]
    if booking_date:
        baris.append(f"{'BOOKING DATE':<14}: {esc(booking_date)}")
    baris.append(f"TTR           : {esc(durasi)}")

    return "<pre>\n" + "\n".join(baris) + f"\n</pre>\nPIC: {esc(pic_list)}"


def format_pesan(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal,
                 durasi, pic_list, booking_date=""):
    judul = f"Tiket Open {cust_type} Northren" if kategori != "MANJA" else "Tiket Open Manja Northren"
    isi = blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal,
                   durasi, pic_list, booking_date)
    return f"🚨 {esc(judul)}\n\n{isi}"


def format_pesan_reminder(kategori, sto, no_tiket, no_gangguan, cust_type,
                          tanggal, durasi, pic_list, booking_date, batas_jam):
    judul = "⏰ Reminder Ticket Manja Northren" if kategori == "MANJA" \
        else f"⏰ Reminder Ticket {cust_type} Northren"
    isi = blok_isi(kategori, sto, no_tiket, no_gangguan, cust_type, tanggal,
                   durasi, pic_list, booking_date)
    catatan = (f"\n\nnotes: Durasi ticket sudah lebih dari {batas_jam} jam. "
               f"mohon segera dikerjakan dan diprioritaskan sampai tuntas")
    return f"{esc(judul)}\n\n{isi}{catatan}"