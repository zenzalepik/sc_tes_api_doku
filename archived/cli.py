"""
DOKU API Interactive CLI Tester
===============================
CLI interaktif untuk testing berbagai fitur API DOKU
"""

import sys
import json
from datetime import datetime
from doku_api_tester import (
    DokuApiTester, 
    DokuSignatureGenerator,
    DokuConfig,
    DokuAPIClient,
    DokuSnapClient,
    DokuSnapConfig,
    DokuSnapQrisApi,
    Environment
)
from config import VAChannels, DokuEndpoints, DokuResponseCodes

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLORS = True
except ImportError:
    HAS_COLORS = False
    # Fallback untuk colorama
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def print_header(text: str):
    """Print header dengan border"""
    width = 60
    print()
    print(Fore.CYAN + "=" * width + Style.RESET_ALL)
    print(Fore.CYAN + Style.BRIGHT + f"  {text}" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * width + Style.RESET_ALL)
    print()


def print_success(text: str):
    """Print success message"""
    print(Fore.GREEN + f"✓ {text}" + Style.RESET_ALL)


def print_error(text: str):
    """Print error message"""
    print(Fore.RED + f"✗ {text}" + Style.RESET_ALL)


def print_warning(text: str):
    """Print warning message"""
    print(Fore.YELLOW + f"⚠ {text}" + Style.RESET_ALL)


def print_info(text: str):
    """Print info message"""
    print(Fore.BLUE + f"ℹ {text}" + Style.RESET_ALL)


def print_json(data: dict):
    """Print formatted JSON"""
    print(Fore.WHITE + json.dumps(data, indent=2) + Style.RESET_ALL)


def get_input(prompt: str, default: str = "") -> str:
    """Get input dengan default value"""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def menu_signature_generator():
    """Menu untuk signature generator"""
    print_header("SIGNATURE GENERATOR")
    
    print("Tool ini akan generate signature HMAC-SHA256 sesuai format DOKU")
    print()
    
    # Get inputs
    client_id = get_input("Client ID", "BRN-TEST-001")
    secret_key = get_input("Secret Key", "SK-test-secret-key")
    request_target = get_input("Request Target (endpoint path)", "/doku-virtual-account/v2/payment-code")
    
    print()
    print("Masukkan JSON body untuk request (atau kosongkan untuk GET request):")
    print("Contoh: {\"order\": {\"invoice_number\": \"INV-001\", \"amount\": 10000}}")
    body_input = input("Body JSON: ").strip()
    
    # Generate
    generator = DokuSignatureGenerator(secret_key)
    
    import uuid
    request_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    digest = None
    if body_input:
        try:
            body = json.loads(body_input)
            digest = generator.generate_digest(body)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON: {e}")
            return
    
    signature = generator.generate_signature(
        client_id=client_id,
        request_id=request_id,
        request_timestamp=timestamp,
        request_target=request_target,
        digest=digest
    )
    
    print()
    print_header("HASIL")
    
    print(Fore.YELLOW + "Headers yang diperlukan:" + Style.RESET_ALL)
    print()
    print(f"  Client-Id: {client_id}")
    print(f"  Request-Id: {request_id}")
    print(f"  Request-Timestamp: {timestamp}")
    if digest:
        print(f"  Digest: {digest}")
    print(f"  Signature: {signature}")
    print()
    
    headers = {
        "Client-Id": client_id,
        "Request-Id": request_id,
        "Request-Timestamp": timestamp,
        "Signature": signature,
        "Content-Type": "application/json"
    }
    
    print(Fore.YELLOW + "Format JSON Headers:" + Style.RESET_ALL)
    print_json(headers)


def menu_test_va():
    """Menu untuk test Virtual Account"""
    print_header("TEST VIRTUAL ACCOUNT")
    
    print("Untuk test ini, Anda memerlukan credentials dari DOKU Dashboard")
    print()
    
    client_id = get_input("Client ID")
    if not client_id:
        print_error("Client ID diperlukan!")
        return
    
    secret_key = get_input("Secret Key")
    if not secret_key:
        print_error("Secret Key diperlukan!")
        return
    
    print()
    print("Pilih channel VA:")
    print("  1. BCA")
    print("  2. BNI")
    print("  3. BRI")
    print("  4. Mandiri")
    print("  5. Permata")
    
    channel_choice = get_input("Pilihan", "1")
    channel_map = {
        "1": VAChannels.BCA,
        "2": VAChannels.BNI,
        "3": VAChannels.BRI,
        "4": VAChannels.MANDIRI,
        "5": VAChannels.PERMATA
    }
    channel = channel_map.get(channel_choice, VAChannels.BCA)
    
    print()
    amount = int(get_input("Amount (Rupiah)", "10000"))
    customer_name = get_input("Customer Name", "Test Customer")
    customer_email = get_input("Customer Email", "test@example.com")
    
    print()
    print_info("Sending request to DOKU...")
    
    tester = DokuApiTester(client_id, secret_key, use_sandbox=True)
    
    try:
        result = tester.va_api.create_va(
            customer_name=customer_name,
            customer_email=customer_email,
            amount=amount,
            invoice_number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            channel=channel
        )
        
        print()
        if result["status_code"] == 200:
            print_success("Virtual Account berhasil dibuat!")
        else:
            print_error(f"Request gagal dengan status: {result['status_code']}")
        
        print()
        print_json(result)
        
    except Exception as e:
        print_error(f"Error: {e}")


def menu_test_qris():
    """Menu untuk test QRIS"""
    print_header("TEST QRIS")
    
    print("Untuk test ini, Anda memerlukan konfigurasi QRIS SNAP dari DOKU")
    print()
    
    snap_client_key = get_input("SNAP Client Key (X-CLIENT-KEY)")
    if not snap_client_key:
        print_error("SNAP Client Key diperlukan!")
        return
    
    snap_client_secret = get_input("SNAP Client Secret")
    if not snap_client_secret:
        print_error("SNAP Client Secret diperlukan!")
        return

    private_key_path = get_input("Private Key Path (PEM)")
    if not private_key_path:
        print_error("Private Key Path diperlukan!")
        return

    try:
        with open(private_key_path, "r", encoding="utf-8") as f:
            private_key_pem = f.read()
    except Exception as e:
        print_error(f"Gagal membaca private key: {e}")
        return

    merchant_id = get_input("QRIS Merchant ID")
    if not merchant_id:
        print_error("QRIS Merchant ID diperlukan!")
        return

    terminal_id = get_input("QRIS Terminal ID")
    if not terminal_id:
        print_error("QRIS Terminal ID diperlukan!")
        return

    channel_id = get_input("CHANNEL-ID", "H2H")
    
    print()
    amount = int(get_input("Amount (Rupiah)", "10000"))
    postal_code = get_input("Postal Code (opsional)", "")
    fee_type = get_input("Fee Type (opsional)", "")
    postal_code = postal_code or None
    fee_type = fee_type or None
    
    print()
    print_info("Sending request to DOKU...")
    
    try:
        snap_config = DokuSnapConfig(
            client_key=snap_client_key,
            client_secret=snap_client_secret,
            private_key_pem=private_key_pem,
            environment=Environment.SANDBOX,
        )
        snap_client = DokuSnapClient(snap_config)
        qris_api = DokuSnapQrisApi(
            client=snap_client,
            partner_id=snap_client_key,
            merchant_id=merchant_id,
            terminal_id=terminal_id,
            channel_id=channel_id,
        )

        result = qris_api.generate(
            partner_reference_no=f"INV-QRIS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            amount_idr=amount,
            postal_code=postal_code,
            fee_type=fee_type,
        )
        
        print()
        if result["status_code"] == 200:
            print_success("QRIS berhasil di-generate!")
        else:
            print_error(f"Request gagal dengan status: {result['status_code']}")
        
        print()
        print_json(result)
        
    except Exception as e:
        print_error(f"Error: {e}")


def menu_api_reference():
    """Tampilkan API reference"""
    print_header("API REFERENCE")
    
    print(Fore.YELLOW + "Base URLs:" + Style.RESET_ALL)
    print(f"  Sandbox: {DokuEndpoints.BASE_SANDBOX}")
    print(f"  Production: {DokuEndpoints.BASE_PRODUCTION}")
    print()
    
    print(Fore.YELLOW + "Virtual Account Endpoints:" + Style.RESET_ALL)
    print(f"  Create: POST {DokuEndpoints.VA_CREATE}")
    print(f"  Update: PUT {DokuEndpoints.VA_UPDATE}")
    print(f"  Delete: DELETE {DokuEndpoints.VA_DELETE}")
    print()
    
    print(Fore.YELLOW + "QRIS Endpoints:" + Style.RESET_ALL)
    print(f"  Create: POST {DokuEndpoints.QRIS_CREATE}")
    print()
    
    print(Fore.YELLOW + "Order Status:" + Style.RESET_ALL)
    print(f"  Check: GET {DokuEndpoints.ORDER_STATUS}")
    print()
    
    print(Fore.YELLOW + "Virtual Account Channels:" + Style.RESET_ALL)
    print(f"  BCA: {VAChannels.BCA}")
    print(f"  BNI: {VAChannels.BNI}")
    print(f"  BRI: {VAChannels.BRI}")
    print(f"  Mandiri: {VAChannels.MANDIRI}")
    print(f"  Permata: {VAChannels.PERMATA}")
    print(f"  CIMB: {VAChannels.CIMB}")
    print(f"  Danamon: {VAChannels.DANAMON}")
    print(f"  BSI: {VAChannels.BSI}")
    print()
    
    print(Fore.YELLOW + "Response Codes:" + Style.RESET_ALL)
    print(f"  {DokuResponseCodes.SUCCESS}: Success")
    print(f"  {DokuResponseCodes.PENDING}: Pending")
    print(f"  {DokuResponseCodes.INVALID_SIGNATURE}: Invalid Signature")
    print(f"  {DokuResponseCodes.INVALID_CLIENT}: Invalid Client")
    print(f"  {DokuResponseCodes.UNAUTHORIZED}: Unauthorized")
    print(f"  {DokuResponseCodes.NOT_FOUND}: Not Found")
    print(f"  {DokuResponseCodes.DUPLICATE_ORDER}: Duplicate Order")
    print(f"  {DokuResponseCodes.INTERNAL_ERROR}: Internal Error")


def menu_how_to_get_credentials():
    """Panduan mendapatkan credentials"""
    print_header("CARA MENDAPATKAN CREDENTIALS DOKU")
    
    print(Fore.CYAN + "Langkah-langkah:" + Style.RESET_ALL)
    print()
    print("1. Kunjungi https://dashboard.doku.com")
    print()
    print("2. Daftar akun baru atau login jika sudah punya akun")
    print()
    print("3. Setelah login, buat Project baru:")
    print("   - Klik 'Create Project'")
    print("   - Isi nama project dan informasi lainnya")
    print("   - Pilih environment 'Sandbox' untuk testing")
    print()
    print("4. Setelah project dibuat, buka menu 'API Keys'")
    print()
    print("5. Copy Client ID dan Secret Key")
    print("   - Client ID: Biasanya format BRN-xxxx-xxxxxxxxx")
    print("   - Secret Key: String rahasia untuk signing")
    print()
    print(Fore.YELLOW + "⚠ PENTING:" + Style.RESET_ALL)
    print("   - JANGAN PERNAH share Secret Key ke orang lain")
    print("   - JANGAN PERNAH commit Secret Key ke repository publik")
    print("   - Gunakan environment variables untuk production")
    print()
    print(Fore.GREEN + "Tips:" + Style.RESET_ALL)
    print("   - Sandbox bisa digunakan untuk testing tanpa biaya")
    print("   - Sandbox tidak melakukan transaksi nyata")
    print("   - Setelah testing selesai, minta credentials Production")


def main():
    """Main menu"""
    while True:
        print_header("DOKU API TESTER - MAIN MENU")
        
        print("Pilih menu:")
        print()
        print("  1. " + Fore.GREEN + "Signature Generator" + Style.RESET_ALL + " - Generate HMAC-SHA256 signature")
        print("  2. " + Fore.GREEN + "Test Virtual Account" + Style.RESET_ALL + " - Create VA di Sandbox")
        print("  3. " + Fore.GREEN + "Test QRIS" + Style.RESET_ALL + " - Generate QRIS di Sandbox")
        print("  4. " + Fore.BLUE + "API Reference" + Style.RESET_ALL + " - Lihat daftar endpoints & channels")
        print("  5. " + Fore.YELLOW + "Cara Dapat Credentials" + Style.RESET_ALL + " - Panduan mendapatkan API keys")
        print()
        print("  0. Exit")
        print()
        
        choice = input("Pilihan Anda: ").strip()
        
        if choice == "1":
            menu_signature_generator()
        elif choice == "2":
            menu_test_va()
        elif choice == "3":
            menu_test_qris()
        elif choice == "4":
            menu_api_reference()
        elif choice == "5":
            menu_how_to_get_credentials()
        elif choice == "0":
            print()
            print_info("Terima kasih telah menggunakan DOKU API Tester!")
            print()
            break
        else:
            print_error("Pilihan tidak valid!")
        
        print()
        input("Tekan Enter untuk melanjutkan...")


if __name__ == "__main__":
    main()
