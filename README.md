# Bot Utama — Monitoring Tiket Telegram

Bot Python yang memantau tiket gangguan dari Google Spreadsheet secara otomatis dan mengirimkan notifikasi/alert ke grup Telegram.

---

## Ringkasan

Bot ini membaca data tiket dari Google Sheets, lalu mengirim notifikasi ke Telegram untuk:
1. **Tiket baru** — dikirim sekali saat pertama terdeteksi.
2. **Reminder** — dikirim ulang secara berkala untuk tiket yang masih open dan sudah melewati batas waktu.
3. **Menu interaktif** — pengguna bisa melihat daftar tiket per wilayah/jenis via perintah `/menu`.

---

## Dependensi

| Library | Fungsi |
|---|---|
| `gspread` | Membaca Google Spreadsheet |
| `google-oauth2` | Autentikasi ke Google API |
| `requests` | Mengirim pesan ke Telegram API |

Install:
```bash
pip install gspread google-auth requests
```

---

## File yang Dibutuhkan

| File | Keterangan |
|---|---|
| `bot_utama.py` | Script utama bot |
| `modern-triumph-506502-u0-2b11a7b4943a.json` | Kredensial Google Service Account |
| `sent_tickets.json` | Catatan tiket yang sudah dikirim (auto-generated) |

---

## Konfigurasi Utama

| Variabel | Nilai | Keterangan |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | dari @BotFather | Token Bot Telegram (dari file `.env`) |
| `CHAT_ID` | `-5587626942` | ID grup Telegram |
| `SHEET_ID` | `1dXZpM8a...` | ID Google Spreadsheet |
| `INTERVAL_MENIT` | `5` | Interval pengecekan tiket baru (menit) |
| `REMINDER_JAM` | `1` | Interval pengiriman reminder (jam) |

---

## Kategori Tiket & Batas Waktu (SLA)

| Kategori | Tab Sheet | Rentang | Batas Jam |
|---|---|---|---|
| HVC Diamond | MONITORING TTR | `P35:V200` | 3 jam |
| HVC Platinum | MONITORING TTR | `P35:V200` | 6 jam |
| HVC Gold | MONITORING TTR | `X35:AD200` | 12 jam |
| Reguler | MONITORING TTR | `AF35:AL200` | 24 jam |
| Manja | MONITORING TTR | `AN35:AS200` | 3 jam |
| FFG | FFG | `H5:O200` | 3 jam |

---

## Struktur Kolom per Kategori

### HVC / HVC_GOLD / REGULER
`STO | NO TIKET | NO GANGGUAN | CUSTOMER TYPE | REPORT DATE | DURASI TTR | PIC`

### MANJA
`NO TIKET | STO | CUSTOMER TYPE | BOOKING DATE | DURASI MANJA | PIC`

### FFG
`STO | NO TIKET | INET GANGGUAN | FLAGGING | REPORTED DATE | TANGGAL MANJA | DURASI TTR | PIC`

---

## Wilayah STO

| Wilayah | STO |
|---|---|
| Jakarta Utara (JAKUT) | CIL, MRD, KLG, KTX, KTZ, MKR, PDM, STR, TPR |
| Jakarta Barat (JAKBAR) | CKG, TGA, KPK, JIA, KSB, PLM, KDY, MRY, SLP, SMI, DTG, SDM |

---

## Cara Menjalankan

```bash
cd "C:\Users\diana\Downloads\MAGANGG\projek magang"
python bot_utama.py
```

Tekan `Ctrl+C` untuk menghentikan bot.

---

## Alur Kerja Bot

```
main()
 ├── Register /menu command ke Telegram
 ├── Jalankan thread telegram_polling() (long polling)
 └── Loop utama:
      ├── baca_data()           → baca semua sheet sekaligus (batch_get)
      ├── bangun_peta_booking() → mapping tiket MANJA ke booking date
      ├── simpan_snapshot_tiket() → simpan untuk fitur /menu
      ├── proses_kategori()     → kirim alert tiket BARU (sekali kirim)
      ├── proses_reminder()     → kirim reminder tiket OVERDUE (berulang)
      └── sleep(INTERVAL_MENIT × 60)
```

---

## Fitur `/menu`

Pengguna di Telegram dapat mengetik `/menu` untuk membuka menu interaktif:

1. **Pilih Wilayah** → Jakarta Utara / Jakarta Barat / Semua
2. **Pilih Jenis Tiket** → HVC / HVC_GOLD / REGULER / MANJA / FFG
3. **Hasil** → Daftar tiket open sesuai filter, dengan jumlah tiket dan info TTR

---

## Mekanisme Penyimpanan

- **`sent_tickets.json`** — Menyimpan tiket yang sudah dikirim alert-nya agar tidak dikirim ulang. Format: `["KATEGORI:INCxxxxx", ...]`
- Hanya ditulis ulang jika ada tiket baru terkirim (hemat I/O).
