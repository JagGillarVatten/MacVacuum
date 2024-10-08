import os
import subprocess
import tkinter as tk
import sys
import shutil
import concurrent.futures
import threading
import psutil
from tkinter import ttk, messagebox, filedialog
from functools import partial
import time
import re

def import_send2trash():
    try:
        import send2trash
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "send2trash"])
        import send2trash
    return send2trash

send2trash = import_send2trash()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MacVacuum:
    def __init__(self, root):
        self.root = root
        self.root.title("MacVacuum")
        self.root.geometry("800x600")
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.scan_results, self.scanning = [], False
        self.progress_var = tk.DoubleVar()
        self.setup_tabs()
        self.last_scan_time = None
        self.duplicate_files = {}
        self.file_categories = {
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            'Videos': ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
            'Audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }

    def configure_styles(self):
        self.style.configure("TButton", padding=5, font=("Helvetica", 10))
        self.style.configure("TNotebook", background="#f0f0f0")
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Helvetica", 10))
        self.style.configure("Treeview", rowheight=25, font=("Helvetica", 10))
        self.style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))
        self.style.configure("TProgressbar", thickness=20)

    def setup_tabs(self):
        tabs = [("Scan", self.setup_scan_tab), ("System", self.setup_system_tab),
                ("Disk", self.setup_disk_usage_tab), ("Help", self.setup_help_tab),
                ("Duplicates", self.setup_duplicates_tab), ("Categories", self.setup_categories_tab)]
        for name, setup in tabs:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=name)
            setup(tab)

    def setup_scan_tab(self, tab):
        ttk.Button(tab, text="Quick Scan", command=lambda: self.start_scan([os.path.expanduser("~/Downloads"), os.path.expanduser("~/Desktop"), "/tmp", "/var/tmp"])).pack(pady=5)
        ttk.Button(tab, text="Deep Scan", command=lambda: self.start_scan([os.path.expanduser("~")])).pack(pady=5)
        ttk.Button(tab, text="Custom Scan", command=self.start_custom_scan).pack(pady=5)
        self.progress_bar = ttk.Progressbar(tab, variable=self.progress_var, length=300)
        self.progress_bar.pack(pady=10)
        self.result_tree = ttk.Treeview(tab, columns=("Type", "Path", "Size", "Last Modified"), show="headings", selectmode="extended")
        for col in ("Type", "Path", "Size", "Last Modified"):
            self.result_tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(c, False))
            self.result_tree.column(col, width=100)
        self.result_tree.column("Path", width=300)
        self.result_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="Clean Selected", command=self.clean_selected).pack(pady=5)
        ttk.Button(tab, text="Stop Scan", command=self.stop_scan).pack(pady=5)
        ttk.Button(tab, text="Schedule Scan", command=self.schedule_scan).pack(pady=5)

    def setup_duplicates_tab(self, tab):
        self.duplicates_tree = ttk.Treeview(tab, columns=("File", "Size", "Duplicates"), show="headings", selectmode="extended")
        for col in ("File", "Size", "Duplicates"):
            self.duplicates_tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(c, False))
            self.duplicates_tree.column(col, width=100)
        self.duplicates_tree.column("File", width=300)
        self.duplicates_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="Find Duplicates", command=self.find_duplicates).pack(pady=5)
        ttk.Button(tab, text="Remove Selected Duplicates", command=self.remove_selected_duplicates).pack(pady=5)

    def setup_categories_tab(self, tab):
        self.categories_tree = ttk.Treeview(tab, columns=("Category", "Count", "Total Size"), show="headings", selectmode="extended")
        for col in ("Category", "Count", "Total Size"):
            self.categories_tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(c, False))
            self.categories_tree.column(col, width=100)
        self.categories_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="Analyze Categories", command=self.analyze_categories).pack(pady=5)

    def start_scan(self, locations):
        if self.scanning:
            messagebox.showinfo("Scan in Progress", "Please wait or stop the current scan.")
            return
        self.scan_results.clear()
        self.result_tree.delete(*self.result_tree.get_children())
        self.scanning = True
        self.progress_var.set(0)
        threading.Thread(target=self.scan_thread, args=(locations,), daemon=True).start()

    def scan_thread(self, locations):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.scan_directory, location) for location in locations]
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                if not self.scanning:
                    break
                self.scan_results.extend(future.result())
                self.progress_var.set((i / len(futures)) * 100)
        self.scanning = False
        self.last_scan_time = time.time()
        self.root.after(0, self.update_result_tree)

    def scan_directory(self, directory):
        results = []
        for root, _, files in os.walk(directory):
            if not self.scanning:
                break
            for file in files:
                if not self.scanning:
                    break
                file_path = os.path.join(root, file)
                try:
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    last_modified = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_mtime))
                    if file_size > 600 * 1024 * 1024 or file == '.DS_Store':
                        results.append(("DS_Store" if file == '.DS_Store' else "Large File", file_path, self.format_size(file_size), last_modified))
                except OSError:
                    continue
        return results

    def update_result_tree(self):
        for item in self.scan_results:
            self.result_tree.insert("", "end", values=item)

    def clean_selected(self):
        selected_items = self.result_tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select items to clean.")
            return
        if messagebox.askyesno("Confirm Deletion", "Delete selected items?"):
            for item in selected_items:
                try:
                    send2trash.send2trash(self.result_tree.item(item)['values'][1])
                    self.result_tree.delete(item)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {self.result_tree.item(item)['values'][1]}: {str(e)}")

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def schedule_scan(self):
        interval = simpledialog.askinteger("Schedule Scan", "Enter scan interval in hours:", minvalue=1, maxvalue=168)
        if interval:
            threading.Thread(target=self.scheduled_scan_thread, args=(interval,), daemon=True).start()

    def scheduled_scan_thread(self, interval):
        while True:
            time.sleep(interval * 3600)
            self.start_scan([os.path.expanduser("~")])

    def find_duplicates(self):
        self.duplicate_files.clear()
        self.duplicates_tree.delete(*self.duplicates_tree.get_children())
        for item in self.scan_results:
            file_path = item[1]
            file_size = os.path.getsize(file_path)
            file_hash = self.get_file_hash(file_path)
            if file_hash in self.duplicate_files:
                self.duplicate_files[file_hash].append(file_path)
            else:
                self.duplicate_files[file_hash] = [file_path]
        
        for file_hash, file_list in self.duplicate_files.items():
            if len(file_list) > 1:
                self.duplicates_tree.insert("", "end", values=(file_list[0], self.format_size(os.path.getsize(file_list[0])), len(file_list)))

    def get_file_hash(self, file_path):
        import hashlib
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    def remove_selected_duplicates(self):
        selected_items = self.duplicates_tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select duplicate items to remove.")
            return
        if messagebox.askyesno("Confirm Deletion", "Delete selected duplicate items?"):
            for item in selected_items:
                file_path = self.duplicates_tree.item(item)['values'][0]
                file_hash = self.get_file_hash(file_path)
                duplicate_list = self.duplicate_files[file_hash]
                for dup_file in duplicate_list[1:]:
                    try:
                        send2trash.send2trash(dup_file)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete {dup_file}: {str(e)}")
                self.duplicates_tree.delete(item)

    def analyze_categories(self):
        self.categories_tree.delete(*self.categories_tree.get_children())
        category_stats = {category: {'count': 0, 'size': 0} for category in self.file_categories}
        
        for item in self.scan_results:
            file_path = item[1]
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            for category, extensions in self.file_categories.items():
                if file_ext in extensions:
                    category_stats[category]['count'] += 1
                    category_stats[category]['size'] += file_size
                    break
            else:
                if 'Other' not in category_stats:
                    category_stats['Other'] = {'count': 0, 'size': 0}
                category_stats['Other']['count'] += 1
                category_stats['Other']['size'] += file_size
        
        for category, stats in category_stats.items():
            self.categories_tree.insert("", "end", values=(category, stats['count'], self.format_size(stats['size'])))

    def treeview_sort_column(self, col, reverse):
        l = [(self.result_tree.set(k, col), k) for k in self.result_tree.get_children('')]
        l.sort(key=lambda t: self.natural_keys(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(l):
            self.result_tree.move(k, '', index)
        self.result_tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

    def natural_keys(self, text):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    os.chdir(application_path)

    root = tk.Tk()
    app = MacVacuum(root)
    root.mainloop()
