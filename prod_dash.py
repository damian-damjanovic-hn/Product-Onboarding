import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3, csv, threading, os, io, urllib.request
import io, os, csv, threading, urllib.request, sqlite3, time
# --------------------------
# Product Management Dashboard
# --------------------------
# Standard library only. Dark "Tokyo Night"-like style.
# Features:
# - Import from CSV (upsert by SKU)
# - Toggle Table <-> Card views
# - Double-click (table) / click (card) opens detail/edit dialog
# - Search/filter, sorting, pagination
# - Export visible page to CSV (optional)
#
# Expected CSV headers: sku,name,price,stock,category,status,image_path,description
#   - image_path supports local PNG/GIF, or URL (PNG/GIF).
#   - Extra columns are ignored.

DB_FILE = "products.db"

class ProductDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Management Dashboard")
        self.root.geometry("1300x800")

        # State
        self.page_size = 12
        self.current_page = 0
        self.sort_column = None   # one of ('sku','name','price','stock','category','status')
        self.sort_reverse = False
        self.view_mode = tk.StringVar(value="table")  # 'table' or 'cards'
        self.search_text = tk.StringVar(value="")
        self.page_size_var = tk.IntVar(value=self.page_size)

        # Keep in-memory lists
        self.all_data = []        # list of dict rows from DB
        self.filtered_data = []   # search-filtered view
        self.image_cache = {}     # id -> PhotoImage (to prevent GC)

        self._setup_theme()
        self._setup_db()
        self._setup_ui()
        self._load_data()

    # ---------- THEME ----------
    def _setup_theme(self):
        self.colors = {
            "bg": "#1a1b26",
            "bg2": "#24283b",
            "fg": "#c0caf5",
            "fg_muted": "#a9b1d6",
            "accent": "#7aa2f7",
            "accent2": "#bb9af7",
            "selected": "#414868",
            "warning": "#e0af68",
            "error": "#f7768e",
            "ok": "#9ece6a",
            "card_border": "#2a2e3f"
        }
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure("TButton", background=self.colors["accent"], foreground=self.colors["bg"])
        style.map("TButton", background=[("active", self.colors["accent2"])])
        style.configure("TEntry", fieldbackground=self.colors["bg2"], foreground=self.colors["fg"])
        style.configure("TCombobox", fieldbackground=self.colors["bg2"], foreground=self.colors["fg"])
        style.configure("Treeview",
                        background=self.colors["bg2"],
                        foreground=self.colors["fg"],
                        fieldbackground=self.colors["bg2"],
                        rowheight=26,
                        bordercolor=self.colors["card_border"])
        style.map("Treeview", background=[("selected", self.colors["selected"])])

    # ---------- DB ----------
    def _setup_db(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE,
                name TEXT,
                price REAL,
                stock INTEGER,
                category TEXT,
                status TEXT,
                image_path TEXT,
                description TEXT
            )
        """)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.commit()


    def _get_db_connection(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        # Match PRAGMAs for consistency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    # ---------- UI ----------
    def _setup_ui(self):
        # Root split: left controls / right content
        self.left = tk.Frame(self.root, bg=self.colors["bg"], width=300)
        self.left.pack(side=tk.LEFT, fill=tk.Y)
        self.right = tk.Frame(self.root, bg=self.colors["bg"])
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Left controls
        tk.Label(self.left, text="Controls", bg=self.colors["bg"], fg=self.colors["fg"],
                 font=("Segoe UI", 12, "bold")).pack(pady=(12, 6), anchor="w", padx=12)

        ttk.Button(self.left, text="Import CSV", command=self.import_csv).pack(padx=12, pady=4, fill="x")
        ttk.Button(self.left, text="Export Visible to CSV", command=self.export_csv).pack(padx=12, pady=4, fill="x")

        # View toggle
        tk.Label(self.left, text="View Mode", bg=self.colors["bg"], fg=self.colors["fg_muted"]).pack(padx=12, pady=(12, 0), anchor="w")
        view_frame = tk.Frame(self.left, bg=self.colors["bg"])
        view_frame.pack(padx=12, pady=4, anchor="w")
        ttk.Radiobutton(view_frame, text="Table", value="table", variable=self.view_mode,
                        command=self._refresh_view).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(view_frame, text="Cards", value="cards", variable=self.view_mode,
                        command=self._refresh_view).pack(side=tk.LEFT)

        # Search
        tk.Label(self.left, text="Search (SKU/Name/Category)", bg=self.colors["bg"], fg=self.colors["fg_muted"]).pack(padx=12, pady=(12, 0), anchor="w")
        search_entry = ttk.Entry(self.left, textvariable=self.search_text)
        search_entry.pack(padx=12, pady=4, fill="x")
        search_entry.bind("<Return>", lambda e: self._apply_search())

        ttk.Button(self.left, text="Apply Filter", command=self._apply_search).pack(padx=12, pady=4, fill="x")
        ttk.Button(self.left, text="Clear Filter", command=self._clear_search).pack(padx=12, pady=(0, 12), fill="x")

        # Page size
        tk.Label(self.left, text="Page Size", bg=self.colors["bg"], fg=self.colors["fg_muted"]).pack(padx=12, pady=(6, 0), anchor="w")
        ps = ttk.Combobox(self.left, textvariable=self.page_size_var, values=[6, 12, 24, 48], state="readonly")
        ps.pack(padx=12, pady=4, fill="x")
        ps.bind("<<ComboboxSelected>>", lambda e: self._change_page_size())

        # Stats section
        self.stats_label = tk.Label(self.left, text="Products: 0", bg=self.colors["bg"], fg=self.colors["fg"])
        self.stats_label.pack(padx=12, pady=(18, 6), anchor="w")

        # Right top: header / nav
        header = tk.Frame(self.right, bg=self.colors["bg"])
        header.pack(fill="x")
        self.status_label = tk.Label(header, text="Ready", bg=self.colors["bg"], fg=self.colors["fg_muted"])
        self.status_label.pack(side=tk.LEFT, padx=12, pady=8)

        nav = tk.Frame(header, bg=self.colors["bg"])
        nav.pack(side=tk.RIGHT, padx=12, pady=8)
        self.prev_btn = ttk.Button(nav, text="Prev", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=4)
        self.page_label = tk.Label(nav, text="Page 1", bg=self.colors["bg"], fg=self.colors["fg"])
        self.page_label.pack(side=tk.LEFT, padx=6)
        self.next_btn = ttk.Button(nav, text="Next", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=4)

        # Content area: stack table and cards, show one at a time
        self.content_stack = tk.Frame(self.right, bg=self.colors["bg"])
        self.content_stack.pack(fill=tk.BOTH, expand=True)

        # Table view
        self.table_frame = tk.Frame(self.content_stack, bg=self.colors["bg"])
        cols = ("sku", "name", "price", "stock", "category", "status")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        headings = {
            "sku": "SKU", "name": "Name", "price": "Price", "stock": "Stock",
            "category": "Category", "status": "Status"
        }
        for cid in cols:
            self.tree.heading(cid, text=headings[cid], command=lambda c=cid: self.sort_by_column(c))
            width = 120 if cid not in ("name",) else 240
            self.tree.column(cid, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._table_double_click)

        # Cards view (scrollable)
        self.cards_frame = tk.Frame(self.content_stack, bg=self.colors["bg"])
        self.cards_canvas = tk.Canvas(self.cards_frame, bg=self.colors["bg"], highlightthickness=0)
        self.cards_scroll = ttk.Scrollbar(self.cards_frame, orient="vertical", command=self.cards_canvas.yview)
        self.cards_inner = tk.Frame(self.cards_canvas, bg=self.colors["bg"])
        self.cards_inner.bind("<Configure>", lambda e: self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all")))
        self.cards_canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")
        self.cards_canvas.configure(yscrollcommand=self.cards_scroll.set)

        self.cards_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        self.cards_scroll.pack(side="right", fill="y")

        # Start with table
        self._show_table()

    # ---------- DATA LOAD / FILTER / SORT ----------
    def _load_data(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, sku, name, price, stock, category, status, image_path, description
            FROM products
            ORDER BY id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        self.all_data = rows
        self._apply_search()
        self.stats_label.config(text=f"Products: {len(self.all_data)}")
        self.status_label.config(text="Loaded products")

    def _apply_search(self):
        q = self.search_text.get().strip().lower()
        if not q:
            self.filtered_data = list(self.all_data)
        else:
            self.filtered_data = [
                r for r in self.all_data
                if q in (r.get("sku") or "").lower()
                or q in (r.get("name") or "").lower()
                or q in (r.get("category") or "").lower()
            ]
        # Reset page on new filter
        self.current_page = 0
        self._refresh_view()

    def _clear_search(self):
        self.search_text.set("")
        self._apply_search()

    def sort_by_column(self, col):
        # Toggle sort order if same col
        reverse = self.sort_column == col and not self.sort_reverse
        self.filtered_data.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=reverse)
        self.sort_column = col
        self.sort_reverse = reverse
        self._refresh_view()

    # ---------- PAGINATION ----------
    def _page_slice(self):
        total = len(self.filtered_data)
        start = self.current_page * self.page_size
        end = min(start + self.page_size, total)
        return start, end

    def _change_page_size(self):
        self.page_size = int(self.page_size_var.get())
        self.current_page = 0
        self._refresh_view()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_view()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_data):
            self.current_page += 1
            self._refresh_view()

    # ---------- VIEW SWITCH ----------
    def _refresh_view(self):
        total_pages = max(1, (len(self.filtered_data) - 1) // self.page_size + 1)
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")
        if self.view_mode.get() == "table":
            self._show_table()
            self._update_table()
        else:
            self._show_cards()
            self._update_cards()

    def _show_table(self):
        self.cards_frame.pack_forget()
        self.table_frame.pack(fill=tk.BOTH, expand=True)

    def _show_cards(self):
        self.table_frame.pack_forget()
        self.cards_frame.pack(fill=tk.BOTH, expand=True)

    # ---------- TABLE ----------
    def _update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        start, end = self._page_slice()
        for r in self.filtered_data[start:end]:
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("sku") or "",
                r.get("name") or "",
                f'{(r.get("price") or 0):.2f}',
                int(r.get("stock") or 0),
                r.get("category") or "",
                r.get("status") or "",
            ))

    def _table_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        prod = next((x for x in self.all_data if x["id"] == pid), None)
        if prod:
            self._open_detail_dialog(prod)

    # ---------- CARDS ----------
    def _clear_cards(self):
        for w in self.cards_inner.winfo_children():
            w.destroy()
        # keep images to avoid flicker; they’re re-used by id in image_cache

    def _update_cards(self):
        self._clear_cards()
        start, end = self._page_slice()
        data = self.filtered_data[start:end]

        # layout grid
        cols = 3 if self.page_size <= 12 else 4
        thumb_w, thumb_h = 120, 120

        for idx, r in enumerate(data):
            card = tk.Frame(self.cards_inner, bg=self.colors["bg2"], bd=1, relief="solid", highlightthickness=0)
            card.configure(highlightbackground=self.colors["card_border"])
            row, col = divmod(idx, cols)
            card.grid(row=row, column=col, padx=12, pady=12, sticky="n")
            card.bind("<Button-1>", lambda e, rr=r: self._open_detail_dialog(rr))

            # Image
            img_holder = tk.Label(card, bg=self.colors["bg2"])
            img_holder.pack(padx=12, pady=(12, 6))
            photo = self._get_thumbnail_for_product(r, thumb_w, thumb_h)
            if photo is not None:
                img_holder.configure(image=photo)
                img_holder.image = photo  # keep ref
            else:
                # Placeholder
                ph = tk.Canvas(card, width=thumb_w, height=thumb_h, bg=self.colors["bg"], highlightthickness=0)
                ph.create_text(thumb_w//2, thumb_h//2, text="No Image", fill=self.colors["fg_muted"])
                ph.pack(padx=12, pady=(12, 6))

            # Text
            name = tk.Label(card, text=r.get("name") or "(no name)", bg=self.colors["bg2"],
                            fg=self.colors["fg"], font=("Segoe UI", 10, "bold"))
            name.pack(padx=12, anchor="w")
            sku = tk.Label(card, text=f"SKU: {r.get('sku') or ''}", bg=self.colors["bg2"], fg=self.colors["fg_muted"])
            sku.pack(padx=12, anchor="w")

            details = tk.Label(card,
                               text=f"${(r.get('price') or 0):.2f}  |  Stock: {int(r.get('stock') or 0)}",
                               bg=self.colors["bg2"], fg=self.colors["fg_muted"])
            details.pack(padx=12, pady=(0, 8), anchor="w")

            # Click-to-edit binding on children
            for w in (img_holder, name, sku, details):
                w.bind("<Button-1>", lambda e, rr=r: self._open_detail_dialog(rr))

        # make grid stretch
        for c in range(cols):
            self.cards_inner.grid_columnconfigure(c, weight=1)

    def _get_thumbnail_for_product(self, r, max_w, max_h):
        """
        Load and lightly downscale a PNG/GIF using Tkinter PhotoImage.
        (No PIL to keep stdlib-only.)
        """
        pid = r["id"]
        if pid in self.image_cache:
            return self.image_cache[pid]

        path = (r.get("image_path") or "").strip()
        if not path:
            return None

        try:
            if path.startswith("http://") or path.startswith("https://"):
                # Download to memory (only PNG/GIF supported by PhotoImage)
                with urllib.request.urlopen(path, timeout=5) as resp:
                    data = resp.read()
                img = tk.PhotoImage(data=data)
            else:
                if not os.path.exists(path):
                    return None
                img = tk.PhotoImage(file=path)
        except Exception:
            return None

        # Downscale via subsample if needed (integer factor)
        w, h = img.width(), img.height()
        if w > max_w or h > max_h:
            fx = max(1, w // max_w)
            fy = max(1, h // max_h)
            img = img.subsample(fx, fy)

        self.image_cache[pid] = img
        return img

    # ---------- IMPORT / EXPORT ----------



    # --- Add inside ProductDashboard class ---

    # def _ensure_db_indexes(self):
    #     cur = self.conn.cursor()
    #     cur.execute("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
    #     self.conn.commit()

    def _ensure_db_indexes(self, conn):
        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
        conn.commit()

    def _detect_encoding(self, path):
        """Detect encoding with BOM and sane fallbacks. Return (encoding, bom_used)"""
        with open(path, "rb") as fb:
            head = fb.read(8)
        # BOM checks
        if head.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig", True
        if head.startswith(b"\xff\xfe\x00\x00") or head.startswith(b"\x00\x00\xfe\xff"):
            # UTF-32 not supported by csv easily; we'll fallback to utf-8 later
            pass
        if head.startswith(b"\xff\xfe"):
            return "utf-16le", True
        if head.startswith(b"\xfe\xff"):
            return "utf-16be", True

        # Try candidates with "strict" to see what fits small sample
        candidates = ["utf-8", "cp1252", "latin-1", "utf-16", "utf-16le", "utf-16be"]
        with open(path, "rb") as fb:
            sample = fb.read(65536)
        for enc in candidates:
            try:
                sample.decode(enc)
                return enc, False
            except Exception:
                continue
        # Last resort: latin-1 never fails
        return "latin-1", False

    def _open_csv_text(self, path):
        """Return (text_stream, encoding, file_handle) ready for csv. Caller must close fh."""
        enc, _ = self._detect_encoding(path)
        fh = open(path, "rb")  # keep binary handle; wrap in TextIOWrapper
        # errors='replace' ensures we never crash on stray bytes
        tw = io.TextIOWrapper(fh, encoding=enc, errors="replace", newline="")
        return tw, enc, fh

    def _sniff_dialect(self, text_stream):
        """Sniff CSV dialect safely; fallback to comma. Keeps stream positioned at start after sniff."""
        pos = text_stream.tell()
        sample = text_stream.read(16384).replace("\x00", "")
        text_stream.seek(pos)
        try:
            dialect = csv.Sniffer().sniff(sample)
            # If delimiter looks unreasonable, force comma
            if getattr(dialect, "delimiter", ",") not in [",", ";", "\t", "|"]:
                dialect.delimiter = ","
            return dialect
        except Exception:
            class Simple(complex): pass  # dummy type just to carry attrs
            dialect = csv.excel
            dialect.delimiter = ","
            return dialect

    def _normalize_header(self, h):
        return (h or "").strip().lower().replace("\u00a0", " ").replace(" ", "").replace("-", "").replace("_","")

    def _dedupe_headers(self, headers):
        seen = {}
        out = []
        for h in headers:
            base = h
            if base in seen:
                seen[base] += 1
                h = f"{base}{seen[base]}"
            else:
                seen[base] = 0
            out.append(h)
        return out

    def _build_header_map(self, hdrs_norm):
        """Map various source names to our target schema."""
        # target: sku,name,price,stock,category,status,image_path,description
        synonyms = {
            "sku": {"sku","productcode","code","itemcode","id","productid"},
            "name": {"name","title","productname","descriptionshort","itemname"},
            "price": {"price","unitprice","sellprice","rrp","priceex","priceinctax"},
            "stock": {"stock","qty","quantity","onhand","inventory"},
            "category": {"category","cat","segment"},
            "status": {"status","state","enabled","active"},
            "image_path": {"image","imagepath","imageurl","picture","img"},
            "description": {"description","longdescription","fulldescription","details","notes"}
        }
        mapping = {}
        for target, keys in synonyms.items():
            for i, src in enumerate(hdrs_norm):
                if src in keys:
                    mapping[target] = i
                    break
        return mapping

    def _to_float(self, x):
        s = str(x or "").strip()
        if not s or s.lower() in {"n/a","na","null","none","-"}:
            return 0.0
        # strip currency and thousands separators
        s = s.replace("$","").replace("€","").replace("£","")
        s = s.replace(",","")
        try:
            return float(s)
        except Exception:
            return 0.0

    def _to_int(self, x):
        s = str(x or "").strip()
        if not s or s.lower() in {"n/a","na","null","none","-"}:
            return 0
        try:
            return int(float(s.replace(",","")))
        except Exception:
            return 0

    def _sanitize_cell(self, s):
        return (str(s or "")
                .replace("\x00","")     # null bytes
                .replace("\r\n","\n")   # normalize newlines
                .replace("\r","\n")).strip()



    # def import_csv(self):
    #     path = filedialog.askopenfilename(
    #         title="Select products CSV",
    #         filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    #     )
    #     if not path:
    #         return

    #     def worker():
    #         inserted, updated, errors = 0, 0, 0
    #         required = {"sku", "name"}
    #         optional = {"price", "stock", "category", "status", "image_path", "description"}

    #         self._set_status("Importing...")
    #         try:
    #             with open(path, "r", newline="", encoding="utf-8-sig") as f:
    #                 reader = csv.DictReader(f)
    #                 headers = {h.strip() for h in reader.fieldnames or []}
    #                 missing = required - {h.lower() for h in headers}
    #                 if missing:
    #                     raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    #                 cur = self.conn.cursor()
    #                 for row in reader:
    #                     try:
    #                         sku = (row.get("sku") or "").strip()
    #                         name = (row.get("name") or "").strip()
    #                         if not sku or not name:
    #                             raise ValueError("SKU and Name are required")

    #                         # Coerce numeric
    #                         def to_float(x):
    #                             try:
    #                                 return float(str(x).strip().replace(",", ""))
    #                             except Exception:
    #                                 return 0.0
    #                         def to_int(x):
    #                             try:
    #                                 return int(float(str(x).strip().replace(",", "")))
    #                             except Exception:
    #                                 return 0

    #                         price = to_float(row.get("price"))
    #                         stock = to_int(row.get("stock"))
    #                         category = (row.get("category") or "").strip()
    #                         status = (row.get("status") or "").strip()
    #                         image_path = (row.get("image_path") or "").strip()
    #                         description = (row.get("description") or "").strip()

    #                         # Upsert by SKU
    #                         cur.execute("SELECT id FROM products WHERE sku = ?", (sku,))
    #                         existing = cur.fetchone()
    #                         if existing:
    #                             cur.execute("""
    #                                 UPDATE products
    #                                 SET name=?, price=?, stock=?, category=?, status=?, image_path=?, description=?
    #                                 WHERE sku=?
    #                             """, (name, price, stock, category, status, image_path, description, sku))
    #                             updated += 1
    #                         else:
    #                             cur.execute("""
    #                                 INSERT INTO products (sku, name, price, stock, category, status, image_path, description)
    #                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    #                             """, (sku, name, price, stock, category, status, image_path, description))
    #                             inserted += 1
    #                     except Exception:
    #                         errors += 1
    #                 self.conn.commit()
    #         except Exception as e:
    #             self._set_status("Import failed")
    #             messagebox.showerror("Import CSV", f"Failed to import:\n{e}")
    #             return

    #         # Reload UI on main thread
    #         self.root.after(0, lambda: self._after_import(inserted, updated, errors))

    #     threading.Thread(target=worker, daemon=True).start()

    # def import_csv(self):
    #     path = filedialog.askopenfilename(
    #         title="Select products CSV",
    #         filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    #     )
    #     if not path:
    #         return

    #     def worker():
    #         t0 = time.time()
    #         inserted = updated = skipped = 0
    #         error_lines = []

    #         self._set_status("Importing...")
    #         self._ensure_db_indexes()

    #         try:
    #             # Open text safely with encoding fallback
    #             text, enc, fh = self._open_csv_text(path)
    #         except Exception as e:
    #             self.root.after(0, lambda: self._after_import(0, 0, 0))
    #             self.root.after(0, lambda: messagebox.showerror("Import CSV", f"Failed to open file:\n{e}"))
    #             return

    #         try:
    #             # csv settings
    #             csv.field_size_limit(10**7)  # allow very large fields
    #             dialect = self._sniff_dialect(text)

    #             # Read headers
    #             try:
    #                 reader = csv.reader(text, dialect=dialect)
    #                 raw_headers = next(reader, None)
    #                 if not raw_headers:
    #                     raise ValueError("File has no header row.")
    #             except Exception as e:
    #                 raise ValueError(f"Could not read header row: {e}")

    #             # Normalize & dedupe headers
    #             headers_norm = [self._normalize_header(h) for h in raw_headers]
    #             headers_norm = self._dedupe_headers(headers_norm)

    #             # Build source index mapping
    #             src_index = {h: i for i, h in enumerate(headers_norm)}

    #             # Build target mapping
    #             target_map = self._build_header_map(headers_norm)

    #             # Required targets
    #             required_targets = ["sku", "name"]
    #             missing_targets = [t for t in required_targets if t not in target_map]
    #             if missing_targets:
    #                 # Allow continue but warn; rows without sku or name will be skipped
    #                 error_lines.append(f"[Header] Missing required columns mapped to: {', '.join(missing_targets)}. "
    #                                 f"File encoding guessed: {enc}")

    #             # Prepare to iterate rows again via DictReader-like logic
    #             # Move back to start of data rows
    #             text.seek(0)
    #             reader = csv.reader(text, dialect=dialect)

    #             # Consume header again
    #             _ = next(reader, None)

    #             # Use single transaction for speed
    #             cur = self.conn.cursor()
    #             cur.execute("BEGIN")

    #             # Try UPSERT availability
    #             upsert_sql = """
    #                 INSERT INTO products (sku, name, price, stock, category, status, image_path, description)
    #                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    #                 ON CONFLICT(sku) DO UPDATE SET
    #                 name=excluded.name,
    #                 price=excluded.price,
    #                 stock=excluded.stock,
    #                 category=excluded.category,
    #                 status=excluded.status,
    #                 image_path=excluded.image_path,
    #                 description=excluded.description
    #             """
    #             have_upsert = True
    #             try:
    #                 cur.execute("SELECT 1")  # no-op
    #             except sqlite3.OperationalError:
    #                 have_upsert = False

    #             batch = []
    #             BATCH_SIZE = 500

    #             def flush_batch():
    #                 nonlocal inserted, updated
    #                 if not batch:
    #                     return
    #                 if have_upsert:
    #                     try:
    #                         cur.executemany(upsert_sql, batch)
    #                         # Rowcount is unreliable for UPSERT; estimate using SKU existence check only if needed
    #                     except sqlite3.OperationalError:
    #                         # SQLite too old for UPSERT -> fallback to manual
    #                         self.conn.rollback()
    #                         raise
    #                 else:
    #                     # Fallback: manual upsert (slower)
    #                     for tpl in batch:
    #                         sku = tpl[0]
    #                         cur.execute("SELECT id FROM products WHERE sku=?", (sku,))
    #                         if cur.fetchone():
    #                             cur.execute("""
    #                                 UPDATE products
    #                                 SET name=?, price=?, stock=?, category=?, status=?, image_path=?, description=?
    #                                 WHERE sku=?""",
    #                                 (tpl[1], tpl[2], tpl[3], tpl[4], tpl[5], tpl[6], tpl[7], sku)
    #                             )
    #                             updated += 1
    #                         else:
    #                             cur.execute("""
    #                                 INSERT INTO products (sku, name, price, stock, category, status, image_path, description)
    #                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", tpl)
    #                             inserted += 1
    #                 batch.clear()

    #             line_no = 1  # counting from after header
    #             for row in reader:
    #                 line_no += 1
    #                 try:
    #                     # Cope with ragged rows
    #                     vals = [self._sanitize_cell(row[i]) if i < len(row) else "" for i in range(len(headers_norm))]
    #                     def get_by_target(t):
    #                         idx = target_map.get(t, None)
    #                         return vals[idx] if idx is not None and idx < len(vals) else ""

    #                     sku = get_by_target("sku")
    #                     name = get_by_target("name")

    #                     if not sku or not name:
    #                         skipped += 1
    #                         error_lines.append(f"[Line {line_no}] Missing SKU or Name; row skipped.")
    #                         continue

    #                     price = self._to_float(get_by_target("price"))
    #                     stock = self._to_int(get_by_target("stock"))
    #                     category = get_by_target("category")
    #                     status = get_by_target("status")
    #                     image_path = get_by_target("image_path")
    #                     description = get_by_target("description")

    #                     batch.append((sku, name, price, stock, category, status, image_path, description))

    #                     if len(batch) >= BATCH_SIZE:
    #                         flush_batch()
    #                 except Exception as e:
    #                     skipped += 1
    #                     error_lines.append(f"[Line {line_no}] {e}")

    #             # Final flush & commit
    #             flush_batch()
    #             self.conn.commit()

    #             # If UPSERT used, we don’t have exact inserted/updated counts.
    #             # We can compute changes by quick pass if desired; for speed we’ll just report total processed.
    #             if have_upsert:
    #                 # Derive estimates from counts; not exact but indicative
    #                 # Better: run count of distinct SKUs in CSV vs existing; skipping for performance.
    #                 pass

    #         except Exception as e:
    #             try:
    #                 self.conn.rollback()
    #             except Exception:
    #                 pass
    #             error_lines.append(f"[Fatal] {e}")
    #         finally:
    #             try:
    #                 text.detach()  # closes wrapper but not fh
    #             except Exception:
    #                 pass
    #             try:
    #                 fh.close()
    #             except Exception:
    #                 pass

    #         # Write error log if any
    #         try:
    #             if error_lines:
    #                 log_path = path + ".errors.txt"
    #                 with open(log_path, "w", encoding="utf-8") as logf:
    #                     logf.write("Import Log\n")
    #                     logf.write(f"Source: {path}\n")
    #                     logf.write(f"Encoding used: {enc}\n")
    #                     logf.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    #                     for line in error_lines[:10000]:  # cap log size
    #                         logf.write(line + "\n")
    #         except Exception:
    #             pass

    #         elapsed = time.time() - t0
    #         msg = f"Import complete in {elapsed:.1f}s | Inserted≈{inserted} Updated≈{updated} Skipped={skipped}"
    #         self.root.after(0, lambda: self._after_import(inserted, updated, skipped))
    #         self.root.after(0, lambda: self._set_status(msg))

    #     threading.Thread(target=worker, daemon=True).start()

    def import_csv(self):
        path = filedialog.askopenfilename(
            title="Select products CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        def worker():
            # 1) Open a separate connection for this thread
            conn = None
            try:
                conn = self._get_db_connection()
                self._ensure_db_indexes(conn)

                # 2) Open text stream with robust encoding handling
                try:
                    text, enc, fh = self._open_csv_text(path)  # from the previous helper I gave you
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Import CSV", f"Failed to open file:\n{e}"))
                    return

                try:
                    # 3) Sniff CSV dialect, read header, etc. (same as previous version)
                    csv.field_size_limit(10**7)
                    dialect = self._sniff_dialect(text)

                    reader = csv.reader(text, dialect=dialect)
                    raw_headers = next(reader, None)
                    if not raw_headers:
                        raise ValueError("File has no header row.")

                    headers_norm = [self._normalize_header(h) for h in raw_headers]
                    headers_norm = self._dedupe_headers(headers_norm)
                    target_map = self._build_header_map(headers_norm)

                    # 4) Start a transaction on the **worker connection**
                    cur = conn.cursor()
                    cur.execute("BEGIN")

                    have_upsert = True
                    upsert_sql = """
                        INSERT INTO products (sku, name, price, stock, category, status, image_path, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sku) DO UPDATE SET
                        name=excluded.name,
                        price=excluded.price,
                        stock=excluded.stock,
                        category=excluded.category,
                        status=excluded.status,
                        image_path=excluded.image_path,
                        description=excluded.description
                    """

                    batch, BATCH_SIZE = [], 500
                    inserted = updated = skipped = 0
                    error_lines = []
                    line_no = 1

                    # Re-create reader to start after header
                    text.seek(0)
                    reader = csv.reader(text, dialect=dialect)
                    _ = next(reader, None)

                    def flush_batch():
                        nonlocal inserted, updated,have_upsert
                        if not batch:
                            return
                        try:
                            if have_upsert:
                                cur.executemany(upsert_sql, batch)
                            else:
                                # (fallback manual upsert here if needed)
                                pass
                        except sqlite3.OperationalError:
                            # SQLite too old for ON CONFLICT -> manual path
                            nonlocal have_upsert
                            have_upsert = False
                            for tpl in batch:
                                sku = tpl[0]
                                cur.execute("SELECT id FROM products WHERE sku=?", (sku,))
                                if cur.fetchone():
                                    cur.execute("""
                                        UPDATE products
                                        SET name=?, price=?, stock=?, category=?, status=?, image_path=?, description=?
                                        WHERE sku=?""",
                                        (tpl[1], tpl[2], tpl[3], tpl[4], tpl[5], tpl[6], tpl[7], sku)
                                    )
                                    updated += 1
                                else:
                                    cur.execute("""
                                        INSERT INTO products (sku, name, price, stock, category, status, image_path, description)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", tpl)
                                    inserted += 1
                        batch.clear()

                    for row in reader:
                        line_no += 1
                        try:
                            vals = [self._sanitize_cell(row[i]) if i < len(row) else "" for i in range(len(headers_norm))]
                            def get_by_target(t):
                                idx = target_map.get(t, None)
                                return vals[idx] if idx is not None and idx < len(vals) else ""

                            sku = get_by_target("sku")
                            name = get_by_target("name")
                            if not sku or not name:
                                skipped += 1
                                error_lines.append(f"[Line {line_no}] Missing SKU or Name; row skipped.")
                                continue

                            price = self._to_float(get_by_target("price"))
                            stock = self._to_int(get_by_target("stock"))
                            category = get_by_target("category")
                            status = get_by_target("status")
                            image_path = get_by_target("image_path")
                            description = get_by_target("description")

                            batch.append((sku, name, price, stock, category, status, image_path, description))
                            if len(batch) >= BATCH_SIZE:
                                flush_batch()
                        except Exception as e:
                            skipped += 1
                            error_lines.append(f"[Line {line_no}] {e}")

                    flush_batch()
                    conn.commit()

                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    # bounce error UI back to main thread
                    self.root.after(0, lambda: messagebox.showerror("Import CSV", f"Failed to import:\n{e}"))
                finally:
                    try:
                        text.detach()
                    except Exception:
                        pass
                    try:
                        fh.close()
                    except Exception:
                        pass

                # UI refresh must be in main thread
                self.root.after(0, self._load_data)
                self.root.after(0, lambda: self._set_status("Import complete"))
            finally:
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass

        # IMPORTANT: start the thread!
        threading.Thread(target=worker, daemon=True).start()


    def _after_import(self, inserted, updated, errors):
        self._load_data()
        self._set_status(f"Import complete: {inserted} inserted, {updated} updated, {errors} errors")

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Save visible page as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        start, end = self._page_slice()
        rows = self.filtered_data[start:end]
        headers = ["sku", "name", "price", "stock", "category", "status", "image_path", "description"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in rows:
                    writer.writerow([r.get(h, "") for h in headers])
            self._set_status(f"Exported {len(rows)} rows")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export:\n{e}")

    # ---------- DETAIL / EDIT ----------
    def _open_detail_dialog(self, product_row):
        d = tk.Toplevel(self.root)
        d.title(f"Product Detail – {product_row.get('sku') or ''}")
        d.configure(bg=self.colors["bg"])
        d.geometry("600x520")
        d.transient(self.root)
        d.grab_set()

        def mk_row(parent, label, var):
            fr = tk.Frame(parent, bg=self.colors["bg"])
            fr.pack(fill="x", padx=16, pady=6)
            tk.Label(fr, text=label, bg=self.colors["bg"], fg=self.colors["fg_muted"], width=12, anchor="w").pack(side="left")
            ent = ttk.Entry(fr, textvariable=var)
            ent.pack(side="left", fill="x", expand=True)
            return ent

        # Variables
        v_sku = tk.StringVar(value=product_row.get("sku") or "")
        v_name = tk.StringVar(value=product_row.get("name") or "")
        v_price = tk.StringVar(value=str(product_row.get("price") if product_row.get("price") is not None else "0.0"))
        v_stock = tk.StringVar(value=str(product_row.get("stock") if product_row.get("stock") is not None else "0"))
        v_category = tk.StringVar(value=product_row.get("category") or "")
        v_status = tk.StringVar(value=product_row.get("status") or "")
        v_image = tk.StringVar(value=product_row.get("image_path") or "")
        v_desc = tk.Text(d, height=6, wrap="word", bg=self.colors["bg2"], fg=self.colors["fg"])

        # Layout
        tk.Label(d, text="Edit Product", bg=self.colors["bg"], fg=self.colors["fg"], font=("Segoe UI", 12, "bold")).pack(padx=16, pady=(16, 4), anchor="w")

        mk_row(d, "SKU", v_sku).configure(state="disabled")
        mk_row(d, "Name", v_name)
        mk_row(d, "Price", v_price)
        mk_row(d, "Stock", v_stock)
        mk_row(d, "Category", v_category)
        mk_row(d, "Status", v_status)
        mk_row(d, "Image Path", v_image)

        desc_frame = tk.Frame(d, bg=self.colors["bg"])
        desc_frame.pack(fill="both", expand=False, padx=16, pady=6)
        tk.Label(desc_frame, text="Description", bg=self.colors["bg"], fg=self.colors["fg_muted"], width=12, anchor="w").pack(side="top", anchor="w")
        v_desc.pack(in_=desc_frame, fill="x")
        v_desc.delete("1.0", "end")
        v_desc.insert("1.0", product_row.get("description") or "")

        # Buttons
        btns = tk.Frame(d, bg=self.colors["bg"])
        btns.pack(fill="x", padx=16, pady=12)
        ttk.Button(btns, text="Save", command=lambda: self._save_product(d, product_row["id"], v_name, v_price, v_stock, v_category, v_status, v_image, v_desc)).pack(side="left")
        ttk.Button(btns, text="Delete", command=lambda: self._delete_product(d, product_row["id"])).pack(side="left", padx=8)
        ttk.Button(btns, text="Close", command=d.destroy).pack(side="right")

    def _save_product(self, dialog, pid, v_name, v_price, v_stock, v_category, v_status, v_image, v_desc):
        try:
            price = float(v_price.get().strip())
        except Exception:
            messagebox.showerror("Validate", "Price must be a number.")
            return
        try:
            stock = int(float(v_stock.get().strip()))
        except Exception:
            messagebox.showerror("Validate", "Stock must be an integer.")
            return

        cur = self.conn.cursor()
        cur.execute("""
            UPDATE products
            SET name=?, price=?, stock=?, category=?, status=?, image_path=?, description=?
            WHERE id=?
        """, (
            v_name.get().strip(),
            price,
            stock,
            v_category.get().strip(),
            v_status.get().strip(),
            v_image.get().strip(),
            v_desc.get("1.0", "end").strip(),
            pid
        ))
        self.conn.commit()
        self._set_status("Saved")
        dialog.destroy()
        self._load_data()  # refresh table/cards
        # Clear cached image so changes reflect
        if pid in self.image_cache:
            del self.image_cache[pid]

    def _delete_product(self, dialog, pid):
        if not messagebox.askyesno("Delete Product", "Are you sure you want to delete this product?"):
            return
        cur = self.conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (pid,))
        self.conn.commit()
        self._set_status("Deleted")
        dialog.destroy()
        self._load_data()

    # ---------- UTIL ----------
    def _set_status(self, text):
        self.status_label.config(text=text)


if __name__ == "__main__":
    root = tk.Tk()
    app = ProductDashboard(root)
    root.mainloop()
