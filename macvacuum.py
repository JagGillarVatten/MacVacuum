import os, subprocess, tkinter as tk, sys, shutil, concurrent.futures, threading, psutil
from tkinter import ttk, messagebox, filedialog
from functools import partial

try:
    import send2trash
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "send2trash"])
    import send2trash

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

    def configure_styles(self):
        self.style.configure("TButton", padding=5, font=("Helvetica", 10))
        self.style.configure("TNotebook", background="#f0f0f0")
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Helvetica", 10))
        self.style.configure("Treeview", rowheight=25, font=("Helvetica", 10))
        self.style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))
        self.style.configure("TProgressbar", thickness=20)

    def setup_tabs(self):
        tabs = [("Scan", self.setup_scan_tab), ("System", self.setup_system_tab),
                ("Disk", self.setup_disk_usage_tab), ("Help", self.setup_help_tab)]
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
        self.result_tree = ttk.Treeview(tab, columns=("Type", "Path", "Size"), show="headings", selectmode="extended")
        for col in ("Type", "Path", "Size"):
            self.result_tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(c, False))
            self.result_tree.column(col, width=100)
        self.result_tree.column("Path", width=300)
        self.result_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="Clean Selected", command=self.clean_selected).pack(pady=5)
        ttk.Button(tab, text="Stop Scan", command=self.stop_scan).pack(pady=5)

    def setup_system_tab(self, tab):
        self.system_info_text = tk.Text(tab, wrap=tk.WORD, font=("Helvetica", 10), bg="#f03324")
        self.system_info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_system_info()

    def setup_disk_usage_tab(self, tab):
        self.disk_usage_frame = ttk.Frame(tab)
        self.disk_usage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_disk_usage()

    def setup_help_tab(self, tab):
        help_text = "MacVacuum - Disk Space Optimizer\n\nQuick Scan: Common locations\nDeep Scan: Entire system\nCustom Scan: Select directories\nClean Selected: Remove items\nStop Scan: Halt process\n\nWarning: Use carefully"
        ttk.Label(tab, text=help_text, wraplength=500, justify="left").pack(padx=20, pady=20)

    def start_custom_scan(self):
        directory = filedialog.askdirectory()
        if directory:
            self.start_scan([directory])

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
                    file_size = os.path.getsize(file_path)
                    if file_size > 600 * 1024 * 1024 or file == '.DS_Store':
                        results.append((("DS_Store" if file == '.DS_Store' else "Large File"), file_path, self.format_size(file_size)))
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

    def update_system_info(self):
        self.system_info_text.delete(1.0, tk.END)
        self.system_info_text.insert(tk.END, subprocess.check_output(["system_profiler", "SPHardwareDataType"]).decode())
        cpu_usage, memory = psutil.cpu_percent(interval=1), psutil.virtual_memory()
        self.system_info_text.insert(tk.END, f"\nCPU: {cpu_usage}%\nMemory: {self.format_size(memory.used)} / {self.format_size(memory.total)} ({memory.percent}%)\n")
        self.root.after(5000, self.update_system_info)

    def update_disk_usage(self):
        for widget in self.disk_usage_frame.winfo_children():
            widget.destroy()
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                ttk.Label(self.disk_usage_frame, text=f"{partition.device} ({partition.mountpoint}):").pack(anchor="w", pady=(10, 5))
                ttk.Progressbar(self.disk_usage_frame, length=300, value=usage.percent).pack(anchor="w")
                ttk.Label(self.disk_usage_frame, text=f"Used: {self.format_size(usage.used)} / {self.format_size(usage.total)} ({usage.percent}%)").pack(anchor="w", pady=(5, 10))
            except PermissionError:
                continue
        self.root.after(60000, self.update_disk_usage)

    def stop_scan(self):
        self.scanning = False

    def treeview_sort_column(self, col, reverse):
        l = [(self.result_tree.set(k, col), k) for k in self.result_tree.get_children('')]
        l.sort(reverse=reverse)
        for index, (_, k) in enumerate(l):
            self.result_tree.move(k, '', index)
        self.result_tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

if __name__ == "__main__":
    root = tk.Tk()
    app = MacVacuum(root)
    root.mainloop()
