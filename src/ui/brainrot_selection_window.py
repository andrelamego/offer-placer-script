# src/ui/brainrot_selection_window.py

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable

from PIL import Image, ImageTk
from tkinter import messagebox  # para avisos

from difflib import SequenceMatcher
from src.core.brainrots_data import BRAINROT_NAMES


def _normalize_name(s: str) -> str:
    return " ".join(s.lower().split())


def best_catalog_match(query: str, catalog: list[str], min_ratio: float = 0.62) -> str | None:
    """Retorna o nome do catálogo mais parecido com 'query', se passar do limiar."""
    q = _normalize_name(query)
    best_name, best_score = None, 0.0
    for cand in catalog:
        score = SequenceMatcher(None, q, _normalize_name(cand)).ratio()
        if score > best_score:
            best_name, best_score = cand, score
    return best_name if best_name and best_score >= min_ratio else None


@dataclass
class SelectedRegion:
    """Bounding box em coordenadas da imagem original."""
    x1: int
    y1: int
    x2: int
    y2: int


class BrainrotSelectionWindow(ctk.CTkToplevel):
    """
    Janela onde o usuário desenha retângulos em volta de cada brainrot.
    
    - Clique e arraste para criar um retângulo;
    - Solte o botão para confirmar a seleção;
    - Botão 'Undo last' remove o último;
    - Botão 'Done' retorna todas as regiões selecionadas via callback.
    """

    def __init__(
        self,
        master: ctk.CTk,
        image_path: str | Path,
        on_done: Callable[[List[SelectedRegion]], None],
        max_width: int = 900,
        max_height: int = 600,
    ):
        super().__init__(master)
        self.title("Select brainrots")
        self.configure(fg_color="#2F2F2F")
        self.resizable(False, False)

        # modal
        self.grab_set()
        # ❌ REMOVIDO focus_force() para evitar TclError
        # self.focus_force()
        self.lift()  # opcional, só pra trazer pra frente

        self.image_path = Path(image_path)
        self.on_done = on_done

        # armazenar retângulos
        self.regions: List[SelectedRegion] = []

        # coords do retângulo atual (em coords do canvas)
        self._start_x: int | None = None
        self._start_y: int | None = None
        self._current_rect_id: int | None = None

        # escala imagem_original -> canvas
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0

        self._build_ui(max_width, max_height)

        # se o usuário fechar na janela (X), apenas destrói sem callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self, max_width: int, max_height: int):
        # Carrega imagem original
        img = Image.open(self.image_path)
        orig_w, orig_h = img.size

        # calcula escala pra caber na janela
        scale = min(max_width / orig_w, max_height / orig_h, 1.0)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        self._scale_x = orig_w / new_w
        self._scale_y = orig_h / new_h

        self._img_display = img.resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(self._img_display)  # manter referência

        # canvas pra desenhar
        self.canvas = tk.Canvas(
            self,
            width=new_w,
            height=new_h,
            highlightthickness=0,
            bg="#1F2933",
        )
        self.canvas.pack(padx=10, pady=(10, 5))

        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

        # binds do mouse
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # barra inferior com botões e dica
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(5, 10))

        lbl_hint = ctk.CTkLabel(
            bottom,
            text="Click and drag to select each brainrot. Use 'Undo last' if needed.",
            text_color="#E5E7EB",
        )
        lbl_hint.pack(anchor="w")

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(anchor="e", pady=(5, 0))

        self.btn_undo = ctk.CTkButton(
            btn_row,
            text="Undo last",
            width=110,
            fg_color="#4B5563",
            hover_color="#374151",
            text_color="white",
            command=self._on_undo,
        )
        self.btn_undo.pack(side="left", padx=(0, 10))

        self.btn_done = ctk.CTkButton(
            btn_row,
            text="Done",
            width=110,
            fg_color="#E5A000",
            hover_color="#AF7B00",
            text_color="black",
            command=self._on_done_click,
        )
        self.btn_done.pack(side="left")

    # ---------------- mouse handlers ----------------

    def _on_mouse_down(self, event):
        self._start_x = event.x
        self._start_y = event.y

        # cria retângulo "temporário"
        if self._current_rect_id is not None:
            self.canvas.delete(self._current_rect_id)

        self._current_rect_id = self.canvas.create_rectangle(
            self._start_x,
            self._start_y,
            event.x,
            event.y,
            outline="#FBBF24",
            width=2,
        )

    def _on_mouse_drag(self, event):
        if (
            self._current_rect_id is not None
            and self._start_x is not None
            and self._start_y is not None
        ):
            self.canvas.coords(
                self._current_rect_id,
                self._start_x,
                self._start_y,
                event.x,
                event.y,
            )

    def _on_mouse_up(self, event):
        if (
            self._current_rect_id is None
            or self._start_x is None
            or self._start_y is None
        ):
            return

        x1, y1, x2, y2 = self.canvas.coords(self._current_rect_id)
        # normaliza (x1 < x2, y1 < y2)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))

        # ignora retângulos muito pequenos (clique acidental)
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.canvas.delete(self._current_rect_id)
            self._current_rect_id = None
            return

        # converte coords de canvas → coords da imagem original
        img_x1 = int(x1 * self._scale_x)
        img_y1 = int(y1 * self._scale_y)
        img_x2 = int(x2 * self._scale_x)
        img_y2 = int(y2 * self._scale_y)

        self.regions.append(SelectedRegion(img_x1, img_y1, img_x2, img_y2))

        # coloca um label com o índice no canto
        idx = len(self.regions)
        self.canvas.create_text(
            x1 + 8,
            y1 + 8,
            text=str(idx),
            anchor="nw",
            fill="#FBBF24",
            font=("Segoe UI", 10, "bold"),
        )

        # "finaliza" esse retângulo e libera para outro
        self._current_rect_id = None
        self._start_x = None
        self._start_y = None

    # ---------------- buttons ----------------

    def _on_undo(self):
        if not self.regions:
            return

        # apaga TUDO e redesenha, mais simples
        self.regions.pop()

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

        # redesenha todos os retângulos e índices
        for i, r in enumerate(self.regions, start=1):
            # volta coords pra canvas
            x1 = r.x1 / self._scale_x
            y1 = r.y1 / self._scale_y
            x2 = r.x2 / self._scale_x
            y2 = r.y2 / self._scale_y
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="#FBBF24",
                width=2,
            )
            self.canvas.create_text(
                x1 + 8,
                y1 + 8,
                text=str(i),
                anchor="nw",
                fill="#FBBF24",
                font=("Segoe UI", 10, "bold"),
            )

    def _on_done_click(self):
        # garante pelo menos 1 seleção
        if not self.regions:
            messagebox.showwarning(
                "No selection",
                "Please select at least one brainrot region.",
                parent=self,
            )
            return

        if self.on_done:
            self.on_done(self.regions)

        self._close()

    def _on_close(self):
        """Handler quando o usuário fecha no X da janela."""
        self._close()

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
