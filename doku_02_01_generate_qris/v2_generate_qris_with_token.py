import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
import datetime
import json
import hmac
import hashlib
import base64
import sys
import os
from urllib.parse import urlparse

# ==========================================
# IMPORT MODULE TOKEN GENERATOR
# ==========================================
# Tambahkan parent directory ke sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import token generator
try:
    from doku_01_get_token.v2_doku_token_generator import DokuTokenGenerator
    print("✓ Token generator module imported successfully")
except ImportError as e:
    print(f"✗ Error importing token generator: {e}")
    print(f"Current sys.path: {sys.path}")
    DokuTokenGenerator = None

class GenerateQRISApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DOKU Generate QRIS Tester with Token Generator")
        self.root.geometry("900x850")
        
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Token Generator Section ---
        token_gen_frame = ttk.Frame(main_frame)
        token_gen_frame.pack(fill=tk.X, pady=(0, 10))
        
        if DokuTokenGenerator:
            # Initialize token generator
            self.token_generator = DokuTokenGenerator(
                token_gen_frame,
                on_token_generated=self.on_token_generated
            )
            print("✓ Token generator initialized")
        else:
            # Show error if module not found
            error_label = ttk.Label(
                token_gen_frame,
                text="⚠ Token Generator Module Not Found!",
                foreground="red",
                font=("Segoe UI", 10, "bold")
            )
            error_label.pack(pady=10)
            self.token_generator = None
        
        # --- Configuration Section ---
        cfg_frame = ttk.LabelFrame(main_frame, text="QRIS Configuration", padding="10")
        cfg_frame.pack(fill=tk.X, pady=(0, 10))

        # ... (rest of your QRIS configuration code remains the same)
        ttk.Label(cfg_frame, text="QRIS Generate URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.url_var = tk.StringVar(
            value="https://api-sandbox.doku.com/snap-adapter/b2b/v1.0/qr/qr-mpm-generate"
        )
        ttk.Entry(cfg_frame, textvariable=self.url_var, width=70).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(cfg_frame, text="X-PARTNER-ID:").grid(row=1, column=0, sticky="w", pady=5)
        self.partner_id_var = tk.StringVar()
        ttk.Entry(cfg_frame, textvariable=self.partner_id_var, width=40).grid(
            row=1, column=1, sticky="w", padx=5
        )

        ttk.Label(cfg_frame, text="Client Secret (HMAC key):").grid(row=2, column=0, sticky="w", pady=5)
        self.client_secret_var = tk.StringVar()
        ttk.Entry(cfg_frame, textvariable=self.client_secret_var, width=40, show="*").grid(
            row=2, column=1, sticky="w", padx=5
        )

        # Access Token field
        ttk.Label(cfg_frame, text="Access Token (Bearer):").grid(row=3, column=0, sticky="w", pady=5)
        self.access_token_var = tk.StringVar()
        self.access_token_entry = ttk.Entry(cfg_frame, textvariable=self.access_token_var, width=70)
        self.access_token_entry.grid(row=3, column=1, sticky="w", padx=5)
        
        if DokuTokenGenerator:
            ttk.Button(cfg_frame, text="Use Generated Token", 
                      command=self.use_generated_token).grid(row=3, column=2, padx=5)
        else:
            ttk.Label(cfg_frame, text="Module not available", 
                     foreground="gray").grid(row=3, column=2, padx=5)

        ttk.Label(cfg_frame, text="CHANNEL-ID:").grid(row=4, column=0, sticky="w", pady=5)
        self.channel_id_var = tk.StringVar(value="H2H")
        ttk.Entry(cfg_frame, textvariable=self.channel_id_var, width=20).grid(
            row=4, column=1, sticky="w", padx=5
        )

        ttk.Label(cfg_frame, text="X-EXTERNAL-ID:").grid(row=5, column=0, sticky="w", pady=5)
        self.external_id_var = tk.StringVar()
        ttk.Entry(cfg_frame, textvariable=self.external_id_var, width=40).grid(
            row=5, column=1, sticky="w", padx=5
        )

        ttk.Button(cfg_frame, text="Generate External ID", command=self.generate_external_id).grid(
            row=5, column=2, sticky="w", padx=5
        )

        # --- Request Body Section ---
        body_frame = ttk.LabelFrame(main_frame, text="Request Body (JSON)", padding="10")
        body_frame.pack(fill=tk.BOTH, expand=True)

        self.body_text = scrolledtext.ScrolledText(body_frame, height=12, font=("Consolas", 10))
        self.body_text.pack(fill=tk.BOTH, expand=True)

        default_body = {
            "partnerReferenceNo": "a98757c8dbc6434ab5dd4c55d9092d9a",
            "merchantId": "2115",
            "terminalId": "k45",
            "validityPeriod": "2023-11-08T17:38:42+07:00",
            "amount": {
                "value": "10000.00",
                "currency": "IDR",
            },
            "additionalInfo": {
                "customerName": "John Doe",
                "invoiceNumber": "INV-001",
            },
        }
        self.body_text.insert("1.0", json.dumps(default_body, indent=2))

        # --- Action Buttons ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(5, 5))

        self.send_btn = ttk.Button(action_frame, text="Generate QRIS", command=self.start_generate)
        self.send_btn.pack(side=tk.LEFT)

        # --- Log Section ---
        log_frame = ttk.LabelFrame(main_frame, text="Logs (Request & Response)", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, font=("Consolas", 10), state="normal")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.bind("<Control-a>", self.select_all)
        self.log_text.bind("<Control-A>", self.select_all)

        clear_btn = ttk.Button(log_frame, text="Clear Logs", command=self.clear_logs)
        clear_btn.pack(anchor="e", pady=(5, 0))
    
    def on_token_generated(self, token, token_info):
        """Callback when token is generated"""
        if token:
            # Auto-fill the access token field
            self.access_token_var.set(token)
            
            # Log to UI
            self.log(f"\n[Token Generator] Token generated successfully!")
            self.log(f"Token Type: {token_info.get('tokenType', 'Bearer')}")
            self.log(f"Expires in: {token_info.get('expiresIn', 0)} seconds")
            self.log(f"Status: {token_info.get('responseMessage', 'Success')}")
    
    def use_generated_token(self):
        """Use the generated token in the access token field"""
        if self.token_generator:
            token = self.token_generator.get_token()
            if token:
                self.access_token_var.set(token)
                self.log("✓ Using generated token")
            else:
                messagebox.showwarning("No Token", "Please generate a token first")
    
    def select_all(self, event):
        self.log_text.tag_add("sel", "1.0", "end")
        return "break"

    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def generate_external_id(self):
        now = datetime.datetime.now()
        value = now.strftime("%Y%m%d%H%M%S%f")
        self.external_id_var.set(value)

    def start_generate(self):
        threading.Thread(target=self.generate_qris, daemon=True).start()

    def generate_qris(self):
        # ... (rest of your QRIS generation code remains the same)
        url = self.url_var.get().strip()
        partner_id = self.partner_id_var.get().strip()
        client_secret = self.client_secret_var.get().strip()
        access_token = self.access_token_var.get().strip()
        channel_id = self.channel_id_var.get().strip()
        external_id = self.external_id_var.get().strip()

        if not url or not partner_id or not client_secret or not access_token or not channel_id:
            self.root.after(
                0,
                lambda: messagebox.showwarning(
                    "Missing Input",
                    "URL, X-PARTNER-ID, Client Secret, Access Token, dan CHANNEL-ID wajib diisi.",
                ),
            )
            return

        if not external_id:
            self.generate_external_id()
            external_id = self.external_id_var.get().strip()

        self.root.after(0, lambda: self.send_btn.configure(state="disabled"))
        self.root.after(0, lambda: self.log("-" * 60))

        try:
            now = datetime.datetime.now().astimezone()
            timestamp = now.isoformat(timespec="seconds")

            body_raw = self.body_text.get("1.0", tk.END).strip()
            try:
                body_obj = json.loads(body_raw)
                body_minified = json.dumps(body_obj, separators=(",", ":"))
            except json.JSONDecodeError as e:
                self.root.after(0, lambda: self.log(f"Body JSON error: {e}"))
                return

            parsed = urlparse(url)
            endpoint_path = parsed.path

            body_hash = hashlib.sha256(body_minified.encode("utf-8")).hexdigest().lower()

            string_to_sign = f"POST:{endpoint_path}:{access_token}:{body_hash}:{timestamp}"

            signature_bytes = hmac.new(
                client_secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha512,
            ).digest()
            signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

            headers = {
                "X-PARTNER-ID": partner_id,
                "X-EXTERNAL-ID": external_id,
                "X-TIMESTAMP": timestamp,
                "X-SIGNATURE": signature_b64,
                "Authorization": f"Bearer {access_token}",
                "CHANNEL-ID": channel_id,
                "Content-Type": "application/json",
            }

            self.root.after(0, lambda: self.log(f"URL: {url}"))
            self.root.after(0, lambda: self.log(f"Timestamp: {timestamp}"))
            self.root.after(0, lambda: self.log(f"StringToSign: {string_to_sign}"))
            self.root.after(0, lambda: self.log("\n--- Request Headers ---"))
            self.root.after(0, lambda: self.log(json.dumps(headers, indent=2)))
            self.root.after(0, lambda: self.log("\n--- Request Body (minified) ---"))
            self.root.after(0, lambda: self.log(body_minified))

            response = requests.post(url, data=body_minified, headers=headers, timeout=60)

            self.root.after(0, lambda: self.log(f"\n--- Response Status: {response.status_code} ---"))
            try:
                resp_json = response.json()
                self.root.after(0, lambda: self.log(json.dumps(resp_json, indent=2)))
            except Exception:
                self.root.after(0, lambda: self.log(response.text))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"\nError occurred: {e}"))
        finally:
            self.root.after(0, lambda: self.send_btn.configure(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    app = GenerateQRISApp(root)
    root.mainloop()