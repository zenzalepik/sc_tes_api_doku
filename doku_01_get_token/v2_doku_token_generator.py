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

class DokuTokenGenerator:
    """Modular Token Generator for DOKU B2B API"""
    
    def __init__(self, parent_frame, on_token_generated=None):
        """
        Initialize the token generator widget
        
        Args:
            parent_frame: Tkinter frame to embed this widget
            on_token_generated: Callback function when token is generated
                               Receives (token: str, token_info: dict)
        """
        self.parent_frame = parent_frame
        self.on_token_generated = on_token_generated
        
        # Initialize variables
        self.generated_token = ""
        self.token_info = {}
        
        # Load environment variables
        self.load_environment_variables()
        
        # Create the widget
        self.create_widgets()
        
        # Load private key from .env path
        self.load_initial_private_key()
    
    def load_environment_variables(self):
        """Load environment variables from .env file"""
        try:
            # Cari file .env di beberapa lokasi yang mungkin
            possible_paths = [
                '.env',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
            ]
            
            env_loaded = False
            for env_path in possible_paths:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    self.env_path = env_path
                    env_loaded = True
                    print(f"[Token Generator] Loaded .env from: {env_path}")
                    break
            
            if not env_loaded:
                print("[Token Generator] Warning: .env file not found")
                self.env_path = None
            
            # Get client ID from .env
            self.env_client_id = os.getenv('DOKU_CLIENT_ID', '') or os.getenv('DOKU_SNAP_CLIENT_KEY', '')
            
            # Get private key path from .env
            self.env_private_key_path = os.getenv('DOKU_SNAP_PRIVATE_KEY_PATH', '')
            
        except Exception as e:
            print(f"[Token Generator] Error loading .env: {e}")
            self.env_client_id = ""
            self.env_private_key_path = ""
            self.env_path = None
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        self.main_frame = ttk.LabelFrame(self.parent_frame, text="Token Generator", padding="10")
        self.main_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Top button frame
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get Token button
        self.get_token_btn = ttk.Button(
            top_frame, 
            text="🔑 Get Token", 
            command=self.start_generation,
            width=15
        )
        self.get_token_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reload config button
        self.reload_btn = ttk.Button(
            top_frame,
            text="🔄 Reload Config",
            command=self.reload_config,
            width=15
        )
        self.reload_btn.pack(side=tk.LEFT)
        
        # Status label
        self.status_label = ttk.Label(
            top_frame, 
            text="Ready", 
            foreground="blue"
        )
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Token display section (initially hidden)
        self.token_display_frame = ttk.Frame(self.main_frame)
        
        # Token label
        self.token_label = ttk.Label(
            self.token_display_frame,
            text="Generated Token:",
            font=("Segoe UI", 10, "bold")
        )
        self.token_label.pack(anchor="w", pady=(0, 5))
        
        # Token text with scrollbar
        token_text_frame = ttk.Frame(self.token_display_frame)
        token_text_frame.pack(fill=tk.X)
        
        self.token_text = tk.Text(
            token_text_frame, 
            height=3, 
            font=("Consolas", 9), 
            wrap=tk.NONE,
            state='disabled'
        )
        token_scrollbar_x = ttk.Scrollbar(token_text_frame, orient=tk.HORIZONTAL, command=self.token_text.xview)
        self.token_text.configure(xscrollcommand=token_scrollbar_x.set)
        
        self.token_text.pack(side=tk.TOP, fill=tk.X, expand=True)
        token_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Token action buttons
        token_actions_frame = ttk.Frame(self.token_display_frame)
        token_actions_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.copy_token_btn = ttk.Button(
            token_actions_frame,
            text="📋 Copy Token",
            command=self.copy_token,
            state='disabled',
            width=15
        )
        self.copy_token_btn.pack(side=tk.LEFT)
        
        self.clear_token_btn = ttk.Button(
            token_actions_frame,
            text="🗑️ Clear",
            command=self.clear_token,
            width=10
        )
        self.clear_token_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        self.copy_status_label = ttk.Label(
            token_actions_frame,
            text="",
            foreground="green"
        )
        self.copy_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Token info frame
        self.token_info_frame = ttk.LabelFrame(self.token_display_frame, text="Token Info", padding="5")
        self.token_info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.token_info_text = tk.Text(
            self.token_info_frame,
            height=4,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state='disabled'
        )
        self.token_info_text.pack(fill=tk.X)
    
    def load_initial_private_key(self):
        """Load private key from .env path on startup"""
        if hasattr(self, 'status_label') and self.env_private_key_path:
            try:
                # Convert relative path to absolute path
                base_dir = os.path.dirname(os.path.abspath(__file__))
                key_path = os.path.join(base_dir, self.env_private_key_path)
                
                if not os.path.exists(key_path):
                    # Try parent directory
                    key_path = os.path.join(os.path.dirname(base_dir), self.env_private_key_path)
                
                if not os.path.exists(key_path):
                    # Try as absolute path
                    key_path = self.env_private_key_path
                    
                if os.path.exists(key_path):
                    self.private_key_path = key_path
                    self.set_status(f"Config loaded: {os.path.basename(key_path)}", "blue")
                else:
                    self.set_status("Private key not found", "orange")
                    
            except Exception as e:
                self.set_status(f"Config error: {str(e)[:30]}...", "red")
    
    def reload_config(self):
        """Reload configuration from .env"""
        self.load_environment_variables()
        self.load_initial_private_key()
    
    def set_status(self, message, color="blue"):
        """Set status label"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message, foreground=color)
    
    def start_generation(self):
        """Start token generation in a separate thread"""
        threading.Thread(target=self.generate_token, daemon=True).start()
    
    def generate_token(self):
        """Generate token using DOKU B2B API"""
        # Update UI in main thread
        self.parent_frame.after(0, lambda: self.get_token_btn.configure(state="disabled"))
        self.parent_frame.after(0, lambda: self.set_status("Generating token...", "orange"))
        
        try:
            # Load private key
            if not hasattr(self, 'private_key_path') or not os.path.exists(self.private_key_path):
                self.parent_frame.after(0, lambda: messagebox.showerror(
                    "Error", 
                    "Private key not found. Please check DOKU_SNAP_PRIVATE_KEY_PATH in .env"
                ))
                return
            
            with open(self.private_key_path, 'r') as f:
                private_key_pem = f.read().strip()
            
            client_id = self.env_client_id
            url = "https://api-sandbox.doku.com/authorization/v1/access-token/b2b"
            
            if not client_id:
                self.parent_frame.after(0, lambda: messagebox.showerror(
                    "Error",
                    "Client ID not found. Please check DOKU_CLIENT_ID or DOKU_SNAP_CLIENT_KEY in .env"
                ))
                return
            
            # 1. Generate Timestamp
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # 2. Create String to Sign
            string_to_sign = f"{client_id}|{timestamp}"
            
            # 3. Sign the string
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
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
            
            # Log to console
            print(f"[Token Generator] Generating token for client: {client_id}")
            print(f"[Token Generator] Timestamp: {timestamp}")
            
            # 6. Send Request
            response = requests.post(url, json=body, headers=headers, timeout=30)
            
            # 7. Handle Response
            if response.status_code == 200:
                resp_json = response.json()
                
                if resp_json.get('responseCode') == '2007300':
                    access_token = resp_json.get('accessToken', '')
                    
                    if access_token:
                        self.generated_token = access_token
                        self.token_info = {
                            'tokenType': resp_json.get('tokenType', 'Bearer'),
                            'expiresIn': resp_json.get('expiresIn', 0),
                            'responseMessage': resp_json.get('responseMessage', ''),
                            'timestamp': timestamp
                        }
                        
                        # Update UI in main thread
                        self.parent_frame.after(0, lambda: self.display_token(access_token, resp_json))
                        self.parent_frame.after(0, lambda: self.set_status("Token generated successfully!", "green"))
                        
                        # Log to console
                        print(f"[Token Generator] Token generated successfully!")
                        print(f"[Token Generator] Token Type: {self.token_info['tokenType']}")
                        print(f"[Token Generator] Expires in: {self.token_info['expiresIn']} seconds")
                        
                        # Call callback if provided
                        if self.on_token_generated:
                            self.parent_frame.after(0, lambda: self.on_token_generated(access_token, self.token_info))
                        
                        return
                
                # If we reach here, token generation failed
                error_msg = resp_json.get('responseMessage', 'Unknown error')
                self.parent_frame.after(0, lambda: self.set_status(f"Failed: {error_msg}", "red"))
                self.parent_frame.after(0, lambda: messagebox.showerror(
                    "Token Generation Failed",
                    f"API Error: {error_msg}"
                ))
                
            else:
                error_msg = f"HTTP {response.status_code}"
                self.parent_frame.after(0, lambda: self.set_status(f"Failed: {error_msg}", "red"))
                self.parent_frame.after(0, lambda: messagebox.showerror(
                    "Token Generation Failed",
                    f"HTTP Error: {response.status_code}\n{response.text}"
                ))
                
        except Exception as e:
            error_msg = str(e)
            self.parent_frame.after(0, lambda: self.set_status(f"Error: {error_msg[:30]}...", "red"))
            self.parent_frame.after(0, lambda: messagebox.showerror(
                "Token Generation Error",
                f"An error occurred:\n{error_msg}"
            ))
            print(f"[Token Generator] Error: {error_msg}")
            
        finally:
            self.parent_frame.after(0, lambda: self.get_token_btn.configure(state="normal"))
    
    def display_token(self, token, token_info):
        """Display the generated token"""
        # Show token display frame if hidden
        if not self.token_display_frame.winfo_ismapped():
            self.token_display_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Enable token text and insert token
        self.token_text.config(state='normal')
        self.token_text.delete("1.0", tk.END)
        self.token_text.insert("1.0", token)
        self.token_text.config(state='disabled')
        
        # Enable copy button
        self.copy_token_btn.config(state='normal')
        
        # Update token info
        info_text = f"Type: {token_info.get('tokenType', 'Bearer')}\n"
        info_text += f"Expires in: {token_info.get('expiresIn', 0)} seconds\n"
        info_text += f"Status: {token_info.get('responseMessage', 'Success')}\n"
        info_text += f"Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.token_info_text.config(state='normal')
        self.token_info_text.delete("1.0", tk.END)
        self.token_info_text.insert("1.0", info_text)
        self.token_info_text.config(state='disabled')
    
    def copy_token(self):
        """Copy token to clipboard"""
        if self.generated_token:
            try:
                pyperclip.copy(self.generated_token)
                self.copy_status_label.config(text="Copied!", foreground="green")
                
                # Reset status after 2 seconds
                self.parent_frame.after(2000, lambda: self.copy_status_label.config(text=""))
                
            except Exception as e:
                messagebox.showerror("Copy Error", f"Failed to copy token: {e}")
    
    def clear_token(self):
        """Clear the displayed token"""
        self.generated_token = ""
        self.token_info = {}
        
        # Clear token text
        self.token_text.config(state='normal')
        self.token_text.delete("1.0", tk.END)
        self.token_text.config(state='disabled')
        
        # Clear token info
        self.token_info_text.config(state='normal')
        self.token_info_text.delete("1.0", tk.END)
        self.token_info_text.config(state='disabled')
        
        # Disable copy button
        self.copy_token_btn.config(state='disabled')
        
        # Hide token display frame
        if self.token_display_frame.winfo_ismapped():
            self.token_display_frame.pack_forget()
        
        self.set_status("Ready", "blue")
    
    def get_token(self):
        """Get the current generated token"""
        return self.generated_token
    
    def get_token_info(self):
        """Get token information"""
        return self.token_info.copy()