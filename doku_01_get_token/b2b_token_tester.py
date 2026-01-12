import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import requests
import datetime
import base64
import json
import pyperclip
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class DokuB2BTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DOKU B2B Token Tester")
        self.root.geometry("800x750")

        # Load environment variables
        self.load_environment_variables()

        # Styles
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))

        # Main Container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Section ---
        input_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # Client ID
        ttk.Label(input_frame, text="Client ID (X-CLIENT-KEY):").grid(row=0, column=0, sticky="w", pady=5)
        self.client_id_var = tk.StringVar()
        self.client_id_var.set(self.env_client_id)  # Set from .env
        ttk.Entry(input_frame, textvariable=self.client_id_var, width=50).grid(row=0, column=1, sticky="w", padx=5)

        # Button to reload from .env
        ttk.Button(input_frame, text="Reload from .env", command=self.reload_from_env, 
                  width=15).grid(row=0, column=2, padx=(5, 0))

        # Target URL
        ttk.Label(input_frame, text="Target URL:").grid(row=1, column=0, sticky="w", pady=5)
        self.url_var = tk.StringVar(value="https://api-sandbox.doku.com/authorization/v1/access-token/b2b")
        ttk.Entry(input_frame, textvariable=self.url_var, width=50).grid(row=1, column=1, sticky="w", padx=5)

        # Private Key Selection
        ttk.Label(input_frame, text="Private Key:").grid(row=2, column=0, sticky="nw", pady=5)
        
        key_btn_frame = ttk.Frame(input_frame)
        key_btn_frame.grid(row=2, column=1, sticky="w", padx=5)
        
        ttk.Button(key_btn_frame, text="Load from File", command=self.load_private_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(key_btn_frame, text="Load from .env Path", command=self.load_private_key_from_env).pack(side=tk.LEFT, padx=5)
        ttk.Label(key_btn_frame, text=" or Paste below (PEM format)").pack(side=tk.LEFT)

        self.private_key_text = scrolledtext.ScrolledText(input_frame, height=8, width=60, font=("Consolas", 9))
        self.private_key_text.grid(row=3, column=0, columnspan=3, pady=5, sticky="ew")

        # Action Button
        self.generate_btn = ttk.Button(input_frame, text="Generate Token", command=self.start_generation)
        self.generate_btn.grid(row=4, column=0, columnspan=3, pady=10)

        # Status label for environment info
        self.status_label = ttk.Label(input_frame, text=f"Loaded from .env: Client ID = {self.env_client_id}", 
                                     foreground="blue")
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(5, 0))

        # --- Token Display Section ---
        self.token_frame = ttk.LabelFrame(main_frame, text="Generated Token", padding="10")
        
        # Token text dengan scrollbar horizontal
        token_container = ttk.Frame(self.token_frame)
        token_container.pack(fill=tk.X, expand=True)
        
        self.token_text = tk.Text(token_container, height=4, font=("Consolas", 9), wrap=tk.NONE)
        token_scrollbar_x = ttk.Scrollbar(token_container, orient=tk.HORIZONTAL, command=self.token_text.xview)
        self.token_text.configure(xscrollcommand=token_scrollbar_x.set)
        
        self.token_text.pack(side=tk.TOP, fill=tk.X, expand=True)
        token_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Frame untuk tombol copy token
        self.token_buttons_frame = ttk.Frame(self.token_frame)
        self.token_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Tombol copy token (akan ditampilkan hanya ketika ada token)
        self.copy_token_btn = ttk.Button(self.token_buttons_frame, text="📋 Copy Token", 
                                         command=self.copy_token_to_clipboard, state="disabled")
        self.copy_token_btn.pack(side=tk.LEFT)
        
        # Label status copy
        self.copy_status_label = ttk.Label(self.token_buttons_frame, text="", foreground="green")
        self.copy_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # --- Log Section ---
        self.log_frame = ttk.LabelFrame(main_frame, text="Logs (Request & Response)", padding="10")
        self.log_frame.pack(fill=tk.BOTH, expand=True)

        # Log Text Area (Selectable and Copyable)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, font=("Consolas", 10), state='normal')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Enable Ctrl+A to select all text
        self.log_text.bind("<Control-a>", self.select_all)
        self.log_text.bind("<Control-A>", self.select_all)
        
        # Frame untuk tombol log
        log_buttons_frame = ttk.Frame(self.log_frame)
        log_buttons_frame.pack(anchor="e", pady=(5, 0))
        
        # Add a clear button for logs
        ttk.Button(log_buttons_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        
        # Tombol copy log
        ttk.Button(log_buttons_frame, text="Copy Logs", command=self.copy_logs_to_clipboard).pack(side=tk.LEFT)

        # Load private key from .env path setelah semua widget dibuat
        self.load_initial_private_key()

    def load_environment_variables(self):
        """Load environment variables from .env file"""
        try:
            # Cari file .env di direktori proyek
            # Coba beberapa lokasi yang mungkin
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
                '.env'
            ]
            
            env_loaded = False
            for env_path in possible_paths:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    self.env_path = env_path
                    env_loaded = True
                    print(f"Loaded .env from: {env_path}")
                    break
            
            if not env_loaded:
                print("Warning: .env file not found in any expected location")
                self.env_path = None
            
            # Get client ID from .env
            self.env_client_id = os.getenv('DOKU_CLIENT_ID', '') or os.getenv('DOKU_SNAP_CLIENT_KEY', '')
            
            # Get private key path from .env
            self.env_private_key_path = os.getenv('DOKU_SNAP_PRIVATE_KEY_PATH', '')
            
            if not self.env_client_id:
                print("Warning: DOKU_CLIENT_ID or DOKU_SNAP_CLIENT_KEY not found in .env file")
            if not self.env_private_key_path:
                print("Warning: DOKU_SNAP_PRIVATE_KEY_PATH not found in .env file")
                
        except Exception as e:
            print(f"Error loading .env file: {e}")
            self.env_client_id = ""
            self.env_private_key_path = ""
            self.env_path = None

    def reload_from_env(self):
        """Reload client ID from .env file"""
        self.load_environment_variables()
        self.client_id_var.set(self.env_client_id)
        
        env_source = f" from {self.env_path}" if self.env_path else ""
        self.status_label.config(text=f"Reloaded from .env{env_source}: Client ID = {self.env_client_id}")
        self.log(f"Reloaded configuration from .env file")
        self.log(f"Client ID: {self.env_client_id}")
        self.log(f"Private Key Path: {self.env_private_key_path}")

    def load_initial_private_key(self):
        """Load private key from .env path on startup"""
        if self.env_private_key_path:
            try:
                # Convert relative path to absolute path
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                key_path = os.path.join(base_dir, self.env_private_key_path)
                
                if not os.path.exists(key_path):
                    # Try as absolute path
                    key_path = self.env_private_key_path
                    
                if os.path.exists(key_path):
                    with open(key_path, 'r') as f:
                        content = f.read()
                        self.private_key_text.delete("1.0", tk.END)
                        self.private_key_text.insert("1.0", content)
                        self.log(f"Auto-loaded private key from .env path: {key_path}")
                else:
                    self.log(f"Warning: Private key file not found at: {key_path}")
            except Exception as e:
                self.log(f"Error loading private key from .env path: {e}")

    def load_private_key_from_env(self):
        """Load private key from path specified in .env file"""
        if not self.env_private_key_path:
            messagebox.showwarning("No Path", "DOKU_SNAP_PRIVATE_KEY_PATH not found in .env file")
            return
        
        try:
            # Convert relative path to absolute path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            key_path = os.path.join(base_dir, self.env_private_key_path)
            
            if not os.path.exists(key_path):
                # Try absolute path
                key_path = self.env_private_key_path
                if not os.path.exists(key_path):
                    messagebox.showerror("File Not Found", 
                                        f"Private key file not found at:\n{key_path}")
                    return
            
            with open(key_path, 'r') as f:
                content = f.read()
                self.private_key_text.delete("1.0", tk.END)
                self.private_key_text.insert("1.0", content)
                self.log(f"Loaded private key from .env path: {key_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read private key file: {e}")

    def select_all(self, event):
        self.log_text.tag_add("sel", "1.0", "end")
        return "break"

    def load_private_key(self):
        filename = filedialog.askopenfilename(
            title="Select Private Key", 
            filetypes=[("PEM Files", "*.pem"), ("All Files", "*.*")],
            initialdir="keys"  # Open in keys directory by default
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                    self.private_key_text.delete("1.0", tk.END)
                    self.private_key_text.insert("1.0", content)
                    self.log(f"Loaded private key from file: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {e}")

    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def start_generation(self):
        # Run in thread to prevent freezing
        threading.Thread(target=self.generate_token, daemon=True).start()

    def copy_token_to_clipboard(self):
        """Copy token to clipboard"""
        token = self.token_text.get("1.0", tk.END).strip()
        if token:
            try:
                pyperclip.copy(token)
                self.copy_status_label.config(text="Token copied to clipboard!")
                # Reset status label setelah 2 detik
                self.root.after(2000, lambda: self.copy_status_label.config(text=""))
            except Exception as e:
                messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {e}")

    def copy_logs_to_clipboard(self):
        """Copy logs to clipboard"""
        logs = self.log_text.get("1.0", tk.END).strip()
        if logs:
            try:
                pyperclip.copy(logs)
                messagebox.showinfo("Success", "Logs copied to clipboard!")
            except Exception as e:
                messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {e}")

    def display_token(self, token):
        """Display token in the token frame and enable copy button"""
        # Clear token text dan insert token baru
        self.token_text.delete("1.0", tk.END)
        self.token_text.insert("1.0", token)
        
        # Enable tombol copy
        self.copy_token_btn.config(state="normal")
        
        # Reset status label
        self.copy_status_label.config(text="")
        
        # Tampilkan frame token jika belum ditampilkan
        if not self.token_frame.winfo_ismapped():
            self.token_frame.pack(fill=tk.X, pady=(0, 10), before=self.log_frame)

    def hide_token_frame(self):
        """Hide token frame"""
        if self.token_frame.winfo_ismapped():
            self.token_frame.pack_forget()
            self.copy_token_btn.config(state="disabled")

    def generate_token(self):
        client_id = self.client_id_var.get().strip()
        url = self.url_var.get().strip()
        private_key_pem = self.private_key_text.get("1.0", tk.END).strip()

        if not client_id or not private_key_pem:
            self.root.after(0, lambda: messagebox.showwarning("Missing Input", "Please provide Client ID and Private Key."))
            return

        self.root.after(0, lambda: self.generate_btn.configure(state="disabled"))
        self.root.after(0, lambda: self.log("-" * 50))
        self.root.after(0, lambda: self.log(f"Starting request to {url}..."))
        self.root.after(0, lambda: self.log(f"Using Client ID: {client_id}"))
        
        # Sembunyikan frame token di awal proses
        self.root.after(0, self.hide_token_frame)

        try:
            # 1. Generate Timestamp (ISO8601 UTC+0)
            # Format: YYYY-MM-DDTHH:mm:ssZ
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

            # 2. Create String to Sign
            # stringToSign = client_ID + "|" + X-TIMESTAMP
            string_to_sign = f"{client_id}|{timestamp}"
            
            self.root.after(0, lambda: self.log(f"Timestamp: {timestamp}"))
            self.root.after(0, lambda: self.log(f"String to Sign: {string_to_sign}"))

            # 3. Sign the string
            try:
                private_key = serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None
                )
            except ValueError as e:
                self.root.after(0, lambda: self.log(f"Error: Invalid Private Key format. {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Private Key Error", "Invalid Private Key format. Please check your private key."))
                return

            signature = private_key.sign(
                string_to_sign.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # 4. Base64 Encode Signature
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            # 5. Prepare Headers and Body
            headers = {
                "X-CLIENT-KEY": client_id,
                "X-TIMESTAMP": timestamp,
                "X-SIGNATURE": signature_b64,
                "Content-Type": "application/json"
            }
            
            body = {
                "grantType": "client_credentials"
            }

            self.root.after(0, lambda: self.log("\n--- Request Headers ---"))
            self.root.after(0, lambda: self.log(json.dumps(headers, indent=2)))
            self.root.after(0, lambda: self.log("\n--- Request Body ---"))
            self.root.after(0, lambda: self.log(json.dumps(body, indent=2)))

            # 6. Send Request
            response = requests.post(url, json=body, headers=headers, timeout=30)

            # 7. Handle Response
            self.root.after(0, lambda: self.log(f"\n--- Response Status: {response.status_code} ---"))
            try:
                resp_json = response.json()
                self.root.after(0, lambda: self.log(json.dumps(resp_json, indent=2)))
                
                # Cek jika response sukses (200 OK dan responseCode 2007300)
                if response.status_code == 200 and resp_json.get('responseCode') == '2007300':
                    access_token = resp_json.get('accessToken', '')
                    if access_token:
                        # Tampilkan token di area khusus
                        self.root.after(0, lambda: self.display_token(access_token))
                        self.root.after(0, lambda: self.log("\n✓ Token successfully generated and displayed above!"))
                        
                        # Log token info
                        token_type = resp_json.get('tokenType', 'Bearer')
                        expires_in = resp_json.get('expiresIn', 0)
                        self.root.after(0, lambda: self.log(f"Token Type: {token_type}"))
                        self.root.after(0, lambda: self.log(f"Expires in: {expires_in} seconds"))
                    else:
                        self.root.after(0, lambda: self.log("\n⚠ Token generated but accessToken field is empty!"))
                else:
                    # Sembunyikan frame token jika response tidak sukses
                    self.root.after(0, self.hide_token_frame)
                    response_message = resp_json.get('responseMessage', 'Unknown error')
                    self.root.after(0, lambda: self.log(f"\n✗ Request failed: {response_message}"))
                    
            except json.JSONDecodeError:
                self.root.after(0, lambda: self.log(f"Response text: {response.text}"))
                # Sembunyikan frame token jika response error
                self.root.after(0, self.hide_token_frame)
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error parsing response: {str(e)}"))
                self.root.after(0, self.hide_token_frame)

        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: self.log(f"\nNetwork error occurred: {str(e)}"))
            self.root.after(0, self.hide_token_frame)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"\nError occurred: {str(e)}"))
            self.root.after(0, self.hide_token_frame)
        finally:
            self.root.after(0, lambda: self.generate_btn.configure(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = DokuB2BTesterApp(root)
    root.mainloop()