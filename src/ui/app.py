# Eldorado Offer Placer
# Copyright (c) 2025 André Lamego
# Licensed under Dual License (MIT + Proprietary)
# For commercial use, contact: andreolamego@gmail.com

from __future__ import annotations

import os
import platform
import traceback
import subprocess
import threading
import tkinter as tk
from decimal import Decimal, InvalidOperation
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox, filedialog

from src.core.version import get_version, short_version
from src.core.settings import Settings
from src.core.insercao_service import (
    nova_insercao,
    adicionar_ou_incrementar_item,
    carregar_insercao,
)
from src.core.models import ItemInsercao
from src.core.bot import executar_bot
from src.core.license_client import (
    LicenseConfig,
    LicenseCheckResult,
    load_config,
    save_config,
    verify_license,
)


# =========================
# PALETTE / THEME
# =========================
PALETTE = {
    # main background
    "bg": "#2F2F2F",
    "sidebar_bg": "#373737",
    "content_bg": "#373737",

    # text
    "text_primary": "#F9FAFB",
    "text_secondary": "#9CA3AF",

    # buttons
    "accent": "#E5A000",
    "accent_hover": "#AF7B00",
    "danger": "#EF4444",
    "danger_hover": "#B91C1C",
    "muted": "#4B5563",
    "muted_hover": "#374151",

    # components
    "card_bg": "#414141",
    "entry_bg": "#414141",
    "entry_border": "#2F2F2F",
    "log_bg": "#414141",
}

def apply_widget_colors():
    """Global CTk theme configuration."""
    ctk.set_appearance_mode("dark")
    # no pre-made theme to keep manual control over colors


class BotApp(ctk.CTk):
    """Main window with sidebar menu and Add Offers / Configs screens."""

    def __init__(self):
        super().__init__()
        self.title(f"Eldorado Placer {short_version()}")

        # window icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
        if platform.system() == "Windows" and icon_path.exists():
            self.iconbitmap(default=str(icon_path))
        else:
            # fallback (Linux/macOS)
            icon_png = Path(__file__).parent.parent / "assets" / "icon.png"
            if icon_png.exists():
                self.iconphoto(False, tk.PhotoImage(file=str(icon_png)))

        self.resizable(False, False)
        self.geometry("850x461")

        apply_widget_colors()
        self.configure(fg_color=PALETTE["bg"])

        self.settings = Settings.load()

        # content frames (screens)
        self.add_offers_frame: AddOffersFrame | None = None
        self.config_frame: ConfigFrame | None = None

        self._build_layout()
        self.show_add_offers()  # initial screen

        self._log("Application started.")

    # ------------------------------------------------------------------
    # Main layout: sidebar + content area
    # ------------------------------------------------------------------
    def set_global_font(family="Segoe UI", size=13):
        """Aplica uma fonte global em todos os widgets CustomTkinter."""
        ctk.ThemeManager.theme["CTkFont"]["family"] = "Segoe UI"
        # ctk.ThemeManager.theme["CTkFont"]["size"] = size
    
    def _build_layout(self):
        # main container
        container = ctk.CTkFrame(self, fg_color=PALETTE["bg"])
        container.pack(fill="both", expand=True)

        # sidebar
        sidebar = ctk.CTkFrame(
            container,
            width=200,
            fg_color=PALETTE["sidebar_bg"],
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar buttons (store references)
        self.btn_add_offers = ctk.CTkButton(
            sidebar,
            text="Add Offers",
            command=self.show_add_offers,
            width=150,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )
        self.btn_add_offers.pack(pady=(20, 10))

        self.btn_configs = ctk.CTkButton(
            sidebar,
            text="Configs",
            command=self.show_configs,
            width=150,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        self.btn_configs.pack(pady=0)

        lbl_made = ctk.CTkLabel(
            sidebar,
            text="Made by:\nandrelamego",
            font=ctk.CTkFont(size=12),
            justify="center",
            text_color=PALETTE["text_secondary"],
        )
        lbl_made.pack(side="bottom", pady=(0, 20))

        lbl_logo = ctk.CTkLabel(
            sidebar,
            text="ELDORADADO PLACER",
            font=ctk.CTkFont(size=14, weight="bold"),
            justify="center",
            text_color=PALETTE["text_secondary"],
        )
        lbl_logo.pack(side="bottom", pady=0)

        # content area (right)
        content = ctk.CTkFrame(
            container,
            fg_color=PALETTE["content_bg"],
            corner_radius=0,
        )
        content.pack(side="left", fill="both", expand=True)

        self.content = content

        # instantiate screens, but only show one at a time
        self.add_offers_frame = AddOffersFrame(content, app=self)
        self.config_frame = ConfigFrame(content, app=self)

    # ------------------------------------------------------------------
    # Screen navigation
    # ------------------------------------------------------------------
    def show_add_offers(self):
        """Show Add Offers screen and update button highlight."""
        if self.config_frame:
            self.config_frame.pack_forget()
        if self.add_offers_frame:
            self.add_offers_frame.pack(fill="both", expand=True)
            self.add_offers_frame.update_info()

        # highlight button
        self._highlight_sidebar_button(self.btn_add_offers)


    def show_configs(self):
        """Show Configs screen and update button highlight."""
        if self.add_offers_frame:
            self.add_offers_frame.pack_forget()
        if self.config_frame:
            self.config_frame.pack(fill="both", expand=True)
            self.config_frame.load_from_settings()

        # highlight button
        self._highlight_sidebar_button(self.btn_configs)
        
    def _highlight_sidebar_button(self, active_button):
        """Updates sidebar button colors to show which screen is active."""
        # Reset all buttons
        self.btn_add_offers.configure(
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        self.btn_configs.configure(
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )

        # Highlight the active one
        active_button.configure(
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )

    # ------------------------------------------------------------------
    # Global actions (called by screens)
    # ------------------------------------------------------------------
    def open_insertion_window(self):
        """Opens the New Insert window (brainrots form)."""
        NovaInsercaoWindow(
            master=self,
            settings=self.settings,
            start_bot_callback=self._rodar_bot_thread,
            refresh_main_callback=self._refresh_main_info,
        )

    def clear_csv_file(self):
        """Clears the active CSV file (new empty insertion)."""
        csv_path = nova_insercao(self.settings)
        self._log(f"CSV file cleared: {csv_path}")
        self._refresh_main_info()

    def open_csv_file(self):
        """Opens the active CSV file in an external editor."""
        path = self.settings.csv_ativo_path
        if not path or not Path(path).exists():
            messagebox.showwarning(
                "File not found",
                f"The active CSV file does not exist:\n{path}",
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self._log(f"Opening CSV file: {path}")
        except Exception as e:
            messagebox.showerror(
                "Error opening file",
                f"Could not open the file:\n{e}",
            )

    def _refresh_main_info(self):
        """Updates Add Offers screen info (selected file, items)."""
        if self.add_offers_frame:
            self.add_offers_frame.update_info()

    # ------------------------------------------------------------------
    # Bot execution (thread + login popup + final popup)
    # ------------------------------------------------------------------
    def _rodar_bot_thread(self):
        t = threading.Thread(target=self._rodar_bot, daemon=True)
        t.start()

    def _rodar_bot(self):
        self._log("Starting automation (bot)...")
        try:
            executar_bot(wait_for_login_callback=self._wait_for_login_popup_blocking)
            self._log("Automation finished successfully.")
            self._refresh_main_info()
            # popup after insertion is done
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "Insertion finished",
                    "The insertion has been completed successfully!",
                ),
            )
        except Exception as e:
            self._log(f"[ERROR] Failed to run the bot: {e}")

    def _wait_for_login_popup_blocking(self):
        """Called from the bot thread. Shows a popup and blocks until user confirms login."""
        event = threading.Event()

        def show_popup():
            self._create_login_popup(event)

        self.after(0, show_popup)
        event.wait()

    def _create_login_popup(self, event: threading.Event):
        popup = ctk.CTkToplevel(self)
        popup.title("Confirm login")
        popup.geometry("420x220")
        popup.grab_set()
        popup.configure(fg_color=PALETTE["content_bg"])

        lbl = ctk.CTkLabel(
            popup,
            text=(
                "1) Log in manually in the browser window.\n"
                "2) Solve the CAPTCHA (if any).\n"
                "3) Leave the page on the screen with the 'Sell' button.\n\n"
                "When everything is ready, click the button below."
            ),
            justify="left",
            text_color=PALETTE["text_primary"],
        )
        lbl.pack(padx=20, pady=20)

        def on_confirm():
            event.set()
            popup.destroy()
            self._log("[LOGIN] User confirmed they are logged in and ready.")

        btn = ctk.CTkButton(
            popup,
            text="✅ I'm logged in, continue",
            command=on_confirm,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )
        btn.pack(pady=10)

        def on_close():
            event.set()
            popup.destroy()
            self._log(
                "[LOGIN] Login popup closed. Continuing flow anyway."
            )

        popup.protocol("WM_DELETE_WINDOW", on_close)

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------
    def _log(self, message: str):
        """Centralizes logs: sends them to Add Offers screen (if any) and to the terminal."""
        if self.add_offers_frame:
            self.add_offers_frame.append_log(message)
        print(message)


# ======================================================================
# Screen 1: Add Offers
# ======================================================================
class AddOffersFrame(ctk.CTkFrame):
    def __init__(self, master, app: BotApp):
        super().__init__(master, fg_color=PALETTE["content_bg"])
        self.app = app

        self.lbl_selected_file: ctk.CTkLabel | None = None
        self.lbl_items: ctk.CTkLabel | None = None
        self.txt_logs: ctk.CTkTextbox | None = None

        self._build_ui()

    def _build_ui(self):
        # Title
        lbl_title = ctk.CTkLabel(
            self,
            text="Add Offers",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_title.pack(anchor="w", padx=20, pady=(20, 10))

        # CSV section
        frame_csv = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        frame_csv.pack(fill="x", padx=20, pady=(0, 20))

        lbl_csv_title = ctk.CTkLabel(
            frame_csv,
            text="Current .CSV",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_csv_title.pack(anchor="w", padx=10, pady=(10, 5))

        self.lbl_selected_file = ctk.CTkLabel(
            frame_csv,
            text="Selected file: (none)",
            text_color=PALETTE["text_secondary"],
        )
        self.lbl_selected_file.pack(anchor="w", padx=10, pady=(0, 3))

        self.lbl_items = ctk.CTkLabel(
            frame_csv,
            text="Items: 0",
            text_color=PALETTE["text_secondary"],
        )
        self.lbl_items.pack(anchor="w", padx=10, pady=(0, 10))

        # Open / Clear buttons
        btns = ctk.CTkFrame(frame_csv, fg_color=PALETTE["card_bg"])
        btns.pack(anchor="e", padx=10, pady=(0, 10))

        btn_clear = ctk.CTkButton(
            btns,
            text="Clear file",
            width=110,
            command=self.app.clear_csv_file,
            fg_color=PALETTE["danger"],
            hover_color=PALETTE["danger_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_clear.pack(side="left", padx=(0, 10))

        btn_open = ctk.CTkButton(
            btns,
            text="Open file",
            width=110,
            command=self.app.open_csv_file,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_open.pack(side="left", padx=(0, 10))

        # Logs
        lbl_logs = ctk.CTkLabel(
            self,
            text="Logs:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PALETTE["text_secondary"],
        )
        lbl_logs.pack(anchor="w", padx=20)

        self.txt_logs = ctk.CTkTextbox(
            self,
            wrap="word",
            height=130,
            fg_color=PALETTE["log_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.txt_logs.pack(fill="x", padx=20, pady=(5, 20))
        self.txt_logs.configure(state="disabled")

        # Add Brainrots button
        btn_add = ctk.CTkButton(
            self,
            text="Add Brainrots",
            command=self._on_add_brainrots_clicked,
            width=180,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )
        btn_add.pack(anchor="e", padx=20, pady=(0, 20))

        self.update_info()

    def update_info(self):
        """Updates selected file label and item count."""
        if not self.lbl_selected_file or not self.lbl_items:
            return

        path = self.app.settings.csv_ativo_path
        if path and Path(path).exists():
            self.lbl_selected_file.configure(text=f"Selected file: {path}")
            try:
                itens = carregar_insercao(path)
                self.lbl_items.configure(text=f"Items: {len(itens)}")
            except Exception:
                self.lbl_items.configure(text="Items: N/A")
        else:
            self.lbl_selected_file.configure(text="Selected file: (none)")
            self.lbl_items.configure(text="Items: 0")

    def append_log(self, message: str):
        if not self.txt_logs:
            return
        # habilita temporariamente para escrever
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert(tk.END, f"{message}\n")
        self.txt_logs.see(tk.END)
        # volta para read-only
        self.txt_logs.configure(state="disabled")

    def _on_add_brainrots_clicked(self):
        self.app._log("Opening insertion form (New Insert)...")
        self.app.open_insertion_window()


# ======================================================================
# Screen 2: Configs
# ======================================================================
class ConfigFrame(ctk.CTkFrame):
    def __init__(self, master, app: BotApp):
        super().__init__(master, fg_color=PALETTE["content_bg"])
        self.app = app

        self.entry_profile: ctk.CTkEntry | None = None
        self.entry_csv: ctk.CTkEntry | None = None
        self.txt_descricao_padrao: ctk.CTkTextbox | None = None

        self._build_ui()

    def _build_ui(self):
        lbl_title = ctk.CTkLabel(
            self,
            text="Configs",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_title.pack(anchor="w", padx=20, pady=(20, 15))

        padding = {"padx": 20, "pady": 5}

        # Chrome profile
        row_profile = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_profile.pack(fill="x", **padding)        

        btn_escolher_profile = ctk.CTkButton(
            row_profile,
            text="Browse",
            width=80,
            command=self._choose_profile_dir,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_escolher_profile.pack(side="right", padx=5)
        
        self.entry_profile = ctk.CTkEntry(
            row_profile,
            width=380,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_profile.pack(side="right", padx=5)
        
        ctk.CTkLabel(
            row_profile,
            text="Chrome Profile Path:",
            text_color=PALETTE["text_secondary"],
        ).pack(side="right", padx=5)
        
        # CSV path
        row_csv = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_csv.pack(fill="x", **padding)

        btn_escolher_csv = ctk.CTkButton(
            row_csv,
            text="Browse",
            width=80,
            command=self._choose_csv_file,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_escolher_csv.pack(side="right", padx=5)
        
        self.entry_csv = ctk.CTkEntry(
            row_csv,
            width=380,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_csv.pack(side="right", padx=5)
        
        ctk.CTkLabel(
            row_csv,
            text="CSV File Path:",
            text_color=PALETTE["text_secondary"],
        ).pack(side="right", padx=5)

        # Default description (label + textbox on same row)
        row_desc = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_desc.pack(fill="x", expand=False, **padding)

        self.txt_descricao_padrao = ctk.CTkTextbox(
            row_desc,
            width=390,
            height=220,
            border_width=2,
            border_color=PALETTE["entry_border"],
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.txt_descricao_padrao.pack(side="right", padx=(5, 10), pady=10, fill="x", expand=True)
        
        ctk.CTkLabel(
            row_desc,
            text="Default Description:",
            text_color=PALETTE["text_secondary"],
            anchor="n",
        ).pack(anchor="n", side="right", padx=(10, 5), pady=13)

        # Reset / Save buttons
        frame_btns = ctk.CTkFrame(self, fg_color=PALETTE["content_bg"])
        frame_btns.pack(fill="x", pady=(10, 20))

        btn_reset = ctk.CTkButton(
            frame_btns,
            text="Reset to Default",
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
            command=self._on_reset_default,
        )
        btn_reset.pack(side="left", padx=20)

        btn_save = ctk.CTkButton(
            frame_btns,
            text="Save",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
            command=self._on_save,
        )
        btn_save.pack(side="right", padx=20)

    def load_from_settings(self):
        """Load current Settings values into fields."""
        if not self.entry_profile or not self.txt_descricao_padrao or not self.entry_csv:
            return

        self.entry_profile.delete(0, "end")
        if self.app.settings.chrome_profile_path:
            self.entry_profile.insert(0, str(self.app.settings.chrome_profile_path))

        self.entry_csv.delete(0, "end")
        self.entry_csv.insert(0, str(self.app.settings.csv_ativo_path))

        self.txt_descricao_padrao.delete("1.0", "end")
        self.txt_descricao_padrao.insert("1.0", self.app.settings.descricao_padrao)

    def _choose_profile_dir(self):
        d = filedialog.askdirectory(
            title="Select Chrome profile folder",
            initialdir=str(self.app.settings.chrome_profile_path)
            if self.app.settings.chrome_profile_path
            else ".",
        )
        if d and self.entry_profile:
            self.entry_profile.delete(0, "end")
            self.entry_profile.insert(0, d)
            
    def _choose_csv_file(self):
        from pathlib import Path

        initial = (
            str(self.app.settings.csv_ativo_path.parent)
            if self.app.settings.csv_ativo_path
            else "."
        )
        path = filedialog.asksaveasfilename(
            title="Select CSV file",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=initial,
            initialfile=(
                self.app.settings.csv_ativo_path.name
                if self.app.settings.csv_ativo_path
                else "items.csv"
            ),
        )
        if path and self.entry_csv:
            self.entry_csv.delete(0, "end")
            self.entry_csv.insert(0, path)

    def _on_reset_default(self):
        defaults = Settings.defaults()

        self.app.settings.chrome_profile_path = defaults.chrome_profile_path
        self.app.settings.descricao_padrao = defaults.descricao_padrao
        self.app.settings.csv_ativo_path = defaults.csv_ativo_path
        self.app.settings.pasta_logs = defaults.pasta_logs
        self.app.settings.pasta_imagens = defaults.pasta_imagens

        self.app.settings.save()
        self.load_from_settings()
        self.app._log("Settings reset to default.")
        self.app._refresh_main_info()

    def _on_save(self):
        if not self.entry_profile or not self.txt_descricao_padrao or not self.entry_csv:
            return

        profile_str = self.entry_profile.get().strip()
        descricao = self.txt_descricao_padrao.get("1.0", "end").strip()
        csv_path_str = self.entry_csv.get().strip()

        from pathlib import Path

        # valida CSV primeiro
        if not csv_path_str:
            messagebox.showerror(
                "Invalid CSV path",
                "Please select a valid CSV file path.",
                parent=self,
            )
            return

        try:
            # Chrome profile
            if profile_str:
                self.app.settings.chrome_profile_path = Path(profile_str)
            else:
                self.app.settings.chrome_profile_path = None

            # CSV path
            csv_path = Path(csv_path_str)
            if csv_path.suffix.lower() != ".csv":
                if not messagebox.askyesno(
                    "CSV extension",
                    "The selected path does not end with .csv.\nDo you want to use it anyway?",
                    parent=self,
                ):
                    return

            csv_path.parent.mkdir(parents=True, exist_ok=True)
            self.app.settings.csv_ativo_path = csv_path

            # default description
            if descricao.strip():
                self.app.settings.descricao_padrao = descricao.strip()

            # salva
            self.app._log(
                f"Saving settings... chrome_profile_path={self.app.settings.chrome_profile_path}"
            )
            self.app.settings.save()
            self.app._log("Settings saved.")
            self.app._refresh_main_info()

        except Exception as e:
            messagebox.showerror(
                "Error saving settings",
                f"An error occurred while saving settings:\n{e}",
                parent=self,
            )
            self.app._log(f"[ERROR] Failed to save settings: {e}")


# ======================================================================
# License Window
# ======================================================================

class LicenseWindow(ctk.CTkToplevel):
    """
    Window to type and validate the product key with the license API.
    """
    def __init__(
        self,
        master: ctk.CTk,
        config: LicenseConfig,
        on_success,
    ):
        super().__init__(master)
        self.config = config
        self.on_success = on_success

        self.title("Product Key")
        self.geometry("420x230")
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["content_bg"])
        self.grab_set()  # modal

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(
            self,
            text="Enter your license key",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="n")

        self.entry_key = ctk.CTkEntry(
            self,
            width=360,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
            placeholder_text="XXXX-XXXX-XXXX-XXXX",
        )
        self.entry_key.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # if there was already a saved key, show it
        if self.config.license_key:
            self.entry_key.insert(0, self.config.license_key)

        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            text_color=PALETTE["danger"],
        )
        self.lbl_status.grid(row=2, column=0, padx=20, pady=(4, 0), sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=20)

        btn_ok = ctk.CTkButton(
            btn_frame,
            text="Activate",
            command=self._on_activate,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
            width=110,
        )
        btn_ok.pack(side="left", padx=5)

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Exit",
            command=self._on_cancel,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
            width=110,
        )
        btn_cancel.pack(side="left", padx=5)

    # ---------------- callbacks ----------------
    def _set_status(self, text: str):
        self.lbl_status.configure(text=text)

    def _on_cancel(self):
        self.grab_release()
        self.master.destroy()

    def _on_activate(self):
        key = self.entry_key.get().strip()
        if not key:
            self._set_status("Please enter a key.")
            return

        self._set_status("Checking key with server...")
        self.update_idletasks()

        result: LicenseCheckResult = verify_license(key, self.config.client_id)

        if not result.valid:
            reason = result.reason or "unknown_error"

            if reason.startswith("network_error"):
                msg = "Could not contact license server.\nCheck your internet."
            elif reason == "not found":
                msg = "Key not found."
            elif reason == "expired":
                msg = "This key has expired."
            elif reason == "bound_to_another_client":
                msg = "This key is already in use on another device."
            else:
                msg = f"Invalid key. Reason: {reason}"

            self._set_status(msg)
            return

        # success → save key in config
        self.config.license_key = key
        save_config(self.config)

        if self.on_success:
            self.on_success(key)

        self.grab_release()
        self.destroy()


def ensure_valid_license(master: ctk.CTk) -> bool:
    """
    Ensures there is a valid key for this client_id.
    Uses 'master' (BotApp) as parent window for popups/modals.
    """
    cfg: LicenseConfig = load_config()

    # 1) if we already have a saved key, check it first
    if cfg.license_key:
        result = verify_license(cfg.license_key, cfg.client_id)
        if result.valid:
            return True

        if result.reason and str(result.reason).startswith("network_error"):
            messagebox.showerror(
                "License error",
                "Could not contact the license server.\n"
                "Please check your internet connection and try again.",
                parent=master,
            )
            return False
        # other reasons (expired, bound_to_another_client, etc) → open key prompt

    # 2) open modal window to type/activate new key
    done = {"ok": False}

    def _on_success(_key: str):
        done["ok"] = True

    win = LicenseWindow(master, cfg, on_success=_on_success)
    master.wait_window(win)  # local loop until the window is closed

    return done["ok"]

# ======================================================================
# Initial Config Window
# ======================================================================
class InitialSetupWindow(ctk.CTkToplevel):
    """
    First-run setup window to choose CSV path and Chrome profile path.
    """
    def __init__(self, master: BotApp, settings: Settings, on_done):
        super().__init__(master)
        self.master = master
        self.settings = settings
        self.on_done = on_done

        self.title("Initial Setup")
        self.geometry("520x260")
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["content_bg"])
        self.grab_set()

        self.entry_csv: ctk.CTkEntry | None = None
        self.entry_profile: ctk.CTkEntry | None = None

        self._build_ui()

    def _build_ui(self):
        padding = {"padx": 20, "pady": 8}

        title = ctk.CTkLabel(
            self,
            text="Initial Setup",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        title.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(
            self,
            text="Choose where to store your CSV file and Chrome profile.",
            text_color=PALETTE["text_secondary"],
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 10))

        # CSV path row
        row_csv = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_csv.pack(fill="x", **padding)

        btn_csv = ctk.CTkButton(
            row_csv,
            text="Browse",
            width=70,
            command=self._choose_csv_file,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_csv.pack(side="right", padx=5)
        
        self.entry_csv = ctk.CTkEntry(
            row_csv,
            width=260,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_csv.pack(side="right", padx=5)
        
        ctk.CTkLabel(
            row_csv,
            text="CSV File Path:",
            text_color=PALETTE["text_secondary"],
        ).pack(side="right", padx=5)

        # default/value from settings
        default_csv = str(self.settings.csv_ativo_path)
        self.entry_csv.insert(0, default_csv)
        
        #------------------------------------------------------------
        # Chrome profile row
        row_profile = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_profile.pack(fill="x", **padding)

        btn_profile = ctk.CTkButton(
            row_profile,
            text="Browse",
            width=70,
            command=self._choose_profile_dir,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_profile.pack(side="right", padx=5)
        
        self.entry_profile = ctk.CTkEntry(
            row_profile,
            width=260,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_profile.pack(side="right", padx=5)
        
        ctk.CTkLabel(
            row_profile,
            text="Chrome Profile Path:",
            text_color=PALETTE["text_secondary"],
        ).pack(side="right", padx=5)

        default_profile = (
            str(self.settings.chrome_profile_path)
            if self.settings.chrome_profile_path
            else ""
        )
        self.entry_profile.insert(0, default_profile)

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color=PALETTE["content_bg"])
        btn_row.pack(fill="x", padx=20, pady=(15, 15))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Exit",
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
            command=self._on_cancel,
            width=110,
        )
        btn_cancel.pack(side="left")

        btn_ok = ctk.CTkButton(
            btn_row,
            text="Continue",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
            command=self._on_confirm,
            width=120,
        )
        btn_ok.pack(side="right")

    def _choose_csv_file(self):
        initial = (
            str(self.settings.csv_ativo_path.parent)
            if self.settings.csv_ativo_path
            else "."
        )
        path = filedialog.asksaveasfilename(
            title="Select CSV file",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=initial,
            initialfile=self.settings.csv_ativo_path.name
            if self.settings.csv_ativo_path
            else "items.csv",
        )
        if path and self.entry_csv:
            self.entry_csv.delete(0, "end")
            self.entry_csv.insert(0, path)

    def _choose_profile_dir(self):
        initial = (
            str(self.settings.chrome_profile_path)
            if self.settings.chrome_profile_path
            else "."
        )
        d = filedialog.askdirectory(
            title="Select Chrome profile folder",
            initialdir=initial,
        )
        if d and self.entry_profile:
            self.entry_profile.delete(0, "end")
            self.entry_profile.insert(0, d)

    def _on_cancel(self):
        # user aborted setup → close app
        self.grab_release()
        self.master.destroy()

    def _on_confirm(self):
        from pathlib import Path

        csv_str = self.entry_csv.get().strip() if self.entry_csv else ""
        profile_str = self.entry_profile.get().strip() if self.entry_profile else ""

        if not csv_str:
            messagebox.showerror(
                "Invalid CSV path",
                "Please choose a valid CSV file path.",
                parent=self,
            )
            return

        csv_path = Path(csv_str)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        self.settings.csv_ativo_path = csv_path

        if profile_str:
            self.settings.chrome_profile_path = Path(profile_str)
        else:
            self.settings.chrome_profile_path = None

        # mark setup as done and save
        self.settings.initial_setup_done = True
        self.settings.save()

        if self.on_done:
            self.on_done()

        self.grab_release()
        self.destroy()


# ======================================================================
# New Insert Window (Add Brainrots)
# ======================================================================
class NovaInsercaoWindow(ctk.CTkToplevel):
    """
    Window to add brainrots (New Insert).
    """

    def __init__(
        self,
        master: BotApp,
        settings: Settings,
        start_bot_callback,
        refresh_main_callback,
    ):
        super().__init__(master)
        self.master: BotApp = master
        self.settings = settings
        self.start_bot_callback = start_bot_callback
        self.refresh_main_callback = refresh_main_callback

        self.title("New Insert")
        self.geometry("605x580")
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["content_bg"])
        self.grab_set()

        self.use_default_desc_var = ctk.BooleanVar(value=True)

        self._create_widgets()

    def _create_widgets(self):
        lbl_title = ctk.CTkLabel(
            self,
            text="New Insert",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_title.pack(pady=(10, 15))

        # mode options
        self.frame_opcoes = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        self.frame_opcoes.pack(fill="x", padx=20, pady=10)

        lbl_modo = ctk.CTkLabel(
            self.frame_opcoes,
            text="How do you want to add the brainrots?",
            text_color=PALETTE["text_secondary"],
        )
        lbl_modo.pack(pady=(5, 0))

        btns_opcoes = ctk.CTkFrame(self.frame_opcoes, fg_color=PALETTE["card_bg"])
        btns_opcoes.pack(pady=5)

        self.btn_por_imagem = ctk.CTkButton(
            btns_opcoes,
            text="Add by Image (Soon)",
            state="disabled",
            command=self._on_adicionar_por_imagem,
            width=220,
            height=40,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        self.btn_por_imagem.pack(side="left", padx=10, pady=5)

        self.btn_manual = ctk.CTkButton(
            btns_opcoes,
            text="Add Manually",
            command=self._mostrar_formulario_manual,
            width=220,
            height=40,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )
        self.btn_manual.pack(side="left", padx=10, pady=5)

        self.frame_form = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        self._build_formulario_manual()

    def _build_formulario_manual(self):
        padding = {"padx": 10, "pady": 5}

        # Name
        row_nome = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        self.entry_nome = ctk.CTkEntry(
            row_nome,
            width=450,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_nome.pack(side="right", padx=(5, 10), pady=(10, 0))
        row_nome.pack(fill="x", **padding)
        ctk.CTkLabel(
            row_nome, text="Name:", text_color=PALETTE["text_secondary"]
        ).pack(side="right", padx=5)

        # Title
        row_titulo = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        self.entry_titulo = ctk.CTkEntry(
            row_titulo,
            width=450,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_titulo.pack(side="right", padx=(5, 10))
        row_titulo.pack(fill="x", **padding)
        ctk.CTkLabel(
            row_titulo, text="Title:", text_color=PALETTE["text_secondary"]
        ).pack(side="right", padx=5)

        # Image Path + Browse
        row_img = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        row_img.pack(fill="x", **padding)

        btn_escolher_img = ctk.CTkButton(
            row_img,
            text="Browse...",
            width=80,
            command=self._on_escolher_imagem,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_escolher_img.pack(side="right", padx=(5, 10))

        self.entry_img = ctk.CTkEntry(
            row_img,
            width=360,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_img.pack(side="right", padx=5)

        ctk.CTkLabel(
            row_img, text="Image Path:", text_color=PALETTE["text_secondary"]
        ).pack(side="right", padx=5)

        # Checkbox Use Default Description
        row_chk = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        row_chk.pack(fill="x", **padding)
        self.chk_desc_padrao = ctk.CTkCheckBox(
            row_chk,
            text="Use Default Description?",
            variable=self.use_default_desc_var,
            command=self._on_toggle_desc_padrao,
            text_color=PALETTE["text_secondary"],
            fg_color=PALETTE["entry_bg"],
            hover_color=PALETTE["muted_hover"],
            border_color=PALETTE["entry_border"],
            checkmark_color=PALETTE["accent"],
        )
        self.chk_desc_padrao.pack(anchor="w", padx=5)

        # Description
        row_desc = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        row_desc.pack(fill="x", expand=False, **padding)

        self.txt_descricao = ctk.CTkTextbox(
            row_desc,
            width=450,
            height=100,
            border_width=2,
            fg_color=PALETTE["entry_bg"],
            border_color=PALETTE["entry_border"],
            text_color=PALETTE["text_primary"],
        )
        self.txt_descricao.pack(side="right", padx=(5, 10), pady=5)

        ctk.CTkLabel(
            row_desc, text="Description: ", text_color=PALETTE["text_secondary"]
        ).pack(side="right", anchor="n", padx=5)
        self.txt_descricao.insert("1.0", self.settings.descricao_padrao)

        self._aplicar_estado_descricao()

        # Price + Quantity row
        row_qtd = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        # Price
        row_qtd.pack(fill="x", **padding)
        self.entry_preco = ctk.CTkEntry(
            row_qtd,
            width=196,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_preco.pack(side="right", padx=(5, 10))
        self.entry_preco.insert(0, "0.00")
        ctk.CTkLabel(
            row_qtd, text="Price:", text_color=PALETTE["text_secondary"]
        ).pack(side="right", padx=5)

        # Quantity
        row_qtd.pack(fill="x", **padding)
        self.entry_quantidade = ctk.CTkEntry(
            row_qtd,
            width=196,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_quantidade.pack(side="right", padx=(5, 10))
        self.entry_quantidade.insert(0, "1")
        ctk.CTkLabel(
            row_qtd, text="Quantity:", text_color=PALETTE["text_secondary"]
        ).pack(side="right", padx=5)

        vcmd_int = self.register(self._validate_int)
        self.entry_quantidade.configure(
            validate="key", validatecommand=(vcmd_int, "%P")
        )

        vcmd_dec = self.register(self._validate_decimal)
        self.entry_preco.configure(
            validate="key", validatecommand=(vcmd_dec, "%P")
        )

        # Buttons
        frame_botoes = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"])
        frame_botoes.pack(side="bottom", fill="x", pady=(15, 10))

        btn_cancelar = ctk.CTkButton(
            frame_botoes,
            text="Cancel",
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
            command=self._on_cancelar,
        )
        btn_cancelar.pack(side="left", padx=10)

        btn_iniciar = ctk.CTkButton(
            frame_botoes,
            text="Start Posting",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
            command=self._on_iniciar_insercao,
        )
        btn_iniciar.pack(side="right", padx=(5, 10))

        btn_adicionar_mais = ctk.CTkButton(
            frame_botoes,
            text="Add More",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
            command=self._on_adicionar_mais,
        )
        btn_adicionar_mais.pack(side="right", padx=(10, 5))

    # ---------------------- validation ----------------------
    def _validate_int(self, new_value: str) -> bool:
        if new_value == "":
            return True
        return new_value.isdigit()

    def _validate_decimal(self, new_value: str) -> bool:
        if new_value == "":
            return True
        try:
            Decimal(new_value.replace(",", "."))
            return True
        except (InvalidOperation, ValueError):
            return False

    # ---------------------- callbacks ----------------------
    def _on_adicionar_por_imagem(self):
        # placeholder
        pass

    def _mostrar_formulario_manual(self):
        if not self.frame_form.winfo_ismapped():
            self.frame_form.pack(fill="both", expand=True, padx=20, pady=10)

    def _on_escolher_imagem(self):
        initial_dir = (
            str(self.settings.pasta_imagens)
            if self.settings.pasta_imagens
            else "."
        )
        file_path = filedialog.askopenfilename(
            title="Select brainrot image",
            initialdir=initial_dir,
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.entry_img.delete(0, "end")
            self.entry_img.insert(0, file_path)

    def _on_toggle_desc_padrao(self):
        self._aplicar_estado_descricao()

    def _aplicar_estado_descricao(self):
        if self.use_default_desc_var.get():
            self.txt_descricao.configure(state="normal")
            self.txt_descricao.delete("1.0", "end")
            self.txt_descricao.insert("1.0", self.settings.descricao_padrao)
            self.txt_descricao.configure(state="disabled")
        else:
            self.txt_descricao.configure(state="normal")

    def _on_cancelar(self):
        self.master._log("New insertion cancelled by user.")
        self.destroy()

    def _coletar_item_do_form(self) -> ItemInsercao | None:
        nome = self.entry_nome.get().strip()
        titulo = self.entry_titulo.get().strip()
        imgUrl = self.entry_img.get().strip()
        qtd_raw = self.entry_quantidade.get().strip()
        preco_raw = self.entry_preco.get().strip()

        if self.use_default_desc_var.get():
            descricao = self.settings.descricao_padrao
        else:
            descricao = self.txt_descricao.get("1.0", "end").strip()

        if not nome:
            messagebox.showerror("Validation error", "The 'Name' field is required.")
            return None

        if not qtd_raw:
            messagebox.showerror(
                "Validation error", "The 'Quantity' field is required."
            )
            return None

        if not preco_raw:
            messagebox.showerror(
                "Validation error", "The 'Price' field is required."
            )
            return None

        try:
            quantidade = int(qtd_raw)
            if quantidade <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Validation error",
                "Quantity must be a positive integer.",
            )
            return None

        try:
            preco = Decimal(preco_raw.replace(",", "."))
        except (InvalidOperation, AttributeError):
            messagebox.showerror(
                "Validation error",
                "Invalid price. Use only numbers, dot or comma.",
            )
            return None

        item = ItemInsercao(
            nome=nome,
            titulo=titulo,
            imgUrl=imgUrl,
            descricao=descricao,
            quantidade=quantidade,
            preco=preco,
        )
        return item

    def _limpar_form(self):
        self.entry_nome.delete(0, "end")
        self.entry_titulo.delete(0, "end")
        self.entry_img.delete(0, "end")
        self.entry_quantidade.delete(0, "end")
        self.entry_quantidade.insert(0, "1")
        self.entry_preco.delete(0, "end")
        self.entry_preco.insert(0, "0.00")
        self._aplicar_estado_descricao()

    def _on_adicionar_mais(self):
        item = self._coletar_item_do_form()
        if item is None:
            return

        caminho_csv = self.settings.csv_ativo_path
        adicionar_ou_incrementar_item(caminho_csv, item)

        self.master._log(
            f"[Insertion] Item '{item.nome}' added/incremented in active CSV."
        )

        if self.refresh_main_callback:
            self.refresh_main_callback()

        self._limpar_form()

    def _on_iniciar_insercao(self):
        campos_preenchidos = any(
            [
                self.entry_nome.get().strip(),
                self.entry_titulo.get().strip(),
                self.entry_img.get().strip(),
                (
                    self.txt_descricao.get("1.0", "end").strip()
                    if not self.use_default_desc_var.get()
                    else True
                ),
            ]
        )

        if campos_preenchidos and self.entry_nome.get().strip():
            item = self._coletar_item_do_form()
            if item is not None:
                caminho_csv = self.settings.csv_ativo_path
                adicionar_ou_incrementar_item(caminho_csv, item)
                self.master._log(
                    f"[Insertion] Item '{item.nome}' added/incremented in active CSV (before starting bot)."
                )
                if self.refresh_main_callback:
                    self.refresh_main_callback()

        self.master._log("Starting insertion flow (bot)...")
        self.destroy()

        if self.start_bot_callback:
            self.start_bot_callback()
            
            
def ensure_initial_paths(app: BotApp) -> bool:
        """
        Ensures the initial CSV and Chrome profile paths are configured.
        Shows a first-run setup window if needed.
        """
        settings = app.settings

        # Se já rodou o setup uma vez, não faz nada.
        if getattr(settings, "initial_setup_done", False):
            return True

        done = {"ok": False}

        def _on_done():
            done["ok"] = True
            # atualizar tela principal (paths podem ter mudado)
            app._refresh_main_info()

        win = InitialSetupWindow(app, settings, on_done=_on_done)
        app.wait_window(win)

        return done["ok"]


# ----------------------------------------------------------------------
# Direct execution (with license verification)
# ----------------------------------------------------------------------
def main():
    apply_widget_colors()

    app = BotApp()

    # 1) Verifica licença
    if not ensure_valid_license(app):
        if app.winfo_exists():
            app.destroy()
        return

    # 2) Setup inicial de paths (primeira execução)
    if not ensure_initial_paths(app):
        if app.winfo_exists():
            app.destroy()
        return

    # 3) Agora mantém a janela principal visível normalmente
    app.mainloop()


if __name__ == "__main__":
    main()