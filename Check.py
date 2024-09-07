import tkinter as tk
from tkinter import ttk
import requests
import threading
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pyperclip  # Import pyperclip for clipboard functionality
import os  # Import os to check for file existence

# Event to control the crawling process
stop_event = threading.Event()

# Fallback headers if the latest headers cannot be fetched
fallback_headers = [
    {"name": "Cache-Control", "value": "no-store, max-age=0"},
    {"name": "Clear-Site-Data", "value": "\"cache\",\"cookies\",\"storage\""},
    {"name": "Content-Security-Policy", "value": "default-src 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; upgrade-insecure-requests; block-all-mixed-content"},
    {"name": "Cross-Origin-Embedder-Policy", "value": "require-corp"},
    {"name": "Cross-Origin-Opener-Policy", "value": "same-origin"},
    {"name": "Cross-Origin-Resource-Policy", "value": "same-origin"},
    {"name": "Permissions-Policy", "value": "accelerometer=(), autoplay=(), camera=(), cross-origin-isolated=(), display-capture=(), encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), midi=(), payment=(), picture-in-picture=(), publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(self), usb=(), web-share=(), xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(), gamepad=(), hid=(), idle-detection=(), interest-cohort=(), serial=(), unload=()"},
    {"name": "Referrer-Policy", "value": "no-referrer"},
    {"name": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains"},
    {"name": "X-Content-Type-Options", "value": "nosniff"},
    {"name": "X-Frame-Options", "value": "deny"},
    {"name": "X-Permitted-Cross-Domain-Policies", "value": "none"}
]

# Custom headers to use for requests
custom_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br"
}

# Function to fetch the latest OWASP headers from the JSON URL
def fetch_latest_headers():
    try:
        response = requests.get("https://owasp.org/www-project-secure-headers/ci/headers_add.json", timeout=5)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        
        # Check if the expected keys are in the response
        if "headers" in data and "last_update_utc" in data:
            return data["headers"], data["last_update_utc"]
        else:
            # If the structure is not as expected, return an empty list and None
            return [], None
    except requests.RequestException as e:
        print(f"Error fetching headers: {e}")  # Log the error for debugging
        return [], None

# Function to check headers for a given URL without following redirects
def check_headers(url):
    try:
        response = requests.get(url, headers=custom_headers, timeout=5, allow_redirects=False)  # Use custom headers
        return {k.lower().strip(): v for k, v in response.headers.items()}  # Convert header names to lowercase and strip whitespace
    except requests.RequestException:
        return {}

def crawl(url, crawl_time, headers):
    start_time = time.time()
    initial_headers = check_headers(url)
    
    # Check if the initial headers were fetched successfully
    if not initial_headers:
        status_label.config(text=f"Could not fetch headers from {url}.")
        return

    initial_results = []

    for header in headers:
        header_name = header["name"].lower().strip()  # Convert to lowercase and strip whitespace
        status = "Missing" if header_name not in initial_headers else "OK"
        initial_results.append((url, header["name"], status))  # Keep original case for display

    # Insert initial results into the treeview
    for header in initial_results:
        tree.insert("", "end", values=header)

    # Add a separator line
    tree.insert("", "end", values=("---------", "---------", "---------"))

    # Fetch the page content and find all links
    try:
        response = requests.get(url, headers=custom_headers, timeout=5)  # Use custom headers
        soup = BeautifulSoup(response.content, 'lxml')
        links = {a['href'] for a in soup.find_all('a', href=True)}  # Extract unique links
    except requests.RequestException:
        status_label.config(text=f"Could not fetch links from {url}.")
        return

    # Get the base domain to limit crawling to the same domain
    base_domain = urlparse(url).netloc

    # Check for meta tags
    meta_tags = {meta.get('name', '').lower(): meta.get('content', '') for meta in soup.find_all('meta')}

    # Crawl the found links and compare results
    for link in links:
        # Construct the full URL
        full_url = urljoin(url, link)  # This handles relative URLs correctly

        # Check if the full URL is within the same domain
        if urlparse(full_url).netloc != base_domain:
            continue  # Skip URLs that are outside the scope

        remaining_time = crawl_time - (time.time() - start_time)

        # Update status label
        update_status(full_url, max(0, int(remaining_time)))

        if remaining_time <= 0 or stop_event.is_set():
            break  # Stop if the crawl time is exceeded or stop event is set

        # Check headers for the crawled URL (allowing redirects)
        crawled_headers = check_headers(full_url)

        # Only proceed if the headers were fetched successfully
        if crawled_headers:
            for header in headers:
                header_name = header["name"].lower().strip()  # Convert to lowercase and strip whitespace
                initial_status = "Missing" if header_name not in initial_headers else "OK"
                crawled_status = "Missing" if header_name not in crawled_headers else "OK"

                # Check if the header is missing but present in meta tags
                if initial_status == "Missing" and header_name in meta_tags:
                    crawled_status = f"Missing (in meta: {meta_tags[header_name]})"

                # Only print if the status differs from the initial test
                if initial_status != crawled_status:
                    tree.insert("", "end", values=(full_url, header["name"], crawled_status))  # Keep original case for display

        time.sleep(1)  # Simulate a delay for each request

    # Reset status label after crawling
    status_label.config(text="Crawling complete.")


def update_status(full_url, remaining_time):
    status_label.config(text=f"Testing: {full_url} | Remaining Time: {remaining_time} seconds")

def on_check():
    url = url_entry.get().strip()  # Get the URL and strip any leading/trailing whitespace
    try:
        crawl_time = int(time_entry.get())
    except ValueError:
        status_label.config(text="Please enter a valid number for crawl time.")
        return

    if not url:
        status_label.config(text="Please enter a URL.")
        return

    # Check if the URL starts with http:// or https://
    if not url.startswith(("http://", "https://")):
        url = "https://" + url  # Default to https
        status_label.config(text=f"Protocol not specified. Defaulting to: {url}")

    # Clear previous results
    for row in tree.get_children():
        tree.delete(row)

    # Reset the stop event
    stop_event.clear()

    # Fetch the latest headers
    headers, last_update = fetch_latest_headers()
    if not headers:
        # If fetching headers fails, use fallback headers
        status_label.config(text="Could not fetch the latest headers. Using fallback headers.")
        headers = fallback_headers
        last_update = "Fallback headers in use."

    # Update the headers label with the last update date only
    headers_label.config(text=f"Using headers from: {last_update}")

    # Start crawling in a separate thread
    threading.Thread(target=crawl, args=(url, crawl_time, headers)).start()

def on_stop():
    stop_event.set()  # Signal the crawling thread to stop

def sort_treeview(column, reverse):
    """Sort the treeview based on the selected column."""
    # Get the data from the treeview
    data = [(tree.item(item)["values"], item) for item in tree.get_children()]
    
    # Sort the data
    data.sort(key=lambda x: x[0][column], reverse=reverse)

    # Reinsert the sorted data into the treeview
    for index, (values, item) in enumerate(data):
        tree.move(item, '', index)

    # Toggle the sort order for the next click
    tree.heading(column, command=lambda: sort_treeview(column, not reverse))

def copy_to_clipboard(text):
    """Copy the given text to the clipboard."""
    pyperclip.copy(text)

def show_context_menu(event):
    """Show the context menu on right-click for the treeview."""
    try:
        # Get the selected item
        item = tree.selection()[0]
        values = tree.item(item, "values")
        
        # Update the context menu options
        copy_url_menu.entryconfig(0, command=lambda: copy_to_clipboard(values[0]))  # Copy URL
        copy_url_menu.entryconfig(1, command=lambda: copy_to_clipboard(values[1]))  # Copy Header Name
        copy_url_menu.entryconfig(2, command=lambda: copy_to_clipboard(values[2]))  # Copy Status
        
        # Display the context menu
        copy_url_menu.post(event.x_root, event.y_root)
    except IndexError:
        pass  # No item selected

# Create the main window
root = tk.Tk()
root.title("OWASP Security Header Checker")
root.geometry("800x600")  # Set a modern window size

# Check if icon.ico exists and set it as the window icon
icon_path = os.path.abspath("icon.ico")
if os.path.isfile(icon_path):
    try:
        root.iconbitmap(icon_path)  # Try to set the icon using iconbitmap
    except tk.TclError:
        print("Failed to set icon using iconbitmap. Trying iconphoto instead.")
        try:
            icon_image = tk.PhotoImage(file=icon_path)  # Use PhotoImage for PNG or GIF
            root.iconphoto(False, icon_image)
        except Exception as e:
            print(f"Failed to set icon using iconphoto: {e}")

# Configure grid weights for resizing
root.grid_rowconfigure(5, weight=1)  # Make the treeview row expandable
root.grid_columnconfigure(1, weight=1)  # Make the second column expandable

# URL input
tk.Label(root, text="URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

# Crawl Time input
tk.Label(root, text="Crawl Time (Seconds):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
time_entry = tk.Entry(root)
time_entry.insert(0, "30")  # Default time
time_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

# Button frame for modern layout
button_frame = ttk.Frame(root)
button_frame.grid(row=2, column=0, columnspan=2, pady=10)

# Check button
check_button = ttk.Button(button_frame, text="Check Headers", command=on_check)
check_button.pack(side=tk.LEFT, padx=5)

# Stop button
stop_button = ttk.Button(button_frame, text="Stop Check", command=on_stop)
stop_button.pack(side=tk.LEFT, padx=5)

# Status label
status_label = tk.Label(root, text="")
status_label.grid(row=3, column=0, columnspan=2, pady=10)

# Headers label for displaying the last update date only
headers_label = tk.Label(root, text="")
headers_label.grid(row=4, column=0, columnspan=2, pady=10)

# Treeview for displaying results
columns = ("Tested URL", "Header Name", "Status")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.heading("Tested URL", text="Tested URL", command=lambda: sort_treeview(0, False))
tree.heading("Header Name", text="Header Name", command=lambda: sort_treeview(1, False))
tree.heading("Status", text="Status", command=lambda: sort_treeview(2, False))
tree.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

# Create a context menu for the treeview
copy_url_menu = tk.Menu(root, tearoff=0)
copy_url_menu.add_command(label="Copy URL")
copy_url_menu.add_command(label="Copy Header Name")
copy_url_menu.add_command(label="Copy Status")

# Bind the right-click event to show the context menu for the treeview
tree.bind("<Button-3>", show_context_menu)

# Create a context menu for the URL entry
url_context_menu = tk.Menu(root, tearoff=0)
url_context_menu.add_command(label="Copy", command=lambda: copy_to_clipboard(url_entry.get()))
url_context_menu.add_command(label="Paste", command=lambda: url_entry.insert(tk.END, pyperclip.paste()))

# Function to show the context menu for the URL entry
def show_url_context_menu(event):
    url_context_menu.post(event.x_root, event.y_root)

# Bind the right-click event to show the context menu for the URL entry
url_entry.bind("<Button-3>", show_url_context_menu)

# Start the GUI event loop
root.mainloop()
