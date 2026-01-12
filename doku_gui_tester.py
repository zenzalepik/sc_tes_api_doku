import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import threading
import json
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
import qrcode
from PIL import Image, ImageTk
from io import BytesIO

# Import core classes
from doku_api_tester import (
    DokuSnapConfig, 
    DokuSnapClient, 
    DokuSnapQrisApi, 
    DokuSnapEWalletApi,
    DokuSnapDirectDebitApi,
    DokuSnapKkiApi,
    DokuSnapVirtualAccountApi,
    Environment
)

# Load env
load_dotenv()

class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

class DokuGuiTester:
    def __init__(self, root):
        self.root = root
        self.root.title("DOKU API Tester (GUI)")
        self.root.geometry("1200x850")
        
        self.qris_api = None
        self.ewallet_api = None
        self.dd_api = None
        self.kki_api = None
        self.va_api = None
        self.init_api()
        
        self.create_widgets()
        self.setup_logging()

    def init_api(self):
        try:
            # Load credentials
            client_id = os.getenv("DOKU_SNAP_CLIENT_KEY")
            client_secret = os.getenv("DOKU_SNAP_CLIENT_SECRET")
            private_key_path = os.getenv("DOKU_SNAP_PRIVATE_KEY_PATH", "")
            partner_id = os.getenv("DOKU_SNAP_CLIENT_KEY") # Usually same as Client ID
            merchant_id = os.getenv("DOKU_QRIS_MERCHANT_ID")
            terminal_id = os.getenv("DOKU_QRIS_TERMINAL_ID", "T001")

            private_key_pem = None
            if private_key_path and os.path.exists(private_key_path):
                with open(private_key_path, "r", encoding="utf-8") as f:
                    private_key_pem = f.read()
            
            if not all([client_id, client_secret, private_key_pem, merchant_id]):
                logging.warning("Config Warning: Beberapa konfigurasi (Keys/ID) tidak ditemukan di .env.")
                messagebox.showwarning("Config Warning", "Beberapa konfigurasi (Keys/ID) tidak ditemukan di .env.\nFitur mungkin tidak berjalan.")
                return

            logging.info(f"Initializing API with Client Key: {client_id[:4]}****, Merchant ID: {merchant_id}")

            config = DokuSnapConfig(
                client_key=client_id,
                client_secret=client_secret,
                private_key_pem=private_key_pem,
                environment=Environment.SANDBOX
            )
            client = DokuSnapClient(config)
            
            # Init APIs
            self.qris_api = DokuSnapQrisApi(client, partner_id, merchant_id, terminal_id)
            self.ewallet_api = DokuSnapEWalletApi(client, partner_id, merchant_id)
            self.dd_api = DokuSnapDirectDebitApi(client, partner_id, merchant_id)
            self.kki_api = DokuSnapKkiApi(client, partner_id, merchant_id)
            self.va_api = DokuSnapVirtualAccountApi(client, partner_id, merchant_id)
            
            logging.info("API Initialized Successfully")
            
        except Exception as e:
            logging.error(f"Init Error: {str(e)}", exc_info=True)
            messagebox.showerror("Init Error", f"Gagal inisialisasi API: {str(e)}")

    def create_widgets(self):
        # Main Layout
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # VA Tab (SNAP)
        self.create_va_tab(notebook)
        # QRIS Tab
        self.create_qris_tab(notebook)
        # E-Wallet Tab
        self.create_ewallet_tab(notebook)
        # Direct Debit Tab
        self.create_dd_tab(notebook)
        # KKI Tab
        self.create_kki_tab(notebook)
        
        # Logs Area
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_qris_tab(self, notebook):
        qris_frame = ttk.Frame(notebook, padding="10")
        notebook.add(qris_frame, text="QRIS MPM")

        paned = ttk.PanedWindow(qris_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=1)

        # --- Generate QRIS ---
        gen_group = ttk.LabelFrame(left_frame, text="1. Generate QRIS", padding="5")
        gen_group.pack(fill=tk.X, pady=5)
        
        # Row 0: Amount
        ttk.Label(gen_group, text="Amount (IDR):").grid(row=0, column=0, sticky="w", pady=2)
        self.qris_amount_entry = ttk.Entry(gen_group)
        self.qris_amount_entry.insert(0, "10000")
        self.qris_amount_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Row 1: Fee Config
        ttk.Label(gen_group, text="Fee Type:").grid(row=1, column=0, sticky="w", pady=2)
        self.qris_fee_type = ttk.Entry(gen_group, width=10)
        env_fee_type = os.getenv("DOKU_QRIS_FEE_TYPE", "")
        self.qris_fee_type.insert(0, env_fee_type)
        self.qris_fee_type.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(gen_group, text="Fee Amount:").grid(row=2, column=0, sticky="w", pady=2)
        self.qris_fee_amount = ttk.Entry(gen_group)
        env_fee_amount = os.getenv("DOKU_QRIS_FEE_AMOUNT", "")
        self.qris_fee_amount.insert(0, env_fee_amount)
        self.qris_fee_amount.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Button(gen_group, text="Generate", command=self.on_generate_qris).grid(row=3, column=1, pady=5)

        # --- Actions Group (Check, Refund, Cancel) ---
        act_group = ttk.LabelFrame(left_frame, text="2. Actions (By Ref No)", padding="5")
        act_group.pack(fill=tk.X, pady=5)

        ttk.Label(act_group, text="Partner Ref No:").grid(row=0, column=0, sticky="w")
        self.qris_ref_no_entry = ttk.Entry(act_group)
        self.qris_ref_no_entry.grid(row=0, column=1, sticky="ew", padx=5)

        btn_frame = ttk.Frame(act_group)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=5)
        
        ttk.Button(btn_frame, text="Check Status", command=self.on_check_status_qris).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel_qris).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Refund", command=self.on_refund_qris).pack(side=tk.LEFT, padx=2)

        # --- Decode ---
        decode_group = ttk.LabelFrame(left_frame, text="3. Decode QR Content", padding="5")
        decode_group.pack(fill=tk.X, pady=5)
        
        self.qr_content_entry = ttk.Entry(decode_group)
        self.qr_content_entry.grid(row=0, column=0, sticky="ew", padx=5)
        ttk.Button(decode_group, text="Decode", command=self.on_decode_qris).grid(row=0, column=1)

        # --- Right Side: Display ---
        self.qr_image_label = ttk.Label(right_frame, text="QR Image will appear here")
        self.qr_image_label.pack(pady=10)

        ttk.Label(right_frame, text="Result JSON:").pack(anchor="w")
        self.qris_result_text = scrolledtext.ScrolledText(right_frame, height=15)
        self.qris_result_text.pack(fill=tk.BOTH, expand=True)

    def create_ewallet_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="E-Wallet")
        
        # Form
        form_frame = ttk.LabelFrame(frame, text="Payment Details", padding="5")
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Channel:").grid(row=0, column=0, sticky="w")
        self.ewallet_channel = ttk.Combobox(form_frame, values=["OVO", "SHOPEEPAY", "DANA", "LINKAJA"])
        self.ewallet_channel.set("OVO")
        self.ewallet_channel.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Amount:").grid(row=1, column=0, sticky="w")
        self.ewallet_amount = ttk.Entry(form_frame)
        self.ewallet_amount.insert(0, "10000")
        self.ewallet_amount.grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Customer No (Phone):").grid(row=2, column=0, sticky="w")
        self.ewallet_cust_no = ttk.Entry(form_frame)
        self.ewallet_cust_no.insert(0, "081234567890")
        self.ewallet_cust_no.grid(row=2, column=1, sticky="ew", padx=5)
        
        ttk.Button(form_frame, text="Pay E-Wallet", command=self.on_pay_ewallet).grid(row=3, column=1, pady=10)
        
        # Result
        ttk.Label(frame, text="Result JSON:").pack(anchor="w")
        self.ewallet_result_text = scrolledtext.ScrolledText(frame, height=15)
        self.ewallet_result_text.pack(fill=tk.BOTH, expand=True)

    def create_dd_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Direct Debit")
        
        form_frame = ttk.LabelFrame(frame, text="Payment Details", padding="5")
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Amount:").grid(row=0, column=0, sticky="w")
        self.dd_amount = ttk.Entry(form_frame)
        self.dd_amount.insert(0, "10000")
        self.dd_amount.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Customer No:").grid(row=1, column=0, sticky="w")
        self.dd_cust_no = ttk.Entry(form_frame)
        self.dd_cust_no.insert(0, "081234567890")
        self.dd_cust_no.grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Binding ID (Token):").grid(row=2, column=0, sticky="w")
        self.dd_binding_id = ttk.Entry(form_frame)
        self.dd_binding_id.insert(0, "BIND-TOKEN-SAMPLE")
        self.dd_binding_id.grid(row=2, column=1, sticky="ew", padx=5)
        
        ttk.Button(form_frame, text="Pay Direct Debit", command=self.on_pay_dd).grid(row=3, column=1, pady=10)
        
        ttk.Label(frame, text="Result JSON:").pack(anchor="w")
        self.dd_result_text = scrolledtext.ScrolledText(frame, height=15)
        self.dd_result_text.pack(fill=tk.BOTH, expand=True)

    def create_kki_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="KKI CPTS (Credit Card)")
        
        form_frame = ttk.LabelFrame(frame, text="Payment Details", padding="5")
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Amount:").grid(row=0, column=0, sticky="w")
        self.kki_amount = ttk.Entry(form_frame)
        self.kki_amount.insert(0, "10000")
        self.kki_amount.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Token ID (Card Token):").grid(row=1, column=0, sticky="w")
        self.kki_token_id = ttk.Entry(form_frame)
        self.kki_token_id.insert(0, "TOKEN-CC-SAMPLE")
        self.kki_token_id.grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Button(form_frame, text="Pay Credit Card", command=self.on_pay_kki).grid(row=2, column=1, pady=10)
        
        ttk.Label(frame, text="Result JSON:").pack(anchor="w")
        self.kki_result_text = scrolledtext.ScrolledText(frame, height=15)
        self.kki_result_text.pack(fill=tk.BOTH, expand=True)

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def display_result(self, data, text_widget=None):
        widget = text_widget or self.result_text
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, json.dumps(data, indent=2))

    def run_async(self, func):
        threading.Thread(target=func, daemon=True).start()

    # --- Handlers QRIS ---

    def on_generate_qris(self):
        amount = int(self.qris_amount_entry.get())
        ref_no = f"TRX-{uuid.uuid4().hex[:8].upper()}"
        
        def task():
            if not self.qris_api: return
            logging.info(f"Generating QRIS for {ref_no}...")
            
            # Config optional
            postal_code = os.getenv("DOKU_QRIS_POSTAL_CODE", "") or None
            
            # Read from GUI Inputs
            fee_type = self.qris_fee_type.get().strip() or None
            fee_amount = self.qris_fee_amount.get().strip() or None
            
            logging.info(f"Fee Config -> Type: {fee_type}, Amount: {fee_amount}")

            res = self.qris_api.generate(
                partner_reference_no=ref_no, 
                amount_idr=amount,
                postal_code=postal_code,
                fee_type=fee_type,
                fee_amount=fee_amount
            )
            
            self.root.after(0, lambda: self.display_result(res, self.qris_result_text))
            
            if res.get("status_code") == 200:
                data = res.get("data", {})
                qr_content = data.get("qrContent")
                self.root.after(0, lambda: self.qris_ref_no_entry.delete(0, tk.END))
                self.root.after(0, lambda: self.qris_ref_no_entry.insert(0, ref_no))
                self.root.after(0, lambda: self.qr_content_entry.delete(0, tk.END))
                self.root.after(0, lambda: self.qr_content_entry.insert(0, qr_content))
                
                if qr_content:
                    qr = qrcode.QRCode(box_size=10, border=4)
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img = img.resize((250, 250))
                    photo = ImageTk.PhotoImage(img)
                    def show_img():
                        self.qr_image_label.configure(image=photo, text="")
                        self.qr_image_label.image = photo
                    self.root.after(0, show_img)

        self.run_async(task)

    def on_check_status_qris(self):
        ref_no = self.qris_ref_no_entry.get()
        if not ref_no: return
        def task():
            logging.info(f"Checking status for {ref_no}...")
            res = self.qris_api.check_status(ref_no)
            self.root.after(0, lambda: self.display_result(res, self.qris_result_text))
        self.run_async(task)

    def on_cancel_qris(self):
        ref_no = self.qris_ref_no_entry.get()
        if not ref_no: return
        def task():
            logging.info(f"Cancelling {ref_no}...")
            res = self.qris_api.cancel(ref_no)
            self.root.after(0, lambda: self.display_result(res, self.qris_result_text))
        self.run_async(task)

    def on_refund_qris(self):
        ref_no = self.qris_ref_no_entry.get()
        amount = self.qris_amount_entry.get()
        if not ref_no: return
        def task():
            refund_no = f"REF-{ref_no}"
            logging.info(f"Refunding {ref_no}...")
            res = self.qris_api.refund(ref_no, refund_no, int(amount))
            self.root.after(0, lambda: self.display_result(res, self.qris_result_text))
        self.run_async(task)

    def on_decode_qris(self):
        content = self.qr_content_entry.get()
        if not content: return
        def task():
            logging.info("Decoding QR...")
            res = self.qris_api.decode(content)
            self.root.after(0, lambda: self.display_result(res, self.qris_result_text))
        self.run_async(task)

    def on_mock(self):
        ref_no = self.qris_ref_no_entry.get() or "SAMPLE-REF"
        amount = int(self.qris_amount_entry.get() or 10000)
        data = self.qris_api.generate_mock_notification(ref_no, amount)
        self.display_result(data, self.qris_result_text)
        logging.info("Generated Mock Notification Payload")

    # --- Handlers Others ---

    def on_pay_ewallet(self):
        amount = int(self.ewallet_amount.get())
        cust_no = self.ewallet_cust_no.get()
        channel = self.ewallet_channel.get()
        ref_no = f"INV-EW-{uuid.uuid4().hex[:8].upper()}"
        
        def task():
            if not self.ewallet_api: return
            logging.info(f"E-Wallet Payment {channel} for {ref_no}...")
            res = self.ewallet_api.payment(ref_no, amount, cust_no, channel)
            self.root.after(0, lambda: self.display_result(res, self.ewallet_result_text))
        self.run_async(task)

    def on_pay_dd(self):
        amount = int(self.dd_amount.get())
        cust_no = self.dd_cust_no.get()
        binding_id = self.dd_binding_id.get()
        ref_no = f"INV-DD-{uuid.uuid4().hex[:8].upper()}"
        
        def task():
            if not self.dd_api: return
            logging.info(f"Direct Debit Payment for {ref_no}...")
            res = self.dd_api.payment(ref_no, amount, cust_no, binding_id)
            self.root.after(0, lambda: self.display_result(res, self.dd_result_text))
        self.run_async(task)

    def on_pay_kki(self):
        amount = int(self.kki_amount.get())
        token_id = self.kki_token_id.get()
        ref_no = f"INV-KKI-{uuid.uuid4().hex[:8].upper()}"
        
        def task():
            if not self.kki_api: return
            logging.info(f"Credit Card Payment for {ref_no}...")
            res = self.kki_api.payment(ref_no, amount, token_id)
            self.root.after(0, lambda: self.display_result(res, self.kki_result_text))
        self.run_async(task)

    def create_va_tab(self, notebook):
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Virtual Account (SNAP)")
        
        form_frame = ttk.LabelFrame(frame, text="Payment Details", padding="5")
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Amount:").grid(row=0, column=0, sticky="w")
        self.va_amount = ttk.Entry(form_frame)
        self.va_amount.insert(0, "10000")
        self.va_amount.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Customer No:").grid(row=1, column=0, sticky="w")
        self.va_cust_no = ttk.Entry(form_frame)
        self.va_cust_no.insert(0, "081234567890")
        self.va_cust_no.grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(form_frame, text="Customer Name:").grid(row=2, column=0, sticky="w")
        self.va_cust_name = ttk.Entry(form_frame)
        self.va_cust_name.insert(0, "Test Customer")
        self.va_cust_name.grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Button(form_frame, text="Create VA", command=self.on_create_va).grid(row=3, column=1, pady=10)
        
        ttk.Label(frame, text="Result JSON:").pack(anchor="w")
        self.va_result_text = scrolledtext.ScrolledText(frame, height=15)
        self.va_result_text.pack(fill=tk.BOTH, expand=True)

    def on_create_va(self):
        amount = int(self.va_amount.get())
        cust_no = self.va_cust_no.get()
        cust_name = self.va_cust_name.get()
        trx_id = f"TRX-VA-{uuid.uuid4().hex[:8].upper()}"
        
        def task():
            if not self.va_api: return
            logging.info(f"Creating SNAP VA for {trx_id}...")
            
            # Construct Virtual Account No (Partner Service ID + Customer No)
            # Usually Partner Service ID is 8 digits. We'll use client key prefix or env if available.
            partner_service_id = self.va_api.partner_id[:8].replace("-","") 
            # Fallback logic if partner_id is not suitable, user might need to set it properly
            # For testing, we assume partner_id (Client Key) can be used or we hardcode a mock one if needed.
            # But standard SNAP B2B, partnerServiceId is usually assigned.
            
            # Let's try to use what we have
            virtual_account_no = f"{partner_service_id}{cust_no}"

            res = self.va_api.create_va(
                partner_service_id=partner_service_id,
                customer_no=cust_no,
                virtual_account_no=virtual_account_no,
                amount_idr=amount,
                trx_id=trx_id,
                customer_name=cust_name
            )
            self.root.after(0, lambda: self.display_result(res, self.va_result_text))
        self.run_async(task)

if __name__ == "__main__":
    root = tk.Tk()
    app = DokuGuiTester(root)
    root.mainloop()
