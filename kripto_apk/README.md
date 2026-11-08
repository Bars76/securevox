# SecureVox

**Aplikasi Pesan Aman Multimedia Berbasis USB Dongle, Biometrik Wajah, Super Enkripsi, Steganografi, dan Blockchain Sederhana**

Aplikasi desktop murni Python + PySide6 (Windows 10/11, tidak ada server, tidak ada browser, tidak perlu internet).

---

## 1. Cara Instalasi

```bash
# 1. Buat virtual environment (disarankan)
python -m venv .venv
.venv\Scripts\activate

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Jalankan aplikasi
python main.py
```

Dependensi utama: `PySide6`, `wmi`, `opencv-contrib-python`, `pycryptodome`, `sounddevice`, `Pillow`, `numpy`.

---

## 2. Alur Awal Aplikasi

```
Buka Aplikasi
   → Cek Dongle USB (tidak ada dongle = tidak bisa lanjut)
   → Verifikasi Wajah (maks. 3 percobaan)
   → Login Username + Password
   → Dashboard (Pesan Teks, Pesan PDF, Pesan Gambar, Aset, Log)
```

Jika USB dicabut saat aplikasi berjalan, aplikasi langsung mengunci dan kembali ke layar dongle.

---

## 3. Pengaturan Dongle USB (PENTING)

SecureVox hanya bisa dijalankan jika USB dongle dengan **file kunci `securevox.key`** terpasang.

### Jika ingin menggunakan flashdisk berbeda:

Setiap flashdisk USB memiliki kode unik bernama **VID** dan **PID**. SecureVox mencari flashdisk dengan VID/PID yang cocok dengan `config.json`.

**Langkah-langkah untuk flashdisk baru:**

1. Colokkan flashdisk USB yang ingin dijadikan dongle.
2. Jalankan perintah ini untuk melihat VID/PID flashdisk Anda:

   ```bash
   python -c "import modules.dongle as d; print(d.cek_info_dongle())"
   ```

   Contoh output:
   ```
   {'found': False, 'vid': '058F', 'pid': '6387', 'devices': []}
   ```

   Jika `found` berarti `False`, coba lihat semua USB yang terdeteksi:
   ```bash
   python -c "import wmi; c=wmi.WMI(); [print(e.PNPDeviceID) for e in c.Win32_PnPEntity() if e.PNPDeviceID and 'USB' in e.PNPDeviceID.upper()]"
   ```

3. Buka file `config.json`, ubah `vid` dan `pid` agar cocok dengan flashdisk Anda:

   ```json
   {
     "dongle": {
       "vid": "VID_ANDA",
       "pid": "PID_ANDA",
       "key_filename": "securevox.key"
     }
   }
   ```

4. Daftarkan kunci ke flashdisk:

   ```bash
   python -c "import modules.dongle as d; d.registrasi_dongle()"
   ```

   Ini akan membuat file `securevox.key` (32 byte acak) di flashdisk Anda.

5. Jalankan aplikasi: `python main.py`, lalu klik **Deteksi Dongle**.

> Catatan: Jika Anda ganti flashdisk, ulangi langkah 1–4 untuk flashdisk baru. Setiap flashdisk harus memiliki file `securevox.key` sendiri.

---

## 4. Fitur Utama

| Fitur | Metode |
|-------|--------|
| Akses aplikasi | USB dongle + file `securevox.key` |
| Verifikasi wajah | LBPH (OpenCV), maks. 3 percobaan |
| Login | Username + password (hash SHA-256 + salt) |
| Master Key | PBKDF2(password + securevox.key, 200.000 iterasi), hanya di memori |
| Pesan teks | Vigenère (klasik) → AES-256 (modern), 2 lapis |
| Pesan file (PDF) | ChaCha20 (berbeda dari teks) |
| Basis data | SQLite, field sensitif AES-256-GCM |
| Pesan gambar | LSB steganografi pada PNG |
| Aset penting | Blockchain sederhana dengan Proof of Work |
| Log aktivitas | Semua aktivitas dicatat dengan waktu |

---

## 5. Skenario Demo (untuk dosen)

1. Cabut USB → aplikasi langsung terkunci.
2. Pasang dongle → verifikasi wajah (wajah tidak terdaftar ditolak; 3x gagal kembali ke awal).
3. Login password salah → ditolak; password disimpan sebagai hash + salt.
4. Pesan teks → 2 lapis enkripsi (Vigenère → AES-256), tampilkan setiap tahap, lalu dekripsi.
5. Pesan PDF → enkripsi ChaCha20, simpan `.enc`, dekripsi kembali ke PDF.
6. Lihat Isi DB Mentah → tabel database menunjukkan ciphertext (tidak terbaca tanpa Master Key).
7. Pesan gambar → pilih cover PNG, sisipkan pesan, lihat asli vs stego + PSNR, ekstrak pesan.
8. Aset → tambah file ke blockchain, validasi chain, simulasi manipulasi → validasi menampilkan blok yang rusak.
9. Log → lihat semua aktivitas dengan waktu dan status.

---

## 6. Unit Test

```bash
python -m unittest discover -s tests -v
```

Semua tes di `tests/` harus lulus.

---

## 7. Pengemasan ke `.exe` (Opsional)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile main.py
```

Hasil `.exe` berada di folder `dist/`.

---

## 8. Struktur Proyek

```
SecureVox/
├── main.py                  # titik masuk
├── config.json              # konfigurasi dongle (VID/PID) dan aplikasi
├── requirements.txt         # dependensi Python
├── README.md
├── modules/                 # logika murni (tanpa PySide6)
│   ├── dongle.py            # deteksi USB dongle + securevox.key
│   ├── face_auth.py         # LBPH verifikasi wajah
│   ├── login.py             # registrasi, hash+salt, login, Master Key
│   ├── crypto_text.py       # Vigenère + AES-256
│   ├── crypto_file.py       # ChaCha20 untuk file PDF
│   ├── database.py          # SQLite, AES-GCM, file_messages
│   ├── stego.py             # LSB PNG steganografi
│   └── blockchain.py        # rantai blok, PoW, validasi
├── ui/                      # tampilan PySide6
│   ├── main_window.py       # QStackedWidget, DongleWorker
│   ├── session.py           # Master Key hanya di memori
│   ├── theme.qss            # tema gelap
│   ├── screens/             # dongle, wajah, login, dashboard
│   ├── tabs/                # teks, pdf, gambar, aset, log
│   └── widgets/             # kamera QThread
├── tests/                   # unit test
└── data/                    # faces, files, stego, securevox.db, chain.json
```

---

## 9. Catatan Penting

- **Tidak ada kunci/password hardcode** di kode.
- **IV/nonce acak** setiap enkripsi, tidak dipakai ulang.
- **Master Key hanya di memori**, dihapus saat logout atau dongle dicabut.
- **Flashdisk berbeda** memerlukan registrasi ulang (lihat Bagian 3).
- Aplikasi **tidak perlu internet**, semua proses lokal.
