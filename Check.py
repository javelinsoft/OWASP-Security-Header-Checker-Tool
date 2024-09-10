import tkinter as tk
from tkinter import ttk
import requests
import threading
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pyperclip
import os
import json

# Event to control the crawling process
stop_event = threading.Event()

# Custom headers to use for requests
custom_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": ""
}


def read_headers_to_remove_from_file():
    """Read headers that need to be removed from the headers_remove.json file."""
    try:
        with open("headers_remove.json", "r") as file:
            data = json.load(file)
            if "headers" in data and "last_update_utc" in data:
                return data["headers"], data["last_update_utc"]
            else:
                return [], None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading headers to remove from file: {e}")
        return [], None


def read_headers_from_file():
    """Read headers from the headers_add.json file."""
    try:
        with open("headers_add.json", "r") as file:
            data = json.load(file)
            if "headers" in data and "last_update_utc" in data:
                return data["headers"], data["last_update_utc"]
            else:
                return [], None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading headers from file: {e}")
        return [], None

def check_headers(url):
    """Check headers for a given URL without following redirects."""
    try:
        response = requests.get(url, headers=custom_headers, timeout=5, allow_redirects=False)
        return {k.lower().strip(): v for k, v in response.headers.items()}
    except requests.RequestException:
        return {}
def crawl(url, crawl_time, headers):
    """Crawl the given URL and check headers."""
    start_time = time.time()
    
    # Read headers to remove
    remove_headers, last_update_remove = read_headers_to_remove_from_file()
    if remove_headers:
        headers_label.config(text=f"Using headers to remove from: {last_update_remove}")

    # Check headers and track time taken for the initial request
    initial_request_start = time.time()
    initial_headers = check_headers(url)
    initial_request_duration = time.time() - initial_request_start

    if not initial_headers:
        update_status(f"Could not fetch headers from {url}.")
        return

    # Check for duplicate headers in the initial response
    duplicate_initial_headers = {}
    for header in initial_headers:
        header_name = header.lower().strip()
        if header_name in duplicate_initial_headers:
            duplicate_initial_headers[header_name] += 1
        else:
            duplicate_initial_headers[header_name] = 1

    initial_results = []

    for header in headers:
        header_name = header["name"].lower().strip()
        if header_name not in initial_headers:
            status = "Missing"
            value = ""  # No value if header is missing
        else:
            # Check for duplicates
            if duplicate_initial_headers[header_name] > 1:
                status = f"Duplicate (Count: {duplicate_initial_headers[header_name]})"
            else:
                status = "Present"
            value = initial_headers[header_name]  # Get the actual header value
        
        initial_results.append((url, header["name"], status, value))  # Include value here

    for header in initial_results:
        # Use tags based on status
        tag = "missing" if header[2] == "Missing" else "present" if "Duplicate" not in header[2] else "duplicate"
        tree.insert("", "end", values=(header[0], header[1], header[2], header[3]), tags=(tag,))

    # Check headers for removal
    for header_name in remove_headers:
        header_name_lower = header_name.lower().strip()
        if header_name_lower in initial_headers:
            value = initial_headers[header_name_lower]
            tree.insert("", "end", values=(url, header_name, "Should be removed", value), tags=("remove",))

    tree.insert("", "end", values=("---------", "---------", "---------", "---------"))

    try:
        response = requests.get(url, headers=custom_headers, timeout=5)
        soup = BeautifulSoup(response.content, 'lxml')
        links = {a['href'] for a in soup.find_all('a', href=True)}
    except requests.RequestException:
        update_status(f"Could not fetch links from {url}.")
        return

    base_domain = urlparse(url).netloc

    # Calculate remaining time for crawling
    remaining_time = crawl_time - initial_request_duration
    if remaining_time <= 0:
        update_status("Crawl time exceeded during initial request.")
        return

    for link in links:
        full_url = urljoin(url, link)

        # Skip the main URL if found in the page
        if full_url == url:
            continue

        if urlparse(full_url).netloc != base_domain:
            continue

        # Update remaining time after each link check
        elapsed_time = time.time() - start_time
        remaining_time = crawl_time - elapsed_time
        update_status(f"Testing: {full_url} | Remaining Time: {max(0, int(remaining_time))} seconds")

        if remaining_time <= 0 or stop_event.is_set():
            break

        try:
            crawled_response = requests.get(full_url, headers=custom_headers, timeout=5)
            crawled_headers = {k.lower().strip(): v for k, v in crawled_response.headers.items()}
            # Check for duplicate headers
            duplicate_headers = {}
            for header in crawled_response.headers:
                header_name = header.lower().strip()
                if header_name in duplicate_headers:
                    duplicate_headers[header_name] += 1
                else:
                    duplicate_headers[header_name] = 1
        except requests.RequestException:
            continue

        if crawled_headers:
            for header in headers:
                header_name = header["name"].lower().strip()
                initial_status = "Missing" if header_name not in initial_headers else "Present"
                crawled_status = "Missing" if header_name not in crawled_headers else "Present"

                # Check for duplicates in crawled headers
                if header_name in duplicate_headers and duplicate_headers[header_name] > 1:
                    crawled_status = f"Duplicate (Count: {duplicate_headers[header_name]})"

                # Update crawled status if it was missing in the initial request
                if initial_status == "Missing" and crawled_status == "Present":
                    crawled_status = f"Present (Was missing in main URL)"
                # Update crawled status if it was present in the initial request
                elif initial_status == "Present" and crawled_status == "Missing":
                    crawled_status = f"Missing (Was present in main URL)"

                # Use tags based on status
                tag = "missing" if crawled_status.startswith("Missing") else "present" if "Duplicate" not in crawled_status else "duplicate"
                value = crawled_headers.get(header_name, "")  # Get the actual header value or ""
                tree.insert("", "end", values=(full_url, header["name"], crawled_status, value), tags=(tag,))

        time.sleep(1)

    update_status("Crawling complete.")



def update_status(message):
    """Update the status label."""
    status_label.config(text=message)

def start_crawl(url, crawl_time):
    """Start the crawling process in a separate thread."""
    headers, last_update = read_headers_from_file()
    if not headers:
        update_status("Could not fetch the latest headers. No headers available.")
        return

    headers_label.config(text=f"Using headers from: {last_update}")

    # Start the crawling thread
    threading.Thread(target=crawl, args=(url, crawl_time, headers)).start()

def on_check():
    """Handle the Check Headers button click."""
    url = url_entry.get().strip()
    try:
        crawl_time = int(time_entry.get())
    except ValueError:
        update_status("Please enter a valid number for crawl time.")
        return

    if not url:
        update_status("Please enter a URL.")
        return

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        update_status(f"Protocol not specified. Defaulting to: {url}")

    for row in tree.get_children():
        tree.delete(row)

    stop_event.clear()

    # Start the header fetching in a separate thread
    threading.Thread(target=start_crawl, args=(url, crawl_time)).start()

def on_stop():
    """Handle the Stop Check button click."""
    stop_event.set()

def sort_treeview(column, reverse):
    """Sort the treeview based on the selected column."""
    data = [(tree.item(item)["values"], item) for item in tree.get_children()]
    data.sort(key=lambda x: x[0][column], reverse=reverse)

    for index, (values, item) in enumerate(data):
        tree.move(item, '', index)

    tree.heading(column, command=lambda: sort_treeview(column, not reverse))

def copy_to_clipboard(text):
    """Copy the given text to the clipboard."""
    pyperclip.copy(text)

def show_context_menu(event):
    """Show the context menu on right-click for the treeview."""
    try:
        item = tree.selection()[0]
        values = tree.item(item, "values")
        
        copy_url_menu.entryconfig(0, command=lambda: copy_to_clipboard(values[0]))
        copy_url_menu.entryconfig(1, command=lambda: copy_to_clipboard(values[1]))
        copy_url_menu.entryconfig(2, command=lambda: copy_to_clipboard(values[2]))
        copy_url_menu.entryconfig(3, command=lambda: copy_to_clipboard(values[3]))  # Copy Value
        
        copy_url_menu.post(event.x_root, event.y_root)
    except IndexError:
        pass

# Create the main window
root = tk.Tk()
root.title("OWASP Security Header Checker")
root.geometry("800x600")

icon_path = os.path.abspath("icon.ico")
if os.path.isfile(icon_path):
    try:
        root.iconbitmap(icon_path)
    except tk.TclError:
        print("Failed to set icon using iconbitmap. Trying iconphoto instead.")
        try:
            icon_image = tk.PhotoImage(file=icon_path)
            root.iconphoto(False, icon_image)
        except Exception as e:
            print(f"Failed to set icon using iconphoto: {e}")

root.grid_rowconfigure(5, weight=1)
root.grid_columnconfigure(1, weight=1)

tk.Label(root, text="URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

tk.Label(root, text="Crawl Time (Seconds):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
time_entry = tk.Entry(root)
time_entry.insert(0, "30")
time_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

button_frame = ttk.Frame(root)
button_frame.grid(row=2, column=0, columnspan=2, pady=10)

check_button = ttk.Button(button_frame, text="Check Headers", command=on_check)
check_button.pack(side=tk.LEFT, padx=5)

stop_button = ttk.Button(button_frame, text="Stop Check", command=on_stop)
stop_button.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(root, text="")
status_label.grid(row=3, column=0, columnspan=2, pady=10)

headers_label = tk.Label(root, text="")
headers_label.grid(row=4, column=0, columnspan=2, pady=10)

columns = ("Tested URL", "Header Name", "Status", "Value")  # Add "Value" to the columns
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.heading("Tested URL", text="Tested URL", command=lambda: sort_treeview(0, False))
tree.heading("Header Name", text="Header Name", command=lambda: sort_treeview(1, False))
tree.heading("Status", text="Status", command=lambda: sort_treeview(2, False))
tree.heading("Value", text="Value", command=lambda: sort_treeview(3, False))  # Add header for "Value"

# Define tags for colors
tree.tag_configure("missing", foreground="red")
tree.tag_configure("present", foreground="green")
tree.tag_configure("duplicate", foreground="orange")  # New tag for duplicates
tree.tag_configure("remove", foreground="purple")

tree.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

copy_url_menu = tk.Menu(root, tearoff=0)
copy_url_menu.add_command(label="Copy URL")
copy_url_menu.add_command(label="Copy Header Name")
copy_url_menu.add_command(label="Copy Status")
copy_url_menu.add_command(label="Copy Value")  # Add option to copy Value

tree.bind("<Button-3>", show_context_menu)

url_context_menu = tk.Menu(root, tearoff=0)
url_context_menu.add_command(label="Copy", command=lambda: copy_to_clipboard(url_entry.get()))
url_context_menu.add_command(label="Paste", command=lambda: url_entry.insert(tk.END, pyperclip.paste()))

def show_url_context_menu(event):
    url_context_menu.post(event.x_root, event.y_root)

url_entry.bind("<Button-3>", show_url_context_menu)

# Start the GUI event loop
root.mainloop()
