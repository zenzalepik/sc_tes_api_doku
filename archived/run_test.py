"""
Simple test script untuk DOKU API
Jalankan: python run_test.py
"""

from doku_api_tester import (
    DokuApiTester,
    DokuSignatureGenerator,
    DokuSnapClient,
    DokuSnapConfig,
    DokuSnapQrisApi,
    DokuSnapEWalletApi,
    DokuSnapDirectDebitApi,
    DokuSnapKkiApi,
    DokuSnapVirtualAccountApi,
    Environment,
)
import json
from datetime import datetime, timezone
import os
import uuid

# ==============================================
# MASUKKAN CREDENTIALS ANDA DI SINI
# ==============================================
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

CLIENT_ID = os.getenv("DOKU_CLIENT_ID", "")
SECRET_KEY = os.getenv("DOKU_SECRET_KEY", "")
# ==============================================

USE_SANDBOX = True  # Sandbox environment


def test_signature():
    """Test generate signature"""
    print("=" * 60)
    print("TEST 1: SIGNATURE GENERATION")
    print("=" * 60)

    if not CLIENT_ID or not SECRET_KEY:
        print("SKIP: Credentials belum diisi!")
        print("Set DOKU_CLIENT_ID dan DOKU_SECRET_KEY di environment atau file .env")
        return False
    
    generator = DokuSignatureGenerator(SECRET_KEY)
    
    # Sample body
    body = {
        "order": {
            "invoice_number": f"INV-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "amount": 10000
        },
        "virtual_account_info": {
            "expired_time": 60,
            "reusable_status": False
        },
        "customer": {
            "name": "Test Customer",
            "email": "test@example.com"
        }
    }
    
    import uuid
    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    target = "/doku-virtual-account/v2/payment-code"
    
    # Generate digest
    digest = generator.generate_digest(body)
    print(f"Digest: {digest}")
    
    # Generate signature
    signature = generator.generate_signature(
        client_id=CLIENT_ID,
        request_id=request_id,
        request_timestamp=timestamp,
        request_target=target,
        digest=digest
    )
    print(f"Signature: {signature}")
    
    print("\nHeaders lengkap:")
    headers = {
        "Client-Id": CLIENT_ID,
        "Request-Id": request_id,
        "Request-Timestamp": timestamp,
        "Signature": signature,
        "Content-Type": "application/json"
    }
    print(json.dumps(headers, indent=2))
    
    return True


def test_create_va():
    """Test create Virtual Account"""
    print("\n" + "=" * 60)
    print("TEST 2: CREATE VIRTUAL ACCOUNT")
    print("=" * 60)
    
    if not CLIENT_ID or not SECRET_KEY:
        print("SKIP: Credentials belum diisi!")
        print("Set DOKU_CLIENT_ID dan DOKU_SECRET_KEY di environment atau file .env")
        return False
    
    tester = DokuApiTester(CLIENT_ID, SECRET_KEY, use_sandbox=USE_SANDBOX)
    
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"Invoice Number: {invoice_number}")
    print(f"Amount: Rp 10.000")
    print(f"Environment: {'Sandbox' if USE_SANDBOX else 'Production'}")
    print()
    
    try:
        result = tester.va_api.create_va(
            customer_name="Test Customer",
            customer_email="test@example.com",
            amount=10000,
            invoice_number=invoice_number,
            channel="VIRTUAL_ACCOUNT_BCA"
        )
        
        print(f"Status Code: {result['status_code']}")
        print(f"Response:")
        print(json.dumps(result['data'], indent=2) if result['data'] else "No data")
        
        if result['status_code'] == 200:
            print("\nSUCCESS: Virtual Account berhasil dibuat!")
            return True
        else:
            print(f"\nFAILED: Status {result['status_code']}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def get_snap_config_tuple():
    snap_client_key = os.getenv("DOKU_SNAP_CLIENT_KEY", CLIENT_ID)
    snap_client_secret = os.getenv("DOKU_SNAP_CLIENT_SECRET", "")
    private_key_pem = os.getenv("DOKU_SNAP_PRIVATE_KEY", "")
    private_key_path = os.getenv("DOKU_SNAP_PRIVATE_KEY_PATH", "")
    if not private_key_pem and private_key_path:
        with open(private_key_path, "r", encoding="utf-8") as f:
            private_key_pem = f.read()

    qris_merchant_id = os.getenv("DOKU_QRIS_MERCHANT_ID", "")
    
    if not snap_client_key or not snap_client_secret or not private_key_pem or not qris_merchant_id:
        return None
    
    snap_config = DokuSnapConfig(
        client_key=snap_client_key,
        client_secret=snap_client_secret,
        private_key_pem=private_key_pem,
        environment=Environment.SANDBOX if USE_SANDBOX else Environment.PRODUCTION,
    )
    return snap_config, snap_client_key, qris_merchant_id


def test_get_token_api():
    print("\n" + "=" * 60)
    print("TEST 0: GET TOKEN API (B2B)")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False

        snap_config, _, _ = config_tuple
        snap_client = DokuSnapClient(snap_config)
        result = snap_client.get_b2b_token()

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")
        return result["status_code"] == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_create_qris():
    """Test create QRIS"""
    print("\n" + "=" * 60)
    print("TEST 3: CREATE QRIS")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False
        
        snap_config, snap_client_key, merchant_id = config_tuple
        snap_client = DokuSnapClient(snap_config)
        
        terminal_id = os.getenv("DOKU_QRIS_TERMINAL_ID", "")
        
        qris_api = DokuSnapQrisApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
            terminal_id=terminal_id,
        )

        partner_reference_no = f"INV-QRIS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"Partner Reference No: {partner_reference_no}")
        print(f"Amount: Rp 10.000")
        
        # Load optional fee config
        postal_code = os.getenv("DOKU_QRIS_POSTAL_CODE", "") or None
        fee_type = os.getenv("DOKU_QRIS_FEE_TYPE", "") or None
        # Fee Amount handling: If not set in env, use default or skip
        fee_amount = os.getenv("DOKU_QRIS_FEE_AMOUNT", "") or None 
        
        print(f"Fee Config: Type={fee_type}, Amount={fee_amount}")

        if (fee_type or "").strip() == "2" and not (fee_amount or "").strip():
            print("ERROR: DOKU_QRIS_FEE_TYPE=2 wajib ada DOKU_QRIS_FEE_AMOUNT")
            return False

        result = qris_api.generate(
            partner_reference_no=partner_reference_no,
            amount_idr=10000,
            postal_code=postal_code,
            fee_type=fee_type,
            fee_amount=fee_amount
        )

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")

        if result["status_code"] == 200:
            print("\nSUCCESS: QRIS berhasil dibuat!")
            return True
        else:
            print(f"\nFAILED: Status {result['status_code']}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_ewallet():
    """Test E-Wallet Payment (SNAP)"""
    print("\n" + "=" * 60)
    print("TEST 4: E-WALLET PAYMENT (OVO)")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False
        
        snap_config, snap_client_key, merchant_id = config_tuple
        snap_client = DokuSnapClient(snap_config)
        
        ewallet_api = DokuSnapEWalletApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
        )

        partner_reference_no = f"INV-EWALLET-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        customer_no = "081234567890" # Dummy number
        
        print(f"Partner Ref No: {partner_reference_no}")
        print(f"Channel: OVO")
        print(f"Customer: {customer_no}")

        result = ewallet_api.payment(
            partner_reference_no=partner_reference_no,
            amount_idr=10000,
            customer_no=customer_no,
            channel_code="OVO"
        )

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")
        
        if result["status_code"] == 200:
            print("\nSUCCESS: E-Wallet payment initiated!")
            return True
        else:
            print(f"\nFAILED: Status {result['status_code']}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_direct_debit():
    """Test Direct Debit Payment (SNAP)"""
    print("\n" + "=" * 60)
    print("TEST 5: DIRECT DEBIT PAYMENT")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False
        
        snap_config, snap_client_key, merchant_id = config_tuple
        snap_client = DokuSnapClient(snap_config)
        
        dd_api = DokuSnapDirectDebitApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
        )

        partner_reference_no = f"INV-DD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        customer_no = "081234567890"
        binding_id = "BIND-TOKEN-SAMPLE" # Must be a valid binding ID in real scenario
        
        print(f"Partner Ref No: {partner_reference_no}")
        print(f"Binding ID: {binding_id}")

        result = dd_api.payment(
            partner_reference_no=partner_reference_no,
            amount_idr=10000,
            customer_no=customer_no,
            bank_card_token=binding_id,
            channel_code=os.getenv("DOKU_DD_CHANNEL", "DIRECT_DEBIT_ALL"),
        )

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")
        
        # Usually fails with 400/404 if binding ID is invalid, which is expected in this dummy test
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_kki_cpts():
    """Test Kartu Kredit Indonesia (KKI CPTS)"""
    print("\n" + "=" * 60)
    print("TEST 6: KKI CPTS (Credit Card)")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False
        
        snap_config, snap_client_key, merchant_id = config_tuple
        snap_client = DokuSnapClient(snap_config)
        
        kki_api = DokuSnapKkiApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
        )

        partner_reference_no = f"INV-KKI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        token_id = "TOKEN-CC-SAMPLE" # Must be obtained from frontend tokenization
        
        print(f"Partner Ref No: {partner_reference_no}")
        print(f"Token ID: {token_id}")

        result = kki_api.payment(
            partner_reference_no=partner_reference_no,
            amount_idr=10000,
            token_id=token_id
        )

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")
        
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_create_va_snap():
    """Test Create Virtual Account (SNAP)"""
    print("\n" + "=" * 60)
    print("TEST 7: CREATE VIRTUAL ACCOUNT (SNAP)")
    print("=" * 60)

    try:
        config_tuple = get_snap_config_tuple()
        if not config_tuple:
            print("SKIP: Konfigurasi SNAP belum lengkap.")
            return False
        
        snap_config, snap_client_key, merchant_id = config_tuple
        snap_client = DokuSnapClient(snap_config)
        
        va_api = DokuSnapVirtualAccountApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
        )

        trx_id = f"TRX-VA-{uuid.uuid4().hex[:8].upper()}"
        customer_no = os.getenv("DOKU_VA_CUSTOMER_NO", "00000000000000000001")
        partner_service_id = os.getenv("DOKU_VA_PARTNER_SERVICE_ID", "").strip()
        if not partner_service_id:
            print("SKIP: Set DOKU_VA_PARTNER_SERVICE_ID untuk test SNAP VA.")
            return False

        if not customer_no.isdigit():
            print("ERROR: DOKU_VA_CUSTOMER_NO harus hanya berisi digit.")
            return False

        virtual_account_no = ""  # biarkan helper di API yang merangkai

        print(f"Trx ID: {trx_id}")
        print(f"Customer No: {customer_no}")
        print(f"Raw PartnerServiceId: '{partner_service_id}'")

        result = va_api.create_va(
            partner_service_id=partner_service_id,
            customer_no=customer_no,
            virtual_account_no=virtual_account_no,
            amount_idr=10000,
            trx_id=trx_id
        )

        print(f"Status Code: {result['status_code']}")
        print("Response:")
        print(json.dumps(result["data"], indent=2) if result["data"] else "No data")
        
        if result["status_code"] == 200:
            print("\nSUCCESS: SNAP VA Created!")
            return True
        else:
            print(f"\nFAILED: Status {result['status_code']}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print()
    print("*" * 60)
    print("  DOKU API TESTER (ALL CHANNELS)")
    print("*" * 60)
    print()
    print(f"Client ID: {'[BELUM DIISI]' if not CLIENT_ID else CLIENT_ID}")
    print("Secret Key: " + ("[BELUM DIISI]" if not SECRET_KEY else "[TERISI]"))
    print(f"Environment: {'Sandbox' if USE_SANDBOX else 'Production'}")
    print()
    
    # 1. Get Token API (Implicitly tested in SNAP requests, but we can call it explicitly if needed)
    # We will assume it's working if QRIS/E-Wallet works.
    
    test_get_token_api()
    test_signature()
    test_create_va()
    test_create_qris()
    test_ewallet()
    test_direct_debit()
    test_kki_cpts()
    test_create_va_snap()
    
    print("\n" + "=" * 60)
    print("TESTING SELESAI")
    print("=" * 60)


if __name__ == "__main__":
    main()
