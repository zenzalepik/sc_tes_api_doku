"""
Simple test script untuk DOKU API
Jalankan: python run_test.py
"""

from doku_api_tester import DokuApiTester, DokuSignatureGenerator
import json
from datetime import datetime
import os

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
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
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


def main():
    print()
    print("*" * 60)
    print("  DOKU API TESTER")
    print("*" * 60)
    print()
    print(f"Client ID: {'[BELUM DIISI]' if not CLIENT_ID else CLIENT_ID}")
    print("Secret Key: " + ("[BELUM DIISI]" if not SECRET_KEY else "[TERISI]"))
    print(f"Environment: {'Sandbox' if USE_SANDBOX else 'Production'}")
    print()
    
    # Test 1: Signature
    test_signature()
    
    # Test 2: Create VA
    test_create_va()
    
    print("\n" + "=" * 60)
    print("TESTING SELESAI")
    print("=" * 60)


if __name__ == "__main__":
    main()
