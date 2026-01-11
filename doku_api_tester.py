"""
DOKU API Tester - Aplikasi untuk Testing Integrasi API DOKU
============================================================
Aplikasi ini menyediakan tools untuk menguji berbagai endpoint API DOKU
termasuk Virtual Account, QRIS, dan lainnya.

Fitur:
- Generate Signature HMAC-SHA256 sesuai standar DOKU
- Test berbagai endpoint (Create VA, Check Status, dll)
- Support Sandbox dan Production environment
- Logging lengkap untuk debugging
"""

import hmac
import hashlib
import base64
import json
import uuid
import requests
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Environment(Enum):
    """DOKU Environment"""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class DokuConfig:
    """Konfigurasi untuk koneksi ke DOKU API"""
    client_id: str
    secret_key: str
    environment: Environment = Environment.SANDBOX
    
    @property
    def base_url(self) -> str:
        if self.environment == Environment.SANDBOX:
            return "https://api-sandbox.doku.com"
        return "https://api.doku.com"


class DokuSignatureGenerator:
    """
    Generator untuk signature DOKU API
    
    Signature Format:
    - Client-Id:value
    - Request-Id:value
    - Request-Timestamp:value
    - Request-Target:value
    - Digest:value (untuk POST/PUT request)
    
    Lalu di-HMAC-SHA256 dengan Secret Key dan di-base64 encode
    """
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_digest_from_string(self, body_str: str) -> str:
        sha256_hash = hashlib.sha256(body_str.encode('utf-8')).digest()
        digest = base64.b64encode(sha256_hash).decode('utf-8')
        logger.debug(f"Body string: {body_str}")
        logger.debug(f"Generated Digest: {digest}")
        return digest

    def generate_digest(self, body: dict) -> str:
        """
        Generate Digest dari request body
        Digest = Base64(SHA-256(minified JSON body))
        """
        body_str = json.dumps(body, separators=(',', ':'))
        return self.generate_digest_from_string(body_str)
    
    def generate_signature(
        self,
        client_id: str,
        request_id: str,
        request_timestamp: str,
        request_target: str,
        digest: Optional[str] = None
    ) -> str:
        """
        Generate HMAC-SHA256 signature sesuai format DOKU
        
        Args:
            client_id: Client ID dari DOKU
            request_id: UUID unik untuk request
            request_timestamp: Timestamp dalam format ISO 8601
            request_target: Path endpoint (contoh: /doku-virtual-account/v2/payment-code)
            digest: Digest dari body (wajib untuk POST/PUT)
        
        Returns:
            Signature dalam format "HMACSHA256=xxxxx"
        """
        # Build signature component string
        components = [
            f"Client-Id:{client_id}",
            f"Request-Id:{request_id}",
            f"Request-Timestamp:{request_timestamp}",
            f"Request-Target:{request_target}",
        ]
        
        if digest:
            components.append(f"Digest:{digest}")
        
        # Join dengan newline, TANPA newline di akhir
        signature_string = "\n".join(components)
        
        logger.debug(f"Signature string:\n{signature_string}")
        
        # Calculate HMAC-SHA256
        hmac_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 encode
        signature_b64 = base64.b64encode(hmac_signature).decode('utf-8')
        
        final_signature = f"HMACSHA256={signature_b64}"
        logger.debug(f"Generated Signature: {final_signature}")
        
        return final_signature


class DokuAPIClient:
    """
    Client untuk berinteraksi dengan DOKU API
    """
    
    def __init__(self, config: DokuConfig):
        self.config = config
        self.signature_generator = DokuSignatureGenerator(config.secret_key)
        self.session = requests.Session()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return str(uuid.uuid4())
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp dalam format ISO 8601 dengan timezone UTC"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def _build_headers(
        self,
        request_target: str,
        body_str: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build headers untuk request ke DOKU API
        """
        request_id = self._generate_request_id()
        request_timestamp = self._generate_timestamp()
        
        # Generate digest jika ada body
        digest = None
        if body_str is not None:
            digest = self.signature_generator.generate_digest_from_string(body_str)
        
        # Generate signature
        signature = self.signature_generator.generate_signature(
            client_id=self.config.client_id,
            request_id=request_id,
            request_timestamp=request_timestamp,
            request_target=request_target,
            digest=digest
        )
        
        headers = {
            "Client-Id": self.config.client_id,
            "Request-Id": request_id,
            "Request-Timestamp": request_timestamp,
            "Signature": signature,
            "Content-Type": "application/json"
        }

        if digest:
            headers["Digest"] = digest
        
        logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
        
        return headers
    
    def post(self, endpoint: str, body: dict) -> requests.Response:
        """
        Send POST request ke DOKU API
        """
        url = f"{self.config.base_url}{endpoint}"
        body_str = json.dumps(body, separators=(',', ':'))
        headers = self._build_headers(endpoint, body_str)
        
        logger.info(f"POST {url}")
        logger.info(f"Body: {json.dumps(body, indent=2)}")
        
        response = self.session.post(url, data=body_str.encode('utf-8'), headers=headers)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {response.text}")
        
        return response
    
    def get(self, endpoint: str) -> requests.Response:
        """
        Send GET request ke DOKU API
        """
        url = f"{self.config.base_url}{endpoint}"
        headers = self._build_headers(endpoint)
        
        logger.info(f"GET {url}")
        
        response = self.session.get(url, headers=headers)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {response.text}")
        
        return response


class VirtualAccountAPI:
    """
    API untuk Virtual Account DOKU
    """
    
    # Endpoint paths
    ENDPOINT_CREATE_VA = "/doku-virtual-account/v2/payment-code"
    ENDPOINT_CHECK_STATUS = "/orders/v1/status"
    
    def __init__(self, client: DokuAPIClient):
        self.client = client
    
    def create_va(
        self,
        customer_name: str,
        customer_email: str,
        amount: int,
        invoice_number: str,
        channel: str = "VIRTUAL_ACCOUNT_BCA",  # BCA, BNI, BRI, MANDIRI, PERMATA, dll
        expired_time: int = 60,  # dalam menit
        reusable_status: bool = False,
        info1: str = "",
        info2: str = "",
        info3: str = ""
    ) -> Dict[str, Any]:
        """
        Membuat Virtual Account baru
        
        Args:
            customer_name: Nama customer
            customer_email: Email customer
            amount: Jumlah yang harus dibayar (dalam Rupiah)
            invoice_number: Nomor invoice unik
            channel: Channel VA (VIRTUAL_ACCOUNT_BCA, VIRTUAL_ACCOUNT_BNI, dll)
            expired_time: Waktu kadaluarsa dalam menit
            reusable_status: Apakah VA bisa digunakan berulang
            info1-3: Informasi tambahan
        
        Returns:
            Response dari DOKU API
        """
        body = {
            "order": {
                "invoice_number": invoice_number,
                "amount": amount
            },
            "virtual_account_info": {
                "expired_time": expired_time,
                "reusable_status": reusable_status,
                "info1": info1,
                "info2": info2,
                "info3": info3
            },
            "customer": {
                "name": customer_name,
                "email": customer_email
            }
        }

        if channel:
            body["additional_info"] = {"channel": channel}
        
        # Tambahkan channel ke endpoint atau body sesuai kebutuhan
        endpoint = self.ENDPOINT_CREATE_VA
        
        response = self.client.post(endpoint, body)
        
        return {
            "status_code": response.status_code,
            "data": self._safe_json(response)
        }

    @staticmethod
    def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
        if not response.text:
            return None
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}
    
    def check_status(self, invoice_number: str) -> Dict[str, Any]:
        """
        Cek status pembayaran berdasarkan invoice number
        """
        endpoint = f"{self.ENDPOINT_CHECK_STATUS}/{invoice_number}"
        response = self.client.get(endpoint)
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.text else None
        }


class QRISApi:
    """
    API untuk QRIS DOKU
    """
    
    ENDPOINT_CREATE_QRIS = "/qris/v1/create"
    
    def __init__(self, client: DokuAPIClient):
        self.client = client
    
    def create_qris(
        self,
        invoice_number: str,
        amount: int,
        customer_name: str = "",
        expired_time: int = 60
    ) -> Dict[str, Any]:
        """
        Generate QRIS untuk pembayaran
        
        Args:
            invoice_number: Nomor invoice unik
            amount: Jumlah pembayaran (dalam Rupiah)
            customer_name: Nama customer (opsional)
            expired_time: Waktu kadaluarsa dalam menit
        
        Returns:
            Response dari DOKU API (termasuk QRIS string dan QR image)
        """
        body = {
            "order": {
                "invoice_number": invoice_number,
                "amount": amount
            },
            "qris_info": {
                "expired_time": expired_time
            },
            "customer": {
                "name": customer_name
            }
        }
        
        response = self.client.post(self.ENDPOINT_CREATE_QRIS, body)
        
        return {
            "status_code": response.status_code,
            "data": self._safe_json(response)
        }

    @staticmethod
    def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
        if not response.text:
            return None
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}


@dataclass
class DokuSnapConfig:
    client_key: str
    client_secret: str
    private_key_pem: str
    environment: Environment = Environment.SANDBOX

    @property
    def base_url(self) -> str:
        if self.environment == Environment.SANDBOX:
            return "https://api-sandbox.doku.com"
        return "https://api.doku.com"


class DokuSnapSignature:
    @staticmethod
    def _minify_json(body: Dict[str, Any]) -> str:
        return json.dumps(body, separators=(",", ":"))

    @staticmethod
    def sha256_hex_lower(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def hmac_sha512_base64(secret: str, text: str) -> str:
        mac = hmac.new(secret.encode("utf-8"), text.encode("utf-8"), hashlib.sha512).digest()
        return base64.b64encode(mac).decode("utf-8")

    @staticmethod
    def rsa_sha256_base64(private_key_pem: str, text: str) -> str:
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except Exception as e:
            raise RuntimeError("Dependency 'cryptography' diperlukan untuk SNAP token") from e

        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        signature = key.sign(text.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode("utf-8")


class DokuSnapClient:
    def __init__(self, config: DokuSnapConfig):
        self.config = config
        self.session = requests.Session()

    def _timestamp_utc_z(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_b2b_token(self) -> Dict[str, Any]:
        endpoint = "/authorization/v1/access-token/b2b"
        url = f"{self.config.base_url}{endpoint}"

        timestamp = self._timestamp_utc_z()
        string_to_sign = f"{self.config.client_key}|{timestamp}"
        x_signature = DokuSnapSignature.rsa_sha256_base64(self.config.private_key_pem, string_to_sign)

        headers = {
            "X-CLIENT-KEY": self.config.client_key,
            "X-TIMESTAMP": timestamp,
            "X-SIGNATURE": x_signature,
            "Content-Type": "application/json",
        }
        body = {"grantType": "client_credentials"}
        body_str = json.dumps(body, separators=(",", ":"))

        logger.info(f"POST {url}")
        logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Body: {body_str}")

        response = self.session.post(url, data=body_str.encode("utf-8"), headers=headers)
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {response.text}")

        data: Optional[Dict[str, Any]]
        try:
            data = response.json() if response.text else None
        except Exception:
            data = {"raw": response.text}
        return {"status_code": response.status_code, "data": data}


class DokuSnapQrisApi:
    ENDPOINT_GENERATE = "/snap-adapter/b2b/v1.0/qr/qr-mpm-generate"

    def __init__(
        self,
        client: DokuSnapClient,
        partner_id: str,
        merchant_id: str,
        terminal_id: str,
        channel_id: str = "H2H",
    ):
        self.client = client
        self.partner_id = partner_id
        self.merchant_id = merchant_id
        self.terminal_id = terminal_id
        self.channel_id = channel_id

    def _timestamp_utc_z(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _external_id(self) -> str:
        return str(uuid.uuid4().int)[:32]

    def generate(
        self,
        partner_reference_no: str,
        amount_idr: int,
        validity_period: Optional[str] = None,
        postal_code: Optional[str] = None,
        fee_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        token_result = self.client.get_b2b_token()
        if token_result["status_code"] != 200 or not token_result.get("data"):
            return token_result

        access_token = str(token_result["data"].get("accessToken", "")).strip()
        if not access_token:
            return {"status_code": 500, "data": {"error": {"message": "Access token kosong"}}}

        endpoint = self.ENDPOINT_GENERATE
        url = f"{self.client.config.base_url}{endpoint}"
        timestamp = self._timestamp_utc_z()

        body: Dict[str, Any] = {
            "partnerReferenceNo": partner_reference_no,
            "amount": {"value": f"{amount_idr:.2f}", "currency": "IDR"},
            "merchantId": self.merchant_id,
            "terminalId": self.terminal_id,
        }
        if validity_period:
            body["validityPeriod"] = validity_period
        if postal_code or fee_type:
            body["additionalInfo"] = {}
            if postal_code:
                body["additionalInfo"]["postalCode"] = postal_code
            if fee_type:
                body["additionalInfo"]["feeType"] = fee_type

        body_str = DokuSnapSignature._minify_json(body)
        body_hash = DokuSnapSignature.sha256_hex_lower(body_str)

        string_to_sign = f"POST:{endpoint}:{access_token}:{body_hash}:{timestamp}"
        x_signature = DokuSnapSignature.hmac_sha512_base64(self.client.config.client_secret, string_to_sign)

        headers = {
            "X-PARTNER-ID": self.partner_id,
            "X-EXTERNAL-ID": self._external_id(),
            "X-TIMESTAMP": timestamp,
            "X-SIGNATURE": x_signature,
            "Authorization": f"Bearer {access_token}",
            "CHANNEL-ID": self.channel_id,
            "Content-Type": "application/json",
        }

        logger.info(f"POST {url}")
        logger.info(f"Request Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Body: {json.dumps(body, indent=2)}")

        response = self.client.session.post(url, data=body_str.encode("utf-8"), headers=headers)
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {response.text}")

        data: Optional[Dict[str, Any]]
        try:
            data = response.json() if response.text else None
        except Exception:
            data = {"raw": response.text}
        return {"status_code": response.status_code, "data": data}


class DokuApiTester:
    """
    Utility class untuk testing API DOKU dengan mudah
    """
    
    def __init__(self, client_id: str, secret_key: str, use_sandbox: bool = True):
        env = Environment.SANDBOX if use_sandbox else Environment.PRODUCTION
        self.config = DokuConfig(
            client_id=client_id,
            secret_key=secret_key,
            environment=env
        )
        self.client = DokuAPIClient(self.config)
        self.va_api = VirtualAccountAPI(self.client)
        self.qris_api = QRISApi(self.client)
    
    def test_connection(self) -> bool:
        """
        Test koneksi ke DOKU API
        """
        logger.info("=== Testing Connection to DOKU API ===")
        logger.info(f"Environment: {self.config.environment.value}")
        logger.info(f"Base URL: {self.config.base_url}")
        logger.info(f"Client ID: {self.config.client_id[:10]}...")
        return True
    
    def test_signature_generation(self) -> None:
        """
        Test signature generation
        """
        logger.info("=== Testing Signature Generation ===")
        
        # Sample data
        sample_body = {
            "order": {
                "invoice_number": "INV-TEST-001",
                "amount": 10000
            },
            "customer": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        
        request_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        target = "/doku-virtual-account/v2/payment-code"
        
        # Generate digest
        digest = self.client.signature_generator.generate_digest(sample_body)
        logger.info(f"Digest: {digest}")
        
        # Generate signature
        signature = self.client.signature_generator.generate_signature(
            client_id=self.config.client_id,
            request_id=request_id,
            request_timestamp=timestamp,
            request_target=target,
            digest=digest
        )
        logger.info(f"Signature: {signature}")
    
    def test_create_va(
        self,
        amount: int = 10000,
        channel: str = "VIRTUAL_ACCOUNT_BCA"
    ) -> Dict[str, Any]:
        """
        Test pembuatan Virtual Account
        """
        logger.info("=== Testing Create Virtual Account ===")
        
        invoice_number = f"INV-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        result = self.va_api.create_va(
            customer_name="Test Customer",
            customer_email="test@example.com",
            amount=amount,
            invoice_number=invoice_number,
            channel=channel,
            expired_time=60
        )
        
        return result
    
    def test_create_qris(self, amount: int = 10000) -> Dict[str, Any]:
        """
        Test pembuatan QRIS
        """
        logger.info("=== Testing Create QRIS ===")

        snap_client_key = os.getenv("DOKU_SNAP_CLIENT_KEY", self.config.client_id)
        snap_client_secret = os.getenv("DOKU_SNAP_CLIENT_SECRET", "")
        private_key_pem = os.getenv("DOKU_SNAP_PRIVATE_KEY", "")
        private_key_path = os.getenv("DOKU_SNAP_PRIVATE_KEY_PATH", "")
        if not private_key_pem and private_key_path:
            try:
                with open(private_key_path, "r", encoding="utf-8") as f:
                    private_key_pem = f.read()
            except Exception:
                private_key_pem = ""

        qris_merchant_id = os.getenv("DOKU_QRIS_MERCHANT_ID", "")
        qris_terminal_id = os.getenv("DOKU_QRIS_TERMINAL_ID", "")
        qris_channel_id = os.getenv("DOKU_QRIS_CHANNEL_ID", "H2H")
        qris_postal_code = os.getenv("DOKU_QRIS_POSTAL_CODE", "") or None
        qris_fee_type = os.getenv("DOKU_QRIS_FEE_TYPE", "") or None

        if snap_client_key and snap_client_secret and private_key_pem and qris_merchant_id and qris_terminal_id:
            snap_config = DokuSnapConfig(
                client_key=snap_client_key,
                client_secret=snap_client_secret,
                private_key_pem=private_key_pem,
                environment=self.config.environment,
            )
            snap_client = DokuSnapClient(snap_config)
            qris_api = DokuSnapQrisApi(
                client=snap_client,
                partner_id=snap_client_key,
                merchant_id=qris_merchant_id,
                terminal_id=qris_terminal_id,
                channel_id=qris_channel_id,
            )

            partner_reference_no = f"INV-QRIS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return qris_api.generate(
                partner_reference_no=partner_reference_no,
                amount_idr=amount,
                postal_code=qris_postal_code,
                fee_type=qris_fee_type,
            )

        invoice_number = f"INV-QRIS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return self.qris_api.create_qris(
            invoice_number=invoice_number,
            amount=amount,
            customer_name="Test Customer",
        )


def main():
    """
    Main function untuk menjalankan test
    """
    print("=" * 60)
    print("DOKU API TESTER")
    print("=" * 60)
    print()
    
    # PENTING: Ganti dengan credentials Anda dari DOKU Dashboard
    # Untuk mendapatkan credentials:
    # 1. Daftar di https://dashboard.doku.com
    # 2. Buat project baru
    # 3. Dapatkan Client ID dan Secret Key dari menu API Keys
    
    CLIENT_ID = "YOUR_CLIENT_ID_HERE"
    SECRET_KEY = "YOUR_SECRET_KEY_HERE"
    USE_SANDBOX = True  # Set False untuk production
    
    if CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        print("⚠️  PERHATIAN: Anda harus mengisi CLIENT_ID dan SECRET_KEY!")
        print()
        print("Cara mendapatkan credentials:")
        print("1. Daftar di https://dashboard.doku.com")
        print("2. Buat project baru atau gunakan project yang sudah ada")
        print("3. Ambil Client ID dan Secret Key dari menu API Keys")
        print()
        print("Untuk saat ini, kita akan menjalankan test signature generation saja...")
        print()
        
        # Demo signature generation dengan dummy credentials
        demo_test_signature_only()
        return
    
    # Initialize tester
    tester = DokuApiTester(CLIENT_ID, SECRET_KEY, USE_SANDBOX)
    
    # Run tests
    tester.test_connection()
    print()
    
    tester.test_signature_generation()
    print()
    
    # Test Create VA
    va_result = tester.test_create_va(amount=10000)
    print(f"\nVA Result: {json.dumps(va_result, indent=2)}")
    
    # Test Create QRIS
    qris_result = tester.test_create_qris(amount=10000)
    print(f"\nQRIS Result: {json.dumps(qris_result, indent=2)}")


def demo_test_signature_only():
    """
    Demo signature generation tanpa credentials asli
    """
    print("=== DEMO: Signature Generation ===")
    print()
    
    # Dummy credentials untuk demo
    demo_client_id = "BRN-0001-0000000001"
    demo_secret_key = "SK-abcdefghijklmnop"
    
    generator = DokuSignatureGenerator(demo_secret_key)
    
    # Sample request body
    sample_body = {
        "order": {
            "invoice_number": "INV-20260109-001",
            "amount": 150000
        },
        "virtual_account_info": {
            "expired_time": 60,
            "reusable_status": False
        },
        "customer": {
            "name": "Budi Santoso",
            "email": "budi@example.com"
        }
    }
    
    request_id = str(uuid.uuid4())
    timestamp = "2026-01-09T00:15:00Z"
    target = "/doku-virtual-account/v2/payment-code"
    
    print(f"Client ID: {demo_client_id}")
    print(f"Request ID: {request_id}")
    print(f"Timestamp: {timestamp}")
    print(f"Target: {target}")
    print()
    
    # Generate digest
    digest = generator.generate_digest(sample_body)
    print(f"Request Body:\n{json.dumps(sample_body, indent=2)}")
    print()
    print(f"Digest (Base64 SHA-256): {digest}")
    print()
    
    # Generate signature
    signature = generator.generate_signature(
        client_id=demo_client_id,
        request_id=request_id,
        request_timestamp=timestamp,
        request_target=target,
        digest=digest
    )
    
    print(f"Signature: {signature}")
    print()
    
    # Show complete headers
    print("=== Complete Headers untuk Request ===")
    headers = {
        "Client-Id": demo_client_id,
        "Request-Id": request_id,
        "Request-Timestamp": timestamp,
        "Signature": signature,
        "Content-Type": "application/json"
    }
    print(json.dumps(headers, indent=2))


if __name__ == "__main__":
    main()
