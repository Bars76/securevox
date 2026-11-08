# PRD: SecureVox

**Aplikasi Pesan Aman Multimedia Berbasis USB Dongle, Biometrik Wajah, Super Enkripsi, Steganografi, dan Blockchain Sederhana**

Dokumen ini ditulis sebagai instruksi lengkap untuk AI coding agent (OpenCode). Kerjakan bertahap sesuai urutan fase pada bagian 12, dan jangan lanjut ke fase berikutnya sebelum fase sebelumnya bisa dijalankan.

## 1. Ringkasan Produk

SecureVox adalah aplikasi desktop untuk bertukar dan menyimpan pesan rahasia (teks, audio, gambar) serta mengamankan aset penting. Aplikasi hanya dapat dijalankan jika USB dongle yang terdaftar terpasang, lalu pengguna harus lolos verifikasi wajah dan login password (hash). Setiap jenis data diamankan dengan metode kriptografi yang berbeda.

Aplikasi ini dibuat untuk tugas kuliah Kriptografi, sehingga **setiap algoritma harus diimplementasikan dan didemonstrasikan secara jelas** (tampilkan plaintext vs ciphertext, gambar asli vs stego, validasi blockchain).

## 2. Tujuan dan Kriteria Keberhasilan

| No | Kriteria tugas | Wujud di SecureVox |
| --- | --- | --- |
| 1 | Login biometrik, hanya hidup dengan dongle | Cek USB dongle, lalu verifikasi wajah |
| 2 | Login memakai algoritma kriptografi | Password di-hash SHA-256 + salt (atau PBKDF2) |
| 3 | Pesan teks memakai super enkripsi | Vigenère, Transposisi Kolom, lalu AES-256 |
| 4 | Pesan file memakai kriptografi berbeda dari teks | Pesan audio (WAV) dienkripsi ChaCha20 |
| 5 | Pesan penting dienkripsi di basis data | Field sensitif di SQLite dienkripsi AES-GCM |
| 6 | Pesan gambar memakai steganografi | LSB pada PNG, pesan dienkripsi sebelum disisipkan |
| 7 | Aset penting memakai blockchain sederhana | Rantai blok berisi hash aset + validasi chain |

## 3. Target Pengguna dan Skenario

- Pengguna tunggal atau beberapa akun lokal (admin dan user biasa) di satu perangkat Windows.
- Skenario demo dosen: cabut USB (aplikasi terkunci), wajah salah (ditolak), password salah (ditolak), kirim dan baca pesan teks, audio, gambar, tambah aset ke blockchain lalu manipulasi data dan buktikan terdeteksi.

## 4. Tech Stack (wajib diikuti)

| Kebutuhan | Pilihan |
| --- | --- |
| Bahasa | Python 3.10+ |
| Platform target | Windows 10/11 |
| Jenis aplikasi | Aplikasi desktop murni (satu proses, tanpa server, tanpa browser, tanpa internet) |
| GUI | `PySide6` (Qt6), di-styling dengan QSS bertema gelap |
| Cek dongle | `wmi` (Windows), baca `PNPDeviceID` (berisi VID dan PID) |
| Kamera | `opencv-python` (`VideoCapture`) di thread terpisah |
| Wajah | `opencv-contrib-python` (LBPH) atau `face_recognition` |
| Hash | `hashlib` (SHA-256 + salt acak), opsi PBKDF2 |
| AES-256, AES-GCM, ChaCha20 | `pycryptodome` |
| Kripto klasik | Implementasi sendiri (Vigenère, Transposisi Kolom) |
| Audio | `sounddevice` + `wave` (rekam dan putar WAV) |
| Steganografi | `Pillow` + `numpy` |
| Database | `sqlite3` |
| Blockchain | Implementasi sendiri (`hashlib`, `json`) |
| Pengemasan (opsional) | `PyInstaller` untuk membuat `.exe` |

Semua dependency dicatat di `requirements.txt`.

## 5. Alur Utama Aplikasi

```
Buka Aplikasi
   -> Cek Dongle USB (VID/PID + file kunci)   gagal: aplikasi tidak bisa lanjut
   -> Verifikasi Wajah (maks. 3 percobaan)             gagal: ditolak
   -> Login Username + Password (hash)                 gagal: ditolak
   -> Dashboard (Teks, Audio, Gambar, Aset, Log)
```

Selama aplikasi berjalan, `QTimer` mengecek dongle setiap 3 detik di thread terpisah. Jika USB dicabut, Master Key dihapus dari memori dan aplikasi langsung kembali ke layar kunci.

## 6. Kebutuhan Fungsional

### 6.1 Modul Dongle (`modules/dongle.py`)

- Identitas dongle: `VID_058F&PID_6387`, ditambah **file kunci securevox.key di dalam USB sebagai syarat wajib: dongle sah hanya jika VID/PID cocok dan file kunci terbac**a.
- Konfigurasi dongle (VID/PID yang diizinkan) disimpan di `config.json`.
- Di dalam USB terdapat file kunci `securevox.key` berisi 32 byte acak (dibuat saat setup/registrasi dongle).
- Fungsi: `cek_dongle() -> bool`, `baca_file_kunci() -> bytes`, `registrasi_dongle()`.
- Jika dongle tidak ada, tampilkan layar "Colokkan Dongle" dan polling sampai terdeteksi. Fitur lain tidak boleh dapat diakses.
- Jalankan pengecekan berkala di background thread, dengan callback saat dongle dicabut.

### 6.2 Modul Biometrik Wajah (`modules/face_auth.py`)

- Pendaftaran: ambil 15-30 sampel wajah dari webcam, simpan sebagai template/model (bukan foto mentah yang dipajang di UI). Simpan di folder `data/faces/`.
- Verifikasi: tangkap wajah dari webcam, bandingkan dengan template, ambang batas (threshold) dapat diatur di `config.json`.
- Maksimum 3 kali percobaan gagal, lalu kembali ke layar awal dan catat ke log.
- Tampilkan preview kamera dengan kotak deteksi wajah dan status (hijau = cocok, merah = tidak cocok).

### 6.3 Modul Login (`modules/login.py`)

- Registrasi akun: username + password, password di-hash `SHA-256(salt + password)` dengan salt acak 16 byte per user (lebih baik gunakan PBKDF2-HMAC-SHA256 minimal 100.000 iterasi, tetap jelaskan algoritmanya di UI/laporan).
- Simpan hanya `salt` dan `hash`, tidak pernah menyimpan password asli.
- Login membandingkan hash dengan perbandingan waktu konstan (`hmac.compare_digest`).
- Setelah login berhasil, turunkan **Master Key**:

```
Master Key = PBKDF2(password + isi_securevox.key, salt_master, 200000 iterasi, 32 byte)
```

Master Key hanya disimpan di memori selama sesi dan dihapus saat logout atau dongle dicabut.

### 6.4 Pesan Teks: Super Enkripsi (`modules/crypto_text.py`)

Urutan enkripsi (lapisan klasik, lalu modern):

1. **Vigenère Cipher** (kunci turunan dari Master Key atau kunci yang diinput pengguna)
2. **Transposisi Kolom** (kunci kata)
3. **AES-256** (mode CBC atau GCM, IV/nonce acak, hasil di-encode Base64)

Dekripsi dilakukan dengan urutan terbalik. UI wajib menampilkan hasil **tiap tahap** (plaintext, hasil Vigenère, hasil Transposisi, hasil AES) agar proses terlihat saat demo.

### 6.5 Pesan Audio (pengganti pesan file) (`modules/crypto_audio.py`)

- Input: rekam suara langsung dari mikrofon atau pilih file `.wav`.
- Enkripsi seluruh byte file dengan **ChaCha20** (algoritma berbeda dari teks), nonce acak disimpan di awal file.
- Output: file `.enc` di `data/audio/`, dan metadata (nama, ukuran, waktu, pengirim) di database.
- Putar: dekripsi ke memori atau file sementara, putar, lalu hapus file sementara.
- UI menampilkan ukuran file asli vs terenkripsi dan potongan hex ciphertext.

### 6.6 Pesan Penting di Basis Data (`modules/database.py`)

- SQLite di `data/securevox.db`.
- Tabel: `users`, `messages`, `audio_messages`, `stego_messages`, `logs`.
- Konten pesan dan field sensitif disimpan sebagai ciphertext **AES-GCM** (nonce + tag + ciphertext, Base64) dengan kunci dari Master Key.
- Tanpa dongle dan login benar, isi database tidak bisa dibaca. Sediakan tombol "Lihat isi DB mentah" untuk membuktikan data terenkripsi saat demo.

### 6.7 Pesan Gambar: Steganografi (`modules/stego.py`)

- Input: gambar cover berformat **PNG** (tolak JPG, jelaskan alasannya di UI) dan pesan teks.
- Pesan **dienkripsi AES dulu**, lalu disisipkan dengan teknik **LSB** (1 bit per channel warna). Sisipkan header berisi panjang pesan dan penanda (magic bytes).
- Cek kapasitas gambar, tampilkan error jika pesan terlalu panjang.
- Ekstraksi: baca header, ambil bit, dekripsi, tampilkan pesan.
- UI menampilkan gambar asli dan gambar stego berdampingan, plus nilai perbandingan (misal PSNR atau jumlah piksel berubah).

### 6.8 Aset Penting: Blockchain Sederhana (`modules/blockchain.py`)

- Struktur blok: `index`, `timestamp`, `data` (nama aset, SHA-256 file aset, pemilik), `previous_hash`, `nonce`, `hash`.
- Proof of Work ringan (hash harus diawali `000`).
- Blok genesis dibuat otomatis.
- Fitur: tambah aset (pilih file, hitung hash, buat blok), lihat chain, **validasi chain**, dan verifikasi file aset (hash file sekarang dibandingkan hash di blok).
- Chain disimpan di `data/chain.json` atau tabel database.
- Sediakan tombol demo "Simulasi manipulasi" yang mengubah data satu blok, lalu validasi harus menunjukkan blok mana yang rusak.

### 6.9 Log Aktivitas

Catat: login berhasil/gagal, verifikasi wajah, dongle dicabut/dipasang, kirim/baca pesan, tambah aset, validasi chain. Tampilkan di tab Log dengan waktu dan status.

## 7. Kebutuhan Antarmuka (UI/UX)

- **Arsitektur:** satu aplikasi desktop, dijalankan dengan `python main.py` (atau `.exe` hasil PyInstaller). Tidak ada server, browser, atau koneksi internet.
- Antarmuka dibuat dengan **PySide6**. Layar bergantian lewat `QStackedWidget`: `DongleScreen`, `FaceScreen`, `LoginScreen`, `Dashboard`.
- Dashboard memakai `QTabWidget` dengan tab: Pesan Teks, Pesan Audio, Pesan Gambar, Aset (Blockchain), Log.
- Tema gelap bergaya cyber security dengan satu warna aksen (biru atau hijau neon), semua gaya ada di satu file `ui/theme.qss`. Nama dan logo teks "SecureVox" tampil di header.
- Indikator status dongle (hijau/merah) selalu tampil di header dan diperbarui oleh `QTimer` setiap 3 detik.
- Tampilkan plaintext vs ciphertext berdampingan (dua `QTextEdit`) di setiap fitur enkripsi.
- Jendela dapat di-resize dengan layout (`QVBoxLayout`/`QGridLayout`), ukuran awal 1200×780.
- Pesan error memakai `QMessageBox` atau label status berwarna, dalam Bahasa Indonesia yang jelas.

**Aturan teknis aplikasi**

- Pisahkan logika dan tampilan: folder `modules/` tidak boleh mengimpor PySide6. Folder `ui/` hanya memanggil fungsi dari `modules/`.
- Kamera: `VideoCapture` OpenCV berjalan di `QThread`, mengirim frame lewat signal sebagai `QImage` ke `QLabel` untuk preview, lengkap dengan kotak deteksi wajah.
- Proses berat (enkripsi file audio, proof of work, ekstraksi stego) berjalan di `QThread` atau `QThreadPool` supaya jendela tidak membeku, hasilnya dikirim kembali lewat signal.
- Audio direkam dengan `sounddevice` dan disimpan sebagai WAV. Pemutaran dilakukan dari data hasil dekripsi di memori atau file sementara yang dihapus setelah selesai.
- Pemilihan file (WAV, PNG, aset) memakai `QFileDialog`.
- Master Key hanya disimpan di objek `Session` di memori, dan dihapus saat logout atau dongle dicabut.
- Semua modul dapat diuji tanpa GUI lewat `tests/`.
- Opsional: kemas dengan `pyinstaller --noconsole --onefile main.py` agar bisa dijalankan tanpa mengetik perintah.

Kerangka dasar `main.py`:

```python
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open("ui/theme.qss", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

## 8. Kebutuhan Non-Fungsional

- Tidak ada kunci atau password yang ditulis langsung (hardcode) di kode.
- Gunakan IV/nonce acak setiap enkripsi, jangan dipakai ulang.
- Penanganan error untuk: kamera tidak ada, mikrofon tidak ada, USB tidak terdeteksi, file rusak, input kosong.
- Kode modular, ada docstring singkat dan komentar Bahasa Indonesia pada bagian algoritma.
- Setiap modul kripto punya fungsi uji sederhana (`tests/`) yang membuktikan `decrypt(encrypt(x)) == x`.

## 9. Struktur Proyek

```
SecureVox/
├── main.py
├── config.json
├── requirements.txt
├── README.md
├── modules/                 (logika murni, tanpa PySide6)
│   ├── dongle.py
│   ├── face_auth.py
│   ├── login.py
│   ├── crypto_text.py
│   ├── crypto_audio.py
│   ├── database.py
│   ├── stego.py
│   └── blockchain.py
├── ui/                      (tampilan PySide6)
│   ├── main_window.py       (QStackedWidget + header status dongle)
│   ├── session.py           (Master Key dan user aktif, hanya di memori)
│   ├── theme.qss
│   ├── screens/
│   │   ├── dongle_screen.py
│   │   ├── face_screen.py
│   │   ├── login_screen.py
│   │   └── dashboard.py
│   ├── tabs/
│   │   ├── text_tab.py
│   │   ├── audio_tab.py
│   │   ├── image_tab.py
│   │   ├── asset_tab.py
│   │   └── log_tab.py
│   ├── widgets/
│   │   ├── camera_widget.py
│   │   └── workers.py       (QThread untuk proses berat)
│   └── resources/           (ikon, logo)
├── tests/
└── data/
    ├── faces/
    ├── audio/
    ├── stego/
    └── securevox.db
```

## 10. Model Data Singkat

| Tabel | Kolom utama |
| --- | --- |
| `users` | id, username, salt, password\_hash, created\_at |
| `messages` | id, sender, content\_enc, created\_at |
| `audio_messages` | id, sender, file\_path, nonce, size, created\_at |
| `stego_messages` | id, sender, image\_path, created\_at |
| `logs` | id, event, status, created\_at |

## 11. Di Luar Cakupan

- Pengiriman pesan lewat jaringan atau server (pesan disimulasikan lokal antar akun).
- Versi web atau akses lewat browser.
- Dukungan Linux/macOS.
- Blockchain terdistribusi (cukup rantai lokal satu node).
- Penyimpanan kunci di hardware token khusus (dongle hanya USB biasa).

## 12. Fase Pengerjaan untuk OpenCode

Kerjakan berurutan. Setiap fase harus bisa dijalankan dan diuji sebelum lanjut.

1. **Setup proyek**: buat struktur folder, `requirements.txt`, `config.json`, `main.py` yang membuka jendela PySide6, `ui/theme.qss` bertema gelap, dan `QStackedWidget` dengan empat layar kosong.
2. **Modul dongle**: deteksi `VID_058F&PID_6387` + file kunci, `QTimer` polling di thread terpisah, `DongleScreen` "Colokkan Dongle" dengan indikator status.
3. **Database + login**: SQLite, registrasi, hash + salt, login, derivasi Master Key di `Session`, `LoginScreen`.
4. **Biometrik wajah**: pendaftaran, verifikasi, batas 3 percobaan, `FaceScreen` dengan preview kamera dari `QThread`.
5. **Super enkripsi teks**: Vigenère, Transposisi, AES-256, tab Pesan Teks dengan tampilan tiap tahap.
6. **Enkripsi audio**: rekam/pilih WAV, ChaCha20, putar kembali, tab Pesan Audio.
7. **Enkripsi database**: AES-GCM pada field pesan, tombol lihat DB mentah.
8. **Steganografi gambar**: LSB PNG dengan enkripsi sebelum sisip, tab Pesan Gambar dengan perbandingan gambar asli dan stego.
9. **Blockchain aset**: blok, PoW, validasi, simulasi manipulasi, tab Aset dengan tampilan rantai blok.
10. **Integrasi dan polesan**: `Dashboard` bertab, log aktivitas, kunci otomatis saat dongle dicabut, perapihan tema QSS.
11. **Pengujian dan dokumentasi**: unit test modul kripto, `README.md` berisi cara instal dan menjalankan (`python main.py`), cara membuat `.exe` dengan PyInstaller, serta skenario demo.

## 13. Acceptance Criteria (Checklist Akhir)

- [ ] Aplikasi tidak bisa melewati layar awal tanpa dongle yang benar.
- [ ] Mencabut USB saat aplikasi berjalan langsung mengunci aplikasi.
- [ ] Wajah tidak terdaftar ditolak, 3 kali gagal kembali ke awal.
- [ ] Password salah ditolak, password disimpan sebagai hash + salt.
- [ ] Pesan teks melewati 3 lapis enkripsi dan dapat didekripsi kembali dengan benar.
- [ ] Audio terenkripsi (ChaCha20) tidak dapat diputar tanpa dekripsi, dan dapat diputar normal setelah dekripsi.
- [ ] Isi `securevox.db` tidak terbaca (ciphertext) jika dibuka dengan DB viewer.
- [ ] Pesan tersembunyi di PNG dapat diekstrak dan didekripsi, gambar stego tampak sama dengan aslinya.
- [ ] Validasi blockchain mendeteksi blok yang dimanipulasi dan menunjukkan lokasinya.
- [ ] Semua tes di `tests/` lulus dan `README.md` tersedia.


