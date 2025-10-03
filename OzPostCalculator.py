import csv
import json
import os
import threading
from datetime import datetime
import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog

# ----------------------------
# App Constants / Defaults
# ----------------------------
APP_TITLE = "Postage Calculator"
THEME = "cyborg"  # Dark theme per your preference
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".auspost_postage_calculator.json")

# Default API URL (can be changed in Settings tab)
DEFAULT_API_URL = "https://digitalapi.auspost.com.au/postage/parcel/domestic"

# Service options grouped logically
SERVICE_OPTIONS = {
    "AUS_PARCEL_EXPRESS": [
        "AUS_PARCEL_EXPRESS_SATCHEL_SMALL",
        "AUS_PARCEL_EXPRESS_PACKAGE_SMALL",
        "AUS_PARCEL_EXPRESS_SATCHEL_500G"
    ],
    "AUS_PARCEL_REGULAR": [
        "AUS_PARCEL_REGULAR_SATCHEL_SMALL",
        "AUS_PARCEL_REGULAR_PACKAGE_SMALL",
        "AUS_PARCEL_REGULAR_SATCHEL_500G"
    ]
}

# CSV Export Header (consistent ordering)
CSV_FIELDS = [
    "timestamp", "from_postcode", "to_postcode", "length_cm", "width_cm",
    "height_cm", "weight_kg", "service_code", "suboption_code", "cost", "eta"
]


# ----------------------------
# Utility: Config Load/Save
# ----------------------------
def load_config():
    cfg = {
        "api_key": "",
        "api_url": DEFAULT_API_URL,
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                file_cfg = json.load(fh)
                cfg.update({k: file_cfg.get(k, v) for k, v in cfg.items()})
        except Exception:
            # Keep defaults if file is corrupted
            pass
    return cfg


def save_config(api_key: str, api_url: str):
    cfg = {"api_key": api_key.strip(), "api_url": api_url.strip()}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        return True, "Settings saved."
    except Exception as e:
        return False, f"Failed to save settings: {e}"


# ----------------------------
# Main Application
# ----------------------------
class PostageCalculatorApp:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title(APP_TITLE)
        self.history = []
        self.cfg = load_config()
        self._api_lock = threading.Lock()

        # ------------- Main Layout -------------
        self._build_ui()

        # ------------- Key Bindings -------------
        self.root.bind("<Return>", lambda e: self.calculate_postage())
        self.root.bind("<Control-s>", lambda e: self.export_csv())

    # ----------------------------------------
    # UI Construction
    # ----------------------------------------
    def _build_ui(self):
        # Notebook Tabs
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, padx=12, pady=12)

        self.tab_calc = ttk.Frame(self.notebook)
        self.tab_hist = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_calc, text="Calculator")
        self.notebook.add(self.tab_hist, text="History & Export")
        self.notebook.add(self.tab_settings, text="Settings")

        # Status Bar
        self.status_var = ttk.StringVar(value="Ready.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor=W, bootstyle=SECONDARY)
        status_bar.pack(fill=X, padx=12, pady=(0, 12))

        # Build tabs
        self._build_calculator_tab()
        self._build_history_tab()
        self._build_settings_tab()

    def _build_calculator_tab(self):
        # Horizontal Paned Layout: Left (Form), Right (Result/Preview)
        paned = ttk.Panedwindow(self.tab_calc, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        # --- Left: Form ---
        left_inner = ttk.Frame(left, padding=10)
        left_inner.pack(fill=BOTH, expand=True)

        title = ttk.Label(left_inner, text="Postage Calculator", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=W, pady=(0, 8))

        # Group: From/To
        addr_grp = ttk.Labelframe(left_inner, text="Addresses", padding=10)
        addr_grp.pack(fill=X, pady=(0, 8))

        self.var_from = ttk.StringVar()
        self.var_to = ttk.StringVar()

        self._add_labeled_entry(addr_grp, "From Postcode:*", self.var_from, col=0, row=0, width=12)
        self._add_labeled_entry(addr_grp, "To Postcode:*", self.var_to, col=1, row=0, width=12)

        # Group: Package
        pkg_grp = ttk.Labelframe(left_inner, text="Package (Dimensions in cm, Weight in kg)", padding=10)
        pkg_grp.pack(fill=X, pady=8)

        self.var_len = ttk.StringVar()
        self.var_wid = ttk.StringVar()
        self.var_hei = ttk.StringVar()
        self.var_wei = ttk.StringVar()

        self._add_labeled_entry(pkg_grp, "Length:*", self.var_len, col=0, row=0, width=10)
        self._add_labeled_entry(pkg_grp, "Width:*", self.var_wid, col=1, row=0, width=10)
        self._add_labeled_entry(pkg_grp, "Height:*", self.var_hei, col=2, row=0, width=10)
        self._add_labeled_entry(pkg_grp, "Weight:*", self.var_wei, col=0, row=1, width=10)

        # Group: Service
        svc_grp = ttk.Labelframe(left_inner, text="Service", padding=10)
        svc_grp.pack(fill=X, pady=8)

        ttk.Label(svc_grp, text="Service Code:*").grid(row=0, column=0, sticky=W, padx=(0, 6), pady=4)
        self.service_code = ttk.Combobox(svc_grp, state="readonly", width=34)
        self.service_code["values"] = list(SERVICE_OPTIONS.keys())
        self.service_code.bind("<<ComboboxSelected>>", self.update_suboptions)
        self.service_code.grid(row=0, column=1, sticky=EW, pady=4)

        ttk.Label(svc_grp, text="Suboption Code:").grid(row=1, column=0, sticky=W, padx=(0, 6), pady=4)
        self.suboption_code = ttk.Combobox(svc_grp, state="readonly", width=34)
        self.suboption_code.grid(row=1, column=1, sticky=EW, pady=4)

        svc_grp.columnconfigure(1, weight=1)

        # Action Buttons
        btn_row = ttk.Frame(left_inner)
        btn_row.pack(fill=X, pady=(8, 0))

        self.btn_calc = ttk.Button(btn_row, text="Calculate Postage", bootstyle=PRIMARY, command=self.calculate_postage)
        self.btn_calc.pack(side=LEFT)

        ttk.Button(btn_row, text="Clear Form", bootstyle=SECONDARY, command=self._clear_form).pack(side=LEFT, padx=8)

        # --- Right: Results / Preview ---
        right_inner = ttk.Frame(right, padding=10)
        right_inner.pack(fill=BOTH, expand=True)

        result_grp = ttk.Labelframe(right_inner, text="Result", padding=10)
        result_grp.pack(fill=X, pady=(0, 8))

        self.result_cost = ttk.StringVar(value="—")
        self.result_eta = ttk.StringVar(value="—")
        self.result_service = ttk.StringVar(value="—")

        ttk.Label(result_grp, text="Total Cost:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=W)
        ttk.Label(result_grp, textvariable=self.result_cost, font=("Segoe UI", 18, "bold"), bootstyle=SUCCESS).grid(row=0, column=1, sticky=E)

        ttk.Label(result_grp, text="ETA:").grid(row=1, column=0, sticky=W, pady=(6, 0))
        ttk.Label(result_grp, textvariable=self.result_eta, bootstyle=INFO).grid(row=1, column=1, sticky=E, pady=(6, 0))

        ttk.Label(result_grp, text="Service Used:").grid(row=2, column=0, sticky=W, pady=(6, 0))
        ttk.Label(result_grp, textvariable=self.result_service).grid(row=2, column=1, sticky=E, pady=(6, 0))

        result_grp.columnconfigure(1, weight=1)

        # Quick View of recent results
        preview_grp = ttk.Labelframe(right_inner, text="Recent Calculations", padding=10)
        preview_grp.pack(fill=BOTH, expand=True, pady=8)

        cols = ("timestamp", "from", "to", "svc", "cost", "eta")
        self.preview_tree = ttk.Treeview(preview_grp, columns=cols, show="headings", height=7, bootstyle=INFO)
        self.preview_tree.heading("timestamp", text="Time")
        self.preview_tree.heading("from", text="From")
        self.preview_tree.heading("to", text="To")
        self.preview_tree.heading("svc", text="Service")
        self.preview_tree.heading("cost", text="Cost")
        self.preview_tree.heading("eta", text="ETA")
        self.preview_tree.column("timestamp", width=120, anchor=W)
        self.preview_tree.column("from", width=60, anchor=CENTER)
        self.preview_tree.column("to", width=60, anchor=CENTER)
        self.preview_tree.column("svc", width=160, anchor=W)
        self.preview_tree.column("cost", width=80, anchor=E)
        self.preview_tree.column("eta", width=120, anchor=E)
        self.preview_tree.pack(fill=BOTH, expand=True)

    def _build_history_tab(self):
        outer = ttk.Frame(self.tab_hist, padding=10)
        outer.pack(fill=BOTH, expand=True)

        cols = ("timestamp", "from_postcode", "to_postcode", "length_cm", "width_cm",
                "height_cm", "weight_kg", "service_code", "suboption_code", "cost", "eta")
        self.history_tree = ttk.Treeview(outer, columns=cols, show="headings", bootstyle=PRIMARY)
        for c in cols:
            self.history_tree.heading(c, text=c.replace("_", " ").title())
        # Column widths
        widths = [140, 80, 80, 80, 80, 80, 80, 170, 170, 80, 120]
        for c, w in zip(cols, widths):
            self.history_tree.column(c, width=w, anchor=W)
        self.history_tree.pack(fill=BOTH, expand=True)

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill=X, pady=(10, 0))

        ttk.Button(btn_row, text="Recalculate Selected", bootstyle=INFO, command=self.recalculate_selected).pack(side=LEFT)
        ttk.Button(btn_row, text="Copy Selected", bootstyle=SECONDARY, command=self.copy_selected_to_clipboard).pack(side=LEFT, padx=8)
        ttk.Button(btn_row, text="Export to CSV", bootstyle=SUCCESS, command=self.export_csv).pack(side=LEFT, padx=8)
        ttk.Button(btn_row, text="Clear History", bootstyle=DANGER, command=self.clear_history).pack(side=LEFT, padx=8)

        hint = ttk.Label(outer, text="Shortcut: Ctrl+S to export CSV", bootstyle=SECONDARY)
        hint.pack(anchor=E, pady=(6, 0))

    def _build_settings_tab(self):
        outer = ttk.Frame(self.tab_settings, padding=12)
        outer.pack(fill=BOTH, expand=True)

        api_grp = ttk.Labelframe(outer, text="API Configuration", padding=12)
        api_grp.pack(fill=X)

        ttk.Label(api_grp, text="API URL:").grid(row=0, column=0, sticky=W, pady=4)
        self.var_api_url = ttk.StringVar(value=self.cfg.get("api_url", DEFAULT_API_URL))
        ttk.Entry(api_grp, textvariable=self.var_api_url).grid(row=0, column=1, sticky=EW, pady=4)

        ttk.Label(api_grp, text="API Key:").grid(row=1, column=0, sticky=W, pady=4)
        self.var_api_key = ttk.StringVar(value=self.cfg.get("api_key", ""))
        ttk.Entry(api_grp, textvariable=self.var_api_key, show="•").grid(row=1, column=1, sticky=EW, pady=4)

        api_grp.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(api_grp)
        btn_row.grid(row=2, column=0, columnspan=2, sticky=E, pady=(6, 0))

        ttk.Button(btn_row, text="Save", bootstyle=SUCCESS, command=self.save_settings).pack(side=LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Test Connection", bootstyle=INFO, command=self.test_connection).pack(side=LEFT)

        info = ttk.Label(outer,
                         text=f"Settings saved to: {CONFIG_PATH}",
                         bootstyle=SECONDARY, anchor=W)
        info.pack(fill=X, pady=(8, 0))

    # ----------------------------------------
    # UI Helpers
    # ----------------------------------------
    def _add_labeled_entry(self, parent, label, var, col, row, width=12):
        ttk.Label(parent, text=label).grid(row=row, column=col*2, sticky=W, padx=(0, 6), pady=4)
        ent = ttk.Entry(parent, textvariable=var, width=width)
        ent.grid(row=row, column=col*2 + 1, sticky=W, pady=4)
        return ent

    def _clear_form(self):
        for v in (self.var_from, self.var_to, self.var_len, self.var_wid, self.var_hei, self.var_wei):
            v.set("")
        self.service_code.set("")
        self.suboption_code.set("")
        self.result_cost.set("—")
        self.result_eta.set("—")
        self.result_service.set("—")
        self.status_var.set("Form cleared.")

    # ----------------------------------------
    # Validation
    # ----------------------------------------
    def _validate_inputs(self):
        # Required: from, to, length, width, height, weight, service_code
        from_pc = self.var_from.get().strip()
        to_pc = self.var_to.get().strip()
        length = self.var_len.get().strip()
        width = self.var_wid.get().strip()
        height = self.var_hei.get().strip()
        weight = self.var_wei.get().strip()
        svc = self.service_code.get().strip()
        subopt = self.suboption_code.get().strip()

        # Postcode validation (AU: 4 digits)
        def is_postcode(pc):
            return pc.isdigit() and len(pc) == 4

        errors = []
        if not is_postcode(from_pc):
            errors.append("From Postcode must be 4 digits.")
        if not is_postcode(to_pc):
            errors.append("To Postcode must be 4 digits.")

        def parse_positive_float(name, val):
            try:
                f = float(val)
                if f <= 0:
                    raise ValueError
                return f
            except Exception:
                errors.append(f"{name} must be a positive number.")
                return None

        l = parse_positive_float("Length", length)
        w = parse_positive_float("Width", width)
        h = parse_positive_float("Height", height)
        kg = parse_positive_float("Weight (kg)", weight)

        if not svc:
            errors.append("Service Code is required.")

        if errors:
            return None, errors

        grams = int(round(kg * 1000))  # Convert kg → grams

        payload = {
            "from_postcode": from_pc,
            "to_postcode": to_pc,
            "length": l,
            "width": w,
            "height": h,
            "weight": str(grams),  # API expects grams as string
            "service_code": svc
        }
        if subopt:
            payload["suboption_code"] = subopt

        return payload, None

    # ----------------------------------------
    # API Interaction
    # ----------------------------------------
    def calculate_postage(self):
        payload, errors = self._validate_inputs()
        if errors:
            messagebox.showwarning("Validation Error", "\n".join(errors))
            return

        api_key = self.var_api_key.get().strip()
        api_url = self.var_api_url.get().strip() or DEFAULT_API_URL
        if not api_key:
            messagebox.showwarning("Missing API Key", "Please set your API key in Settings.")
            self.notebook.select(self.tab_settings)
            return

        headers = {"AUTH-KEY": api_key}
        self.btn_calc.config(state=DISABLED)
        self.status_var.set("Calculating...")

        def worker():
            try:
                with self._api_lock:
                    r = requests.get(api_url, headers=headers, params={
                        # The API expects numeric params as strings; convert precisely
                        "from_postcode": payload["from_postcode"],
                        "to_postcode": payload["to_postcode"],
                        "length": str(payload["length"]),
                        "width": str(payload["width"]),
                        "height": str(payload["height"]),
                        "weight": payload["weight"],
                        "service_code": payload["service_code"],
                        **({"suboption_code": payload["suboption_code"]} if "suboption_code" in payload else {})
                    }, timeout=20)

                r.raise_for_status()
                # Robust JSON parsing
                try:
                    data = r.json()
                except Exception:
                    raise ValueError("Invalid JSON response from API.")

                # The AusPost response typically nests under 'postage_result'
                res = data.get("postage_result", data)
                cost = res.get("total_cost") or res.get("cost") or "N/A"
                eta = res.get("delivery_time") or res.get("eta") or "No ETA"

                # Update UI in main thread
                self.root.after(0, self._handle_success, payload, cost, eta)
            except requests.HTTPError as e:
                body = e.response.text if hasattr(e, "response") and e.response is not None else str(e)
                self.root.after(0, self._handle_error, f"HTTP Error: {e}\n{body}")
            except requests.Timeout:
                self.root.after(0, self._handle_error, "Request timed out. Please try again.")
            except Exception as e:
                self.root.after(0, self._handle_error, f"API Error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _handle_success(self, payload, cost, eta):
        self.btn_calc.config(state=NORMAL)
        self.result_cost.set(f"${cost}")
        self.result_eta.set(eta)
        svc = payload["service_code"]
        sub = payload.get("suboption_code", "")
        svc_label = f"{svc}" + (f" → {sub}" if sub else "")
        self.result_service.set(svc_label)
        self.status_var.set("Calculation complete.")

        # Add to history
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_postcode": payload["from_postcode"],
            "to_postcode": payload["to_postcode"],
            "length_cm": payload["length"],
            "width_cm": payload["width"],
            "height_cm": payload["height"],
            "weight_kg": round(int(payload["weight"]) / 1000, 3),
            "service_code": payload["service_code"],
            "suboption_code": payload.get("suboption_code", ""),
            "cost": cost,
            "eta": eta
        }
        self.history.append(record)
        self._refresh_preview()
        self._refresh_history_tree([record])  # Append last one

    def _handle_error(self, msg):
        self.btn_calc.config(state=NORMAL)
        messagebox.showerror("API Error", msg)
        self.status_var.set("Error. See dialog for details.")

    # ----------------------------------------
    # History Management
    # ----------------------------------------
    def _refresh_preview(self):
        # Show last 8 results in preview
        for i in self.preview_tree.get_children():
            self.preview_tree.delete(i)
        for rec in self.history[-8:]:
            self.preview_tree.insert("", "end", values=(
                rec["timestamp"], rec["from_postcode"], rec["to_postcode"],
                f"{rec['service_code']}" + (f"→{rec['suboption_code']}" if rec['suboption_code'] else ""),
                f"${rec['cost']}", rec["eta"]
            ))

    def _refresh_history_tree(self, new_records=None):
        # If new_records provided, append; else rebuild entirely
        if new_records:
            for rec in new_records:
                self.history_tree.insert("", "end", values=tuple(rec.get(k, "") for k in CSV_FIELDS))
        else:
            for i in self.history_tree.get_children():
                self.history_tree.delete(i)
            for rec in self.history:
                self.history_tree.insert("", "end", values=tuple(rec.get(k, "") for k in CSV_FIELDS))

    def clear_history(self):
        if not self.history:
            messagebox.showinfo("Clear History", "No entries to clear.")
            return
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all history?"):
            self.history.clear()
            self._refresh_preview()
            self._refresh_history_tree()
            self.status_var.set("History cleared.")

    def export_csv(self):
        if not self.history:
            messagebox.showinfo("Export", "No history to export.")
            return
        f = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not f:
            return
        try:
            with open(f, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(self.history)
            messagebox.showinfo("Export", "Export complete.")
            self.status_var.set(f"Exported to {f}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def recalculate_selected(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Recalculate", "Please select a history row.")
            return
        values = self.history_tree.item(sel[0], "values")
        rec = dict(zip(CSV_FIELDS, values))

        # Refill form with selected record
        self.var_from.set(rec["from_postcode"])
        self.var_to.set(rec["to_postcode"])
        self.var_len.set(rec["length_cm"])
        self.var_wid.set(rec["width_cm"])
        self.var_hei.set(rec["height_cm"])
        self.var_wei.set(rec["weight_kg"])
        self.service_code.set(rec["service_code"])
        self.update_suboptions()
        if rec.get("suboption_code"):
            self.suboption_code.set(rec["suboption_code"])
        else:
            self.suboption_code.set("")

        self.notebook.select(self.tab_calc)
        self.calculate_postage()

    def copy_selected_to_clipboard(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Copy", "Please select a history row.")
            return
        values = self.history_tree.item(sel[0], "values")
        rec = dict(zip(CSV_FIELDS, values))
        text = ", ".join(f"{k}={rec.get(k, '')}" for k in CSV_FIELDS)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied selected row to clipboard.")

    # ----------------------------------------
    # Settings
    # ----------------------------------------
    def save_settings(self):
        ok, msg = save_config(self.var_api_key.get(), self.var_api_url.get() or DEFAULT_API_URL)
        if ok:
            self.cfg = load_config()
            self.status_var.set(msg)
            messagebox.showinfo("Settings", msg)
        else:
            messagebox.showerror("Settings", msg)

    def test_connection(self):
        api_key = self.var_api_key.get().strip()
        api_url = self.var_api_url.get().strip() or DEFAULT_API_URL
        if not api_key:
            messagebox.showwarning("Test Connection", "Please enter an API Key first.")
            return

        self.status_var.set("Testing connection...")
        def worker():
            try:
                # Minimal ping: perform a GET with deliberately incomplete params to check auth/URL.
                r = requests.get(api_url, headers={"AUTH-KEY": api_key}, params={"from_postcode": "2000"}, timeout=12)
                # If 401/403, we still learn that the endpoint/key format is recognized.
                status = r.status_code
                if status == 200:
                    msg = "Connection OK (HTTP 200)."
                elif status in (400, 401, 403):
                    msg = f"Reached API (HTTP {status}). Key/params may need adjustment."
                else:
                    msg = f"Endpoint reachable (HTTP {status})."
                self.root.after(0, lambda: (messagebox.showinfo("Test Connection", msg), self.status_var.set(msg)))
            except Exception as e:
                self.root.after(0, lambda: (messagebox.showerror("Test Connection", str(e)), self.status_var.set("Connection test failed.")))

        threading.Thread(target=worker, daemon=True).start()

    # ----------------------------------------
    # Events
    # ----------------------------------------
    def update_suboptions(self, event=None):
        selected = self.service_code.get()
        options = SERVICE_OPTIONS.get(selected, [])
        self.suboption_code["values"] = options
        if options:
            self.suboption_code.set(options[0])
        else:
            self.suboption_code.set("")


# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app = ttk.Window(themename=THEME)
    PostageCalculatorApp(app)
    app.mainloop()
