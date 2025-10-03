import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap import Style
import json
import os
import requests
import base64
import time

# Constants
HISTORY_FILE = "request_history.json"
request_history = []

# GUI setup
root = tk.Tk()
style = Style("flatly")
root.title("Postman-Style API Client")
root.geometry("900x650")

# Status bar
status_var = tk.StringVar()
status_bar = ttk.Label(root, textvariable=status_var, anchor="w")
status_bar.pack(side="bottom", fill="x")

def update_status(msg):
    status_var.set(msg)

# Top row
top_frame = ttk.Frame(root, padding=5)
top_frame.pack(fill="x")

method_var = tk.StringVar(value="GET")
method_dropdown = ttk.Combobox(top_frame, textvariable=method_var, values=["GET", "POST", "PATCH", "PUT", "DELETE"], width=8)
method_dropdown.pack(side="left", padx=5)
method_dropdown.configure(style="primary.TCombobox")

url_entry = ttk.Entry(top_frame, width=60)
url_entry.pack(side="left", padx=5)

send_button = ttk.Button(top_frame, text="Send", bootstyle="success", command=lambda: make_request())
send_button.pack(side="left", padx=5)

# Tabs
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# Client Tab
client_tab = ttk.Frame(notebook, padding=10)
notebook.add(client_tab, text="Client")

# Headers Section
headers_frame = ttk.LabelFrame(client_tab, text="Headers (key:value)", padding=5)
headers_frame.pack(fill="x", pady=5)

header_entries = []

def add_header():
    row = ttk.Frame(headers_frame)
    key_entry = ttk.Entry(row, width=20)
    value_entry = ttk.Entry(row, width=30)
    del_button = ttk.Button(row, text="X", width=2, bootstyle="danger", command=lambda: remove_header(row))
    key_entry.pack(side="left", padx=2)
    value_entry.pack(side="left", padx=2)
    del_button.pack(side="left", padx=2)
    row.pack(fill="x", pady=2)
    header_entries.append((key_entry, value_entry))

def remove_header(row):
    for widget in row.winfo_children():
        widget.destroy()
    row.destroy()

add_header_button = ttk.Button(headers_frame, text="Add Header", bootstyle="info", command=add_header)
add_header_button.pack(anchor="w", pady=5)

# Request Body
body_frame = ttk.LabelFrame(client_tab, text="Request Body (JSON)", padding=5)
body_frame.pack(fill="both", expand=True, pady=5)
body_textbox = tk.Text(body_frame, height=10)
body_textbox.pack(fill="both", expand=True)

# Response Section
response_frame = ttk.LabelFrame(client_tab, text="Response", padding=5)
response_frame.pack(fill="both", expand=True, pady=5)
response_textbox = tk.Text(response_frame, wrap="word")
response_textbox.pack(fill="both", expand=True)

# Metrics
metrics_frame = ttk.Frame(client_tab)
metrics_frame.pack(fill="x", pady=5)
response_code_label = ttk.Label(metrics_frame, text="Status Code: ")
response_code_label.pack(side="left", padx=10)
response_time_label = ttk.Label(metrics_frame, text="Time: ")
response_time_label.pack(side="left", padx=10)
response_size_label = ttk.Label(metrics_frame, text="Size: ")
response_size_label.pack(side="left", padx=10)

# Config Tab
config_tab = ttk.Frame(notebook, padding=10)
notebook.add(config_tab, text="Config")

ttk.Label(config_tab, text="Username").pack(anchor="w")
username_entry = ttk.Entry(config_tab)
username_entry.pack(fill="x")

ttk.Label(config_tab, text="Password").pack(anchor="w")
password_entry = ttk.Entry(config_tab, show="*")
password_entry.pack(fill="x")

ttk.Label(config_tab, text="Auth Mode").pack(anchor="w")
auth_mode = tk.StringVar(value="Basic Auth")
ttk.Combobox(config_tab, textvariable=auth_mode, values=["Basic Auth", "Header", "Query Params"]).pack(fill="x")

ssl_var = tk.BooleanVar(value=False)
redirect_var = tk.BooleanVar(value=True)
batch_var = tk.BooleanVar(value=False)
pretty_var = tk.BooleanVar(value=True)

ttk.Checkbutton(config_tab, text="Verify SSL", variable=ssl_var).pack(anchor="w")
ttk.Checkbutton(config_tab, text="Follow Redirects", variable=redirect_var).pack(anchor="w")
ttk.Checkbutton(config_tab, text="Batch Requests", variable=batch_var).pack(anchor="w")
ttk.Checkbutton(config_tab, text="Pretty Print JSON", variable=pretty_var).pack(anchor="w")

ttk.Label(config_tab, text="Theme").pack(anchor="w")
theme_var = tk.StringVar(value="flatly")
ttk.Combobox(config_tab, textvariable=theme_var, values=style.theme_names(), width=20).pack(anchor="w")
ttk.Button(config_tab, text="Apply Theme", command=lambda: style.theme_use(theme_var.get())).pack(anchor="w", pady=5)

# History Tab
history_tab = ttk.Frame(notebook, padding=10)
notebook.add(history_tab, text="History")

history_listbox = tk.Listbox(history_tab, height=20)
history_listbox.pack(side="left", fill="y", padx=5)
history_preview = tk.Text(history_tab, height=20, width=60)
history_preview.pack(side="left", fill="both", expand=True)

def populate_history():
    history_listbox.delete(0, tk.END)
    for req in request_history:
        history_listbox.insert(tk.END, req.get("name", "Unnamed"))

def load_history():
    global request_history
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            request_history = json.load(f)
    populate_history()

def on_history_select(event=None):
    selection = history_listbox.curselection()
    if selection:
        index = selection[0]
        req = request_history[index]
        preview = json.dumps(req, indent=2)
        history_preview.delete("1.0", tk.END)
        history_preview.insert(tk.END, preview)

def export_collection():
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "w") as f:
            json.dump(request_history, f, indent=2)
        update_status(f"Exported collection to {file_path}")

def delete_selected_request():
    selection = history_listbox.curselection()
    if selection:
        index = selection[0]
        del request_history[index]
        with open(HISTORY_FILE, "w") as f:
            json.dump(request_history, f, indent=2)
        populate_history()
        history_preview.delete("1.0", tk.END)

history_listbox.bind("<<ListboxSelect>>", on_history_select)

history_buttons = ttk.Frame(history_tab)
history_buttons.pack(side="bottom", fill="x", pady=5)
ttk.Button(history_buttons, text="Export Collection", command=export_collection).pack(side="left", padx=5)
ttk.Button(history_buttons, text="Delete Selected", command=delete_selected_request).pack(side="left", padx=5)

# Request Logic
def make_request():
    url = url_entry.get()
    method = method_var.get()
    verify = ssl_var.get()
    redirects = redirect_var.get()
    pretty = pretty_var.get()
    user = username_entry.get()
    pwd = password_entry.get()
    mode = auth_mode.get()

    headers = {}
    for key_entry, value_entry in header_entries:
        key = key_entry.get().strip()
        value = value_entry.get().strip()
        if key:
            headers[key] = value

    body_input = body_textbox.get("1.0", tk.END).strip()
    body = None
    if method != "GET" and body_input:
        try:
            body = json.loads(body_input)
        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "Request body is not valid JSON.")
            return
    elif method == "GET":
        body_textbox.config(state="disabled")
    else:
        body_textbox.config(state="normal")

    auth = None
    params = {}
    if mode == "Basic Auth":
        auth = requests.auth.HTTPBasicAuth(user, pwd)
    elif mode == "Header":
        encoded = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif mode == "Query Params":
        params = {"username": user, "password": pwd}

    try:
        start = time.time()
        response = requests.request(method, url, headers=headers, json=body, auth=auth, params=params, verify=verify, allow_redirects=redirects)
        end = time.time()
        duration = round(end - start, 2)
        size = len(response.content)

        response_code_label.config(text=f"Status Code: {response.status_code}", foreground="green")
        response_time_label.config(text=f"Time: {duration}s", foreground="blue")
        response_size_label.config(text=f"Size: {size} bytes", foreground="purple")

        response_textbox.config(state="normal")
        response_textbox.delete("1.0", tk.END)
        if pretty and "application/json" in response.headers.get("Content-Type", ""):
            try:
                formatted = json.dumps(response.json(), indent=4)
                response_textbox.insert(tk.END, formatted)
            except:
                response_textbox.insert(tk.END, response.text)
        else:
            response_textbox.insert(tk.END, response.text)
        response_textbox.config(state="disabled")

        request_history.append({
            "name": f"{method} {url}",
            "url": url,
            "method": method,
            "headers": headers,
            "body": body
        })
        with open(HISTORY_FILE, "w") as f:
            json.dump(request_history, f, indent=2)
        populate_history()

    except Exception as e:
        messagebox.showerror("Request Error", str(e))

load_history()
root.mainloop()
