import sys
import os
import logging
from datetime import datetime

# Add library path
LIBRARY_PATH = os.path.join(os.getcwd(), "doku-python-library-main", "doku-python-library-main")
sys.path.append(LIBRARY_PATH)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from doku_python_library.src.snap import DokuSNAP
    from doku_python_library.src.model.token.token_b2b_response import TokenB2BResponse
    print("SUCCESS: Library imported successfully.")
except ImportError as e:
    print(f"ERROR: Failed to import library: {e}")
    sys.exit(1)

from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_temp_keys():
    """Generate temporary RSA keys for testing initialization"""
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

def main():
    print("="*60)
    print("TESTING OFFICIAL DOKU PYTHON LIBRARY")
    print("="*60)

    # Load env
    load_dotenv()
    
    client_id = os.getenv("DOKU_CLIENT_ID")
    secret_key = os.getenv("DOKU_SECRET_KEY")
    
    if not client_id:
        print("WARNING: DOKU_CLIENT_ID not found in .env")
        client_id = "DUMMY_CLIENT_ID"
        
    print(f"Client ID: {client_id}")
    
    # Generate keys for testing
    print("Generating temporary RSA keys for testing...")
    private_key, public_key = generate_temp_keys()
    
    try:
        # Initialize DokuSNAP
        print("Initializing DokuSNAP...")
        snap = DokuSNAP(
            private_key=private_key,
            client_id=client_id,
            is_production=False,
            public_key=public_key,
            issuer="DOKU",
            secret_key=secret_key if secret_key else "DUMMY_SECRET",
            merchant_public_key=public_key
        )
        print("SUCCESS: DokuSNAP initialized.")
        
        # Try to get token (Expected to fail at API level due to invalid keys/client_id for SNAP)
        print("\nAttempting to get B2B Token...")
        print("(Note: This is expected to fail 'Unauthorized' because we are using generated keys not registered at DOKU)")
        
        token_response = snap.get_token()
        
        print(f"\nResponse Code: {token_response.response_code}")
        print(f"Response Message: {token_response.response_message}")
        print(f"Full Response: {token_response.json()}")
        
        if token_response.access_token:
            print(f"Access Token: {token_response.access_token}")
        
        print("\nTest finished.")
        
    except Exception as e:
        print(f"\nERROR during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
