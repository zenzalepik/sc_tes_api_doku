"""
Konfigurasi untuk DOKU API Tester
=================================

PENTING: 
- Jangan commit file ini ke repository jika berisi credentials asli!
- Gunakan .env file atau environment variables untuk production

Cara mendapatkan credentials:
1. Kunjungi https://dashboard.doku.com
2. Login atau daftar akun baru
3. Buat project baru
4. Pilih environment (Sandbox untuk testing)
5. Copy Client ID dan Secret Key
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DokuCredentials:
    """Credentials untuk DOKU API"""
    client_id: str
    secret_key: str
    
    @classmethod
    def from_env(cls) -> 'DokuCredentials':
        """Load credentials dari environment variables"""
        client_id = os.getenv('DOKU_CLIENT_ID')
        secret_key = os.getenv('DOKU_SECRET_KEY')
        
        if not client_id or not secret_key:
            raise ValueError(
                "Environment variables DOKU_CLIENT_ID dan DOKU_SECRET_KEY harus diset!\n"
                "Contoh:\n"
                "  set DOKU_CLIENT_ID=your-client-id\n"
                "  set DOKU_SECRET_KEY=your-secret-key"
            )
        
        return cls(client_id=client_id, secret_key=secret_key)
    
    @classmethod
    def from_file(cls, filepath: str = '.doku_credentials') -> 'DokuCredentials':
        """Load credentials dari file"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                creds = {}
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        creds[key.strip()] = value.strip()
                
                return cls(
                    client_id=creds.get('DOKU_CLIENT_ID', ''),
                    secret_key=creds.get('DOKU_SECRET_KEY', '')
                )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"File {filepath} tidak ditemukan!\n"
                f"Buat file dengan format:\n"
                f"  DOKU_CLIENT_ID=your-client-id\n"
                f"  DOKU_SECRET_KEY=your-secret-key"
            )


# ============================================================
# SANDBOX CREDENTIALS (untuk testing)
# Ganti dengan credentials Anda dari DOKU Dashboard
# ============================================================

SANDBOX_CLIENT_ID = "YOUR_SANDBOX_CLIENT_ID"
SANDBOX_SECRET_KEY = "YOUR_SANDBOX_SECRET_KEY"

# ============================================================
# PRODUCTION CREDENTIALS
# JANGAN PERNAH commit production credentials ke repository!
# ============================================================

PRODUCTION_CLIENT_ID = ""  # Load dari environment variable
PRODUCTION_SECRET_KEY = ""  # Load dari environment variable


# ============================================================
# API Endpoints Reference
# ============================================================

class DokuEndpoints:
    """Reference untuk endpoint DOKU API"""
    
    # Base URLs
    BASE_SANDBOX = "https://api-sandbox.doku.com"
    BASE_PRODUCTION = "https://api.doku.com"
    
    # Virtual Account
    VA_CREATE = "/doku-virtual-account/v2/payment-code"
    VA_UPDATE = "/doku-virtual-account/v2/payment-code/{payment_code}"
    VA_DELETE = "/doku-virtual-account/v2/payment-code/{payment_code}"
    
    # QRIS
    QRIS_CREATE = "/snap-adapter/b2b/v1.0/qr/qr-mpm-generate"
    
    # Order Status
    ORDER_STATUS = "/orders/v1/status/{invoice_number}"
    
    # E-Wallet
    EWALLET_CREATE = "/e-wallets/v1/payment"
    
    # Credit Card
    CC_CHARGE = "/credit-cards/v1/charge"
    CC_CAPTURE = "/credit-cards/v1/capture"


# ============================================================
# Channel Codes Reference
# ============================================================

class VAChannels:
    """Virtual Account Channel Codes"""
    BCA = "VIRTUAL_ACCOUNT_BCA"
    BNI = "VIRTUAL_ACCOUNT_BNI"
    BRI = "VIRTUAL_ACCOUNT_BRI"
    MANDIRI = "VIRTUAL_ACCOUNT_MANDIRI"
    PERMATA = "VIRTUAL_ACCOUNT_PERMATA"
    CIMB = "VIRTUAL_ACCOUNT_CIMB"
    DANAMON = "VIRTUAL_ACCOUNT_DANAMON"
    BSI = "VIRTUAL_ACCOUNT_BSI"  # Bank Syariah Indonesia


class EWalletChannels:
    """E-Wallet Channel Codes"""
    OVO = "OVO"
    DANA = "DANA"
    LINKAJA = "LINKAJA"
    SHOPEEPAY = "SHOPEEPAY"
    GOPAY = "GOPAY"


# ============================================================
# Response Codes Reference
# ============================================================

class DokuResponseCodes:
    """DOKU Response Codes"""
    SUCCESS = "2000"
    PENDING = "2001"
    INVALID_SIGNATURE = "4010"
    INVALID_CLIENT = "4011"
    UNAUTHORIZED = "4012"
    NOT_FOUND = "4040"
    DUPLICATE_ORDER = "4090"
    INTERNAL_ERROR = "5000"
