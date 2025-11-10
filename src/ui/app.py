from __future__ import annotations

import os
import platform
import subprocess
import threading
import tkinter as tk
from decimal import Decimal, InvalidOperation
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox, filedialog

from src.core.settings import Settings
from src.core.insercao_service import (
    nova_insercao,
    adicionar_ou_incrementar_item,
    carregar_insercao,
)
from src.core.models import ItemInsercao
from src.core.bot import executar_bot


# =========================
# PALETA DE CORES / TEMA
# =========================
PALETTE = {
    # fundo geral
    "bg": "#2F2F2F",          # fundo principal (quase preto/azulado)
    "sidebar_bg": "#373737",  # lateral
    "content_bg": "#373737",  # conteúdo central

    # textos
    "text_primary": "#F9FAFB",    # branco suave
    "text_secondary": "#9CA3AF",  # cinza

    # botões
    "accent": "#E5A000",          # laranja principal
    "accent_hover": "#AF7B00",    # larana hover
    "danger": "#EF4444",          # vermelho
    "danger_hover": "#B91C1C",    # vermelho hover
    "muted": "#4B5563",           # cinza botão
    "muted_hover": "#374151",

    # componentes
    "card_bg": "#414141",         # fundo cards
    "entry_bg": "#414141",
    "entry_border": "#2F2F2F",
    "log_bg": "#414141",
}


def apply_widget_colors():
    """Configuração global de tema do CTk."""
    ctk.set_appearance_mode("dark")
    # não uso theme pronto pra poder controlar cores manualmente


class BotApp(ctk.CTk):
    """Janela principal do app, com menu lateral e telas Add Offers / Configs."""

    def __init__(self):
        super().__init__()
        self.title("Eldorado Placer v0.2.0")
        self.resizable(False, False)
        self.geometry("850x460")

        apply_widget_colors()
        self.configure(fg_color=PALETTE["bg"])  # fundo da janela

        self.settings = Settings.load()

        # frames de conteúdo (telas)
        self.add_offers_frame: AddOffersFrame | None = None
        self.config_frame: ConfigFrame | None = None

        self._build_layout()
        self.show_add_offers()  # tela inicial

        self._log("Aplicação iniciada.")

    # ------------------------------------------------------------------
    # Layout principal: menu lateral + área de conteúdo
    # ------------------------------------------------------------------
    def _build_layout(self):
        # Container geral
        container = ctk.CTkFrame(self, fg_color=PALETTE["bg"])
        container.pack(fill="both", expand=True)

        # Menu lateral
        sidebar = ctk.CTkFrame(
            container,
            width=200,
            fg_color=PALETTE["sidebar_bg"],
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        
        # Botões do menu lateral
        btn_add_offers = ctk.CTkButton(
            sidebar,
            text="Add Offers",
            command=self.show_add_offers,
            width=150,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color="black",
        )
        btn_add_offers.pack(pady=(20, 10))

        btn_configs = ctk.CTkButton(
            sidebar,
            text="Configs",
            command=self.show_configs,
            width=150,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_configs.pack(pady=0)
        
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

        # Área de conteúdo (direita)
        content = ctk.CTkFrame(
            container,
            fg_color=PALETTE["content_bg"],
            corner_radius=0,
        )
        content.pack(side="left", fill="both", expand=True)

        self.content = content

        # Instancia as telas, mas mostra só uma de cada vez
        self.add_offers_frame = AddOffersFrame(content, app=self)
        self.config_frame = ConfigFrame(content, app=self)

    # ------------------------------------------------------------------
    # Navegação entre telas
    # ------------------------------------------------------------------
    def show_add_offers(self):
        if self.config_frame:
            self.config_frame.pack_forget()
        if self.add_offers_frame:
            self.add_offers_frame.pack(fill="both", expand=True)
            self.add_offers_frame.update_info()

    def show_configs(self):
        if self.add_offers_frame:
            self.add_offers_frame.pack_forget()
        if self.config_frame:
            self.config_frame.pack(fill="both", expand=True)
            self.config_frame.load_from_settings()

    # ------------------------------------------------------------------
    # Ações globais que as telas chamam
    # ------------------------------------------------------------------
    def open_insertion_window(self):
        """Abre a janela (Tela 3) para adicionar brainrots."""
        NovaInsercaoWindow(
            master=self,
            settings=self.settings,
            start_bot_callback=self._rodar_bot_thread,
            refresh_main_callback=self._refresh_main_info,
        )

    def clear_csv_file(self):
        """Limpa o arquivo CSV ativo (nova inserção vazia)."""
        csv_path = nova_insercao(self.settings)
        self._log(f"Arquivo CSV limpo: {csv_path}")
        self._refresh_main_info()

    def open_csv_file(self):
        """Abre o CSV ativo num editor externo."""
        path = self.settings.csv_ativo_path
        if not path or not Path(path).exists():
            messagebox.showwarning(
                "Arquivo não encontrado",
                f"O arquivo CSV ativo não existe:\n{path}",
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self._log(f"Abrindo arquivo CSV: {path}")
        except Exception as e:
            messagebox.showerror(
                "Erro ao abrir arquivo",
                f"Não foi possível abrir o arquivo:\n{e}",
            )

    def _refresh_main_info(self):
        """Atualiza infos da Tela 1 (selected file, items)."""
        if self.add_offers_frame:
            self.add_offers_frame.update_info()

    # ------------------------------------------------------------------
    # Execução do bot (thread + popup de login + popup final)
    # ------------------------------------------------------------------
    def _rodar_bot_thread(self):
        t = threading.Thread(target=self._rodar_bot, daemon=True)
        t.start()

    def _rodar_bot(self):
        self._log("Iniciando automação (bot)...")
        try:
            executar_bot(wait_for_login_callback=self._wait_for_login_popup_blocking)
            self._log("Automação concluída com sucesso.")
            self._refresh_main_info()
            # Popup ao finalizar inserção
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "Inserção concluída",
                    "A inserção foi finalizada com sucesso!",
                ),
            )
        except Exception as e:
            self._log(f"[ERRO] Falha ao executar o bot: {e}")

    def _wait_for_login_popup_blocking(self):
        """Chamado pela thread do bot. Mostra popup e bloqueia até confirmar login."""
        event = threading.Event()

        def show_popup():
            self._create_login_popup(event)

        self.after(0, show_popup)
        event.wait()

    def _create_login_popup(self, event: threading.Event):
        popup = ctk.CTkToplevel(self)
        popup.title("Confirmar login")
        popup.geometry("420x220")
        popup.grab_set()
        popup.configure(fg_color=PALETTE["content_bg"])

        lbl = ctk.CTkLabel(
            popup,
            text=(
                "1) Faça login manualmente na janela do navegador.\n"
                "2) Resolva o CAPTCHA (se houver).\n"
                "3) Deixe na tela com o botão 'Sell'.\n\n"
                "Quando estiver tudo pronto, clique no botão abaixo."
            ),
            justify="left",
            text_color=PALETTE["text_primary"],
        )
        lbl.pack(padx=20, pady=20)

        def on_confirm():
            event.set()
            popup.destroy()
            self._log("[LOGIN] Usuário confirmou que está logado e pronto.")

        btn = ctk.CTkButton(
            popup,
            text="✅ Já estou logado, pode continuar",
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
                "[LOGIN] Popup de login fechado. Continuando fluxo mesmo assim."
            )

        popup.protocol("WM_DELETE_WINDOW", on_close)

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------
    def _log(self, message: str):
        """Centraliza logs: manda para a Tela 1 (se existir) e para o terminal."""
        if self.add_offers_frame:
            self.add_offers_frame.append_log(message)
        print(message)


# ======================================================================
# Tela 1: Add Offers
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
        # Título
        lbl_title = ctk.CTkLabel(
            self,
            text="Add Offers",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=PALETTE["text_primary"],
        )
        lbl_title.pack(anchor="w", padx=20, pady=(20, 10))

        # Seção CSV
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

        # Botões Open / Clear
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
        
        # Botão Add Brainrots
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
        """Atualiza labels de arquivo selecionado e contagem de itens."""
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
        self.txt_logs.insert(tk.END, f"{message}\n")
        self.txt_logs.see(tk.END)

    def _on_add_brainrots_clicked(self):
        self.app._log("Abrindo formulário de inserção (New Insert)...")
        self.app.open_insertion_window()


# ======================================================================
# Tela 2: Configs
# ======================================================================
class ConfigFrame(ctk.CTkFrame):
    def __init__(self, master, app: BotApp):
        super().__init__(master, fg_color=PALETTE["content_bg"])
        self.app = app

        self.entry_profile: ctk.CTkEntry | None = None
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

        ctk.CTkLabel(
            row_profile,
            text="Chrome Profile Path:",
            text_color=PALETTE["text_secondary"],
        ).pack(side="left", padx=5)
        self.entry_profile = ctk.CTkEntry(
            row_profile,
            width=380,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.entry_profile.pack(side="left", padx=5)

        btn_escolher_profile = ctk.CTkButton(
            row_profile,
            text="Browse",
            width=80,
            command=self._choose_profile_dir,
            fg_color=PALETTE["muted"],
            hover_color=PALETTE["muted_hover"],
            text_color=PALETTE["text_primary"],
        )
        btn_escolher_profile.pack(side="left", padx=5)

        # Descrição padrão
        row_desc = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        row_desc.pack(fill="both", expand=True, **padding)

        ctk.CTkLabel(
            row_desc,
            text="Default Description:",
            text_color=PALETTE["text_secondary"],
        ).pack(anchor="w", padx=5, pady=(10, 5))

        self.txt_descricao_padrao = ctk.CTkTextbox(
            row_desc,
            height=220,
            fg_color=PALETTE["entry_bg"],
            text_color=PALETTE["text_primary"],
        )
        self.txt_descricao_padrao.pack(fill="both", expand=True, padx=5, pady=5)

        # Botões Reset / Save
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
        """Carrega valores atuais de Settings nos campos."""
        if not self.entry_profile or not self.txt_descricao_padrao:
            return

        self.entry_profile.delete(0, "end")
        self.entry_profile.insert(0, str(self.app.settings.chrome_profile_path))

        self.txt_descricao_padrao.delete("1.0", "end")
        self.txt_descricao_padrao.insert("1.0", self.app.settings.descricao_padrao)

    def _choose_profile_dir(self):
        d = filedialog.askdirectory(
            title="Selecione a pasta do perfil do Chrome",
            initialdir=str(self.app.settings.chrome_profile_path)
            if self.app.settings.chrome_profile_path
            else ".",
        )
        if d and self.entry_profile:
            self.entry_profile.delete(0, "end")
            self.entry_profile.insert(0, d)

    def _on_reset_default(self):
        defaults = Settings.defaults()

        self.app.settings.chrome_profile_path = defaults.chrome_profile_path
        self.app.settings.descricao_padrao = defaults.descricao_padrao
        self.app.settings.csv_ativo_path = defaults.csv_ativo_path
        self.app.settings.pasta_logs = defaults.pasta_logs
        self.app.settings.pasta_imagens = defaults.pasta_imagens

        self.app.settings.save()
        self.load_from_settings()
        self.app._log("Configurações resetadas para o padrão.")
        self.app._refresh_main_info()

    def _on_save(self):
        if not self.entry_profile or not self.txt_descricao_padrao:
            return

        profile = self.entry_profile.get().strip()
        descricao = self.txt_descricao_padrao.get("1.0", "end").strip()

        if profile:
            self.app.settings.chrome_profile_path = Path(profile)
        self.app.settings.descricao_padrao = (
            descricao or self.app.settings.descricao_padrao
        )

        self.app.settings.save()
        self.app._log("Configurações salvas.")
        self.app._refresh_main_info()


# ======================================================================
# Janela de Nova Inserção (New Insert / Add Brainrots)
# ======================================================================
class NovaInsercaoWindow(ctk.CTkToplevel):
    """
    Janela para adicionar brainrots (New Insert).
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

        # Opções de modo de adição
        self.frame_opcoes = ctk.CTkFrame(self, fg_color=PALETTE["card_bg"])
        self.frame_opcoes.pack(fill="x", padx=20, pady=10)

        lbl_modo = ctk.CTkLabel(
            self.frame_opcoes,
            text="How you want to add the brainrots?",
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
        
        
        row_qtd = ctk.CTkFrame(self.frame_form, fg_color=PALETTE["card_bg"]) # Row for Price and Quantity
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

        # Botões
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

    # ---------------------- validações ----------------------
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
            title="Selecione a imagem do brainrot",
            initialdir=initial_dir,
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("Todos os arquivos", "*.*"),
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
        self.master._log("Nova Inserção cancelada pelo usuário.")
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
            messagebox.showerror("Erro de validação", "O campo 'Name' é obrigatório.")
            return None

        if not qtd_raw:
            messagebox.showerror(
                "Erro de validação", "O campo 'Quantity' é obrigatório."
            )
            return None

        if not preco_raw:
            messagebox.showerror(
                "Erro de validação", "O campo 'Price' é obrigatório."
            )
            return None

        try:
            quantidade = int(qtd_raw)
            if quantidade <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Erro de validação",
                "Quantity deve ser um número inteiro positivo.",
            )
            return None

        try:
            preco = Decimal(preco_raw.replace(",", "."))
        except (InvalidOperation, AttributeError):
            messagebox.showerror(
                "Erro de validação",
                "Preço inválido. Use apenas números, ponto ou vírgula.",
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
            f"[Inserção] Item '{item.nome}' adicionado/incrementado no CSV ativo."
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
                    f"[Inserção] Item '{item.nome}' adicionado/incrementado no CSV ativo (antes de iniciar o bot)."
                )
                if self.refresh_main_callback:
                    self.refresh_main_callback()

        self.master._log("Iniciando fluxo de inserção (bot)...")
        self.destroy()

        if self.start_bot_callback:
            self.start_bot_callback()


# ----------------------------------------------------------------------
# Execução direta
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = BotApp()
    app.mainloop()
