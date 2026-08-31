# Social Connectors API

Repo mandiri berisi **50 endpoint connector lengkap** untuk:

- TikTok melalui EnsembleData: 20 endpoint
- Instagram melalui EnsembleData: 11 endpoint
- YouTube melalui EnsembleData: 13 endpoint
- Threads melalui EnsembleData: 5 endpoint
- Berita online melalui SerpAPI Google News: 1 endpoint

Semua credential disimpan sebagai environment variable di server. API mengembalikan hasil
normalized serta raw JSON yang telah disensor, dan tidak pernah mengirim API key ke client.

## Menjalankan lokal

Persyaratan: Python 3.11 atau lebih baru.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Isi `ENSEMBLEDATA_API_KEY` dan `SERPAPI_API_KEY` pada `.env`, kemudian jalankan:

```powershell
fastapi dev
```

Dokumentasi tersedia di:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON runtime: http://127.0.0.1:8000/openapi.json
- Snapshot OpenAPI siap Git: `openapi/openapi.json`

## Endpoint lengkap

Setiap endpoint provider muncul sebagai operasi tersendiri di Swagger:

| Method | Pola path | Jumlah |
| --- | --- | ---: |
| `POST` | `/v1/connectors/tiktok/{endpoint_id}` | 20 |
| `POST` | `/v1/connectors/instagram/{endpoint_id}` | 11 |
| `POST` | `/v1/connectors/youtube/{endpoint_id}` | 13 |
| `POST` | `/v1/connectors/threads/{endpoint_id}` | 5 |
| `POST` | `/v1/connectors/news/{endpoint_id}` | 1 |

Gunakan `GET /v1/catalog` untuk membaca nama, deskripsi, upstream path, parameter,
pagination, dan tipe respons seluruh endpoint. Request body di Swagger dibuat otomatis dari
definisi parameter masing-masing endpoint, termasuk required field, tipe data, default, dan batas.

API juga mempertahankan endpoint pencarian ringkas:

| Method | Path | Provider |
| --- | --- | --- |
| `GET` | `/health` | Status konfigurasi connector |
| `GET` | `/v1/catalog` | Metadata 50 endpoint lengkap |
| `POST` | `/v1/youtube/search` | EnsembleData |
| `POST` | `/v1/instagram/search` | EnsembleData |
| `POST` | `/v1/tiktok/search` | EnsembleData |
| `POST` | `/v1/threads/search` | EnsembleData |
| `POST` | `/v1/news/search` | SerpAPI Google News |

Request sosial memakai `query`, `start_date`, `end_date`, `limit`, dan `cursor` opsional.
Request berita memakai `query`, `limit`, `language`, `country`, dan `sort`.

Respons endpoint katalog berisi dua bentuk sekaligus:

- `rows`: hasil yang diratakan agar mudah dikonsumsi tabel atau CSV.
- `raw`: respons JSON provider yang tetap dipertahankan, dengan field credential disensor.

## Postman

Import file berikut ke Postman:

- `postman/Social Connectors API.postman_collection.json`
- `postman/Local.postman_environment.json`

Collection berisi seluruh 50 endpoint katalog, lima convenience search endpoint, health, dan
catalog. Pilih environment **Social Connectors API - Local**, lalu jalankan request. Credential
tetap berada di server `.env`, sehingga tidak perlu dimasukkan ke Postman.

## Validasi

```powershell
python -m pytest
python -m ruff check .
python scripts/import_registry.py
python scripts/generate_postman.py
python scripts/export_openapi.py
```

`import_registry.py` menyalin hanya lima platform yang didukung dari registry sumber.
`generate_postman.py` membuat ulang seluruh request Postman. Perintah terakhir memperbarui
snapshot Swagger/OpenAPI setelah kontrak endpoint berubah.
