# DOKU API Tester

Aplikasi Python untuk testing integrasi API DOKU (Payment Gateway Indonesia).

## Fitur

- ✅ **Signature Generator** - Generate HMAC-SHA256 signature sesuai format DOKU
- ✅ **Virtual Account API** - Create, Update, Delete Virtual Account
- ✅ **QRIS API** - Generate QRIS untuk pembayaran
- ✅ **Order Status** - Cek status pembayaran
- ✅ **CLI Interaktif** - Menu interaktif untuk testing mudah
- ✅ **Support Sandbox & Production**

## Instalasi

```bash
# Clone repository
git clone <repo-url>
cd sc_tes_api_doku

# Install dependencies
pip install -r requirements.txt
```

## Mendapatkan Credentials DOKU

1. Kunjungi https://dashboard.doku.com
2. Daftar atau login
3. Buat Project baru → Pilih environment "Sandbox" untuk testing
4. Buka menu "API Keys"
5. Copy **Client ID** dan **Secret Key**

## Penggunaan

### 1. CLI Interaktif (Recommended)

```bash
python cli.py
```

Menu yang tersedia:
- Signature Generator - Generate signature untuk request
- Test Virtual Account - Create VA di Sandbox
- Test QRIS - Generate QRIS di Sandbox
- API Reference - Lihat daftar endpoints & channels
- Panduan Credentials - Cara mendapatkan API keys

### 2. Direct Script

```bash
python doku_api_tester.py
```

### 3. Sebagai Module

```python
from doku_api_tester import DokuApiTester

# Initialize
tester = DokuApiTester(
    client_id="YOUR_CLIENT_ID",
    secret_key="YOUR_SECRET_KEY",
    use_sandbox=True  # False untuk production
)

# Create Virtual Account
result = tester.va_api.create_va(
    customer_name="John Doe",
    customer_email="john@example.com",
    amount=150000,
    invoice_number="INV-2026-001",
    channel="VIRTUAL_ACCOUNT_BCA"
)

print(result)
```

## Signature Generation

DOKU API menggunakan HMAC-SHA256 untuk autentikasi. Komponen signature:

```
Client-Id:{client_id}
Request-Id:{uuid}
Request-Timestamp:{iso8601_timestamp}
Request-Target:{endpoint_path}
Digest:{sha256_base64_of_body}  # Hanya untuk POST/PUT
```

Contoh generate signature manual:

```python
from doku_api_tester import DokuSignatureGenerator
import uuid
from datetime import datetime

generator = DokuSignatureGenerator("YOUR_SECRET_KEY")

body = {"order": {"invoice_number": "INV-001", "amount": 10000}}
digest = generator.generate_digest(body)

signature = generator.generate_signature(
    client_id="YOUR_CLIENT_ID",
    request_id=str(uuid.uuid4()),
    request_timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    request_target="/doku-virtual-account/v2/payment-code",
    digest=digest
)

print(f"Signature: {signature}")
# Output: HMACSHA256=xxxxxxxxxxxxxx
```

## Virtual Account Channels

| Channel | Code |
|---------|------|
| BCA | `VIRTUAL_ACCOUNT_BCA` |
| BNI | `VIRTUAL_ACCOUNT_BNI` |
| BRI | `VIRTUAL_ACCOUNT_BRI` |
| Mandiri | `VIRTUAL_ACCOUNT_MANDIRI` |
| Permata | `VIRTUAL_ACCOUNT_PERMATA` |
| CIMB | `VIRTUAL_ACCOUNT_CIMB` |
| Danamon | `VIRTUAL_ACCOUNT_DANAMON` |
| BSI | `VIRTUAL_ACCOUNT_BSI` |

## API Endpoints

### Base URLs
- Sandbox: `https://api-sandbox.doku.com`
- Production: `https://api.doku.com`

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/doku-virtual-account/v2/payment-code` | Create VA |
| PUT | `/doku-virtual-account/v2/payment-code/{code}` | Update VA |
| DELETE | `/doku-virtual-account/v2/payment-code/{code}` | Delete VA |
| POST | `/qris/v1/create` | Generate QRIS |
| GET | `/orders/v1/status/{invoice}` | Check Status |

## Response Codes

| Code | Description |
|------|-------------|
| 2000 | Success |
| 2001 | Pending |
| 4010 | Invalid Signature |
| 4011 | Invalid Client |
| 4012 | Unauthorized |
| 4040 | Not Found |
| 4090 | Duplicate Order |
| 5000 | Internal Error |

## Struktur Project

```
sc_tes_api_doku/
├── doku_api_tester.py  # Main API client
├── cli.py              # Interactive CLI
├── config.py           # Configuration & constants
├── requirements.txt    # Dependencies
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
└── README.md           # Documentation
```

## Environment Variables

Buat file `.env` dari template:

```bash
cp .env.example .env
```

Edit `.env` dan isi credentials Anda:

```
DOKU_CLIENT_ID=your-client-id
DOKU_SECRET_KEY=your-secret-key
DOKU_ENVIRONMENT=sandbox
```

## Keamanan

⚠️ **PENTING:**
- JANGAN commit credentials ke repository
- Gunakan `.env` file untuk credentials lokal
- Gunakan environment variables untuk production
- Secret Key harus dijaga kerahasiaannya

## Troubleshooting

### Error: Invalid Signature (4010)
- Pastikan Secret Key benar
- Pastikan format timestamp menggunakan UTC
- Pastikan body JSON di-minify (tanpa whitespace)
- Cek urutan komponen signature

### Error: Invalid Client (4011)
- Pastikan Client ID benar
- Pastikan project sudah aktif di DOKU Dashboard

### Error: Unauthorized (4012)
- Cek apakah environment (sandbox/production) sudah sesuai
- Pastikan credentials belum expired

## Lisensi

MIT License
