# src/ui/brainrot_review_window.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import customtkinter as ctk
from PIL import Image
import tkinter as tk
import tkinter.messagebox as messagebox
import re
from difflib import SequenceMatcher

from src.core.brainrots_data import BRAINROT_NAMES  # sua lista de nomes oficiais


# -------------------------------------------------------------------
# Helpers para normalizar / casar nome com catálogo
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Resultado final da revisão (o que volta pro fluxo principal)
# -------------------------------------------------------------------

@dataclass
class BrainrotReviewResult:
    name: str
    variation: str
    gen_per_s: str
    title: str
    use_default_desc: bool
    description: str
    quantity: int
    price: float
    image_path: str


# -------------------------------------------------------------------
# Janela de resumo final
# -------------------------------------------------------------------

class BrainrotSummaryWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        items: List[BrainrotReviewResult],
        on_confirm: Callable[[List[BrainrotReviewResult]], None],
    ):
        super().__init__(master)
        self.title("Summary: brainrots to insert")
        self.configure(fg_color="#2F2F2F")
        self.resizable(False, False)
        self.grab_set()

        self.items = items
        self.on_confirm = on_confirm

        # Layout
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self,
            text="Review summary",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#F9FAFB",
        )
        title.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(
            self,
            text="These brainrots will be added to the CSV. Confirm to continue.",
            text_color="#9CA3AF",
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 10))

        # Scrollable area
        frame_scroll = ctk.CTkScrollableFrame(self, fg_color="#373737", height=260)
        frame_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for idx, item in enumerate(self.items, start=1):
            row = ctk.CTkFrame(frame_scroll, fg_color="#414141")
            row.pack(fill="x", padx=5, pady=5)

            header = ctk.CTkLabel(
                row,
                text=f"#{idx}  {item.title}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#F9FAFB",
            )
            header.pack(anchor="w", padx=10, pady=(6, 0))

            info = (
                f"Name: {item.name}"
                f"\nVariation: {item.variation or '-'}"
                f"\nGen/s: {item.gen_per_s or '-'}"
                f"\nQuantity: {item.quantity}   Price: {item.price:.2f}"
            )
            lbl = ctk.CTkLabel(
                row,
                text=info,
                text_color="#D1D5DB",
                justify="left",
            )
            lbl.pack(anchor="w", padx=10, pady=(2, 8))

        # Buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 15))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Back",
            fg_color="#4B5563",
            hover_color="#374151",
            text_color="white",
            width=110,
            command=self._on_back,
        )
        btn_cancel.pack(side="left")

        btn_ok = ctk.CTkButton(
            btn_row,
            text="Confirm",
            fg_color="#E5A000",
            hover_color="#AF7B00",
            text_color="black",
            width=110,
            command=self._on_confirm,
        )
        btn_ok.pack(side="right")

    def _on_back(self):
        self.grab_release()
        self.destroy()

    def _on_confirm(self):
        if self.on_confirm:
            self.on_confirm(self.items)
        self.grab_release()
        self.destroy()


# -------------------------------------------------------------------
# Janela principal de revisão (wizard: 1 brainrot por vez)
# -------------------------------------------------------------------

class BrainrotReviewWindow(ctk.CTkToplevel):
    """
    Mostra UM brainrot por vez para revisão.
    """

    def __init__(
        self,
        master: ctk.CTk,
        brainrots: List[object],          # objetos com atributos: nome, geracao_por_segundo, variation?, imagem_full_path
        default_description: str,
        on_done: Callable[[List[BrainrotReviewResult]], None],
    ):
        super().__init__(master)
        self.title("Review brainrots")
        self.configure(fg_color="#2F2F2F")
        self.resizable(False, False)
        self.grab_set()

        self.default_description = default_description or ""
        self.on_done = on_done

        # Normaliza dados de entrada para uma lista de dicts editáveis
        self.items: List[dict] = self._build_initial_items(brainrots)
        self.current_index: int = 0
        self._image_cache: Optional[ctk.CTkImage] = None

        # CTk variables
        self.var_name = tk.StringVar()
        self.var_variation = tk.StringVar()
        self.var_gen = tk.StringVar()
        self.var_title = tk.StringVar()
        self.var_use_default_desc = tk.BooleanVar(value=True)
        self.var_quantity = tk.StringVar(value="1")
        self.var_price = tk.StringVar(value="0.00")

        # Widgets referenciados
        self.txt_description: Optional[ctk.CTkTextbox] = None
        self.lbl_index: Optional[ctk.CTkLabel] = None
        self.btn_prev: Optional[ctk.CTkButton] = None
        self.btn_next: Optional[ctk.CTkButton] = None
        self.lbl_image: Optional[ctk.CTkLabel] = None

        self.entry_name: Optional[ctk.CTkEntry] = None
        self.entry_var: Optional[ctk.CTkEntry] = None
        self.entry_gen: Optional[ctk.CTkEntry] = None
        self.entry_title: Optional[ctk.CTkEntry] = None
        self.entry_qty: Optional[ctk.CTkEntry] = None
        self.entry_price: Optional[ctk.CTkEntry] = None

        self._build_ui()
        self._load_current_item()

    # ----------------------------------------------------------------
    # Construção dos dados iniciais
    # ----------------------------------------------------------------

    def _build_initial_items(self, brainrots: List[object]) -> List[dict]:
        items: List[dict] = []
        for br in brainrots:
            ocr_name = (getattr(br, "nome", "") or "").strip()
            ocr_gen = (getattr(br, "geracao_por_segundo", "") or "").strip()
            ocr_var = (getattr(br, "variation", "") or "").strip()
            img_path = str(getattr(br, "imagem_full_path", "") or "")

            # Ajusta nome com base no catálogo
            matched = best_catalog_match(ocr_name, BRAINROT_NAMES) if ocr_name else None
            name_for_user = matched or ocr_name

            items.append(
                {
                    "image_path": img_path,
                    "ocr_name": ocr_name,
                    "name": name_for_user,
                    "variation": ocr_var,
                    "gen": ocr_gen,
                    "use_default_desc": True,
                    "description": self.default_description,
                    "quantity": 1,
                    "price": "0.00",
                }
            )
        return items

    # ----------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        # Título
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))

        lbl_title = ctk.CTkLabel(
            header,
            text="Review brainrot",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#F9FAFB",
        )
        lbl_title.pack(side="left")

        self.lbl_index = ctk.CTkLabel(
            header,
            text="",
            text_color="#9CA3AF",
        )
        self.lbl_index.pack(side="right")

        main = ctk.CTkFrame(self, fg_color="#373737")
        main.pack(fill="both", expand=True, padx=20, pady=10)

        # Esquerda: imagem
        left = ctk.CTkFrame(main, fg_color="#414141", width=260)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        self.lbl_image = ctk.CTkLabel(left, text="")
        self.lbl_image.pack(padx=10, pady=10)

        # Direita: campos
        right = ctk.CTkFrame(main, fg_color="#414141")
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        # Name
        row_name = ctk.CTkFrame(right, fg_color="transparent")
        row_name.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            row_name,
            text="Name:",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_name = ctk.CTkEntry(
            row_name,
            textvariable=self.var_name,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.entry_name.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Variation
        row_var = ctk.CTkFrame(right, fg_color="transparent")
        row_var.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            row_var,
            text="Variation:",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_var = ctk.CTkEntry(
            row_var,
            textvariable=self.var_variation,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.entry_var.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Gen/s
        row_gen = ctk.CTkFrame(right, fg_color="transparent")
        row_gen.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            row_gen,
            text="Gen/s (ex: 12.5M):",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_gen = ctk.CTkEntry(
            row_gen,
            textvariable=self.var_gen,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.entry_gen.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Title (preview)
        row_title = ctk.CTkFrame(right, fg_color="transparent")
        row_title.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            row_title,
            text="Title (preview):",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_title = ctk.CTkEntry(
            row_title,
            textvariable=self.var_title,
            fg_color="#111827",
            text_color="#FBBF24",
            state="disabled",
        )
        self.entry_title.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Checkbox descrição padrão
        row_chk = ctk.CTkFrame(right, fg_color="transparent")
        row_chk.pack(fill="x", padx=10, pady=(5, 0))
        chk = ctk.CTkCheckBox(
            row_chk,
            text="Use default description?",
            variable=self.var_use_default_desc,
            text_color="#E5E7EB",
            command=self._on_toggle_default_desc,
            fg_color="#1F2933",
            border_color="#111827",
            checkmark_color="#E5A000",
        )
        chk.pack(anchor="w")

        # Descrição
        row_desc = ctk.CTkFrame(right, fg_color="transparent")
        row_desc.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        ctk.CTkLabel(
            row_desc,
            text="Description:",
            text_color="#E5E7EB",
        ).pack(anchor="w")

        self.txt_description = ctk.CTkTextbox(
            row_desc,
            height=120,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.txt_description.pack(fill="both", expand=True, pady=(4, 0))

        # Quantity & Price
        row_qp = ctk.CTkFrame(right, fg_color="transparent")
        row_qp.pack(fill="x", padx=10, pady=(0, 10))

        # Quantity
        ctk.CTkLabel(
            row_qp,
            text="Quantity:",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_qty = ctk.CTkEntry(
            row_qp,
            width=80,
            textvariable=self.var_quantity,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.entry_qty.pack(side="left", padx=(5, 15))

        # Price
        ctk.CTkLabel(
            row_qp,
            text="Price:",
            text_color="#E5E7EB",
        ).pack(side="left")
        self.entry_price = ctk.CTkEntry(
            row_qp,
            width=80,
            textvariable=self.var_price,
            fg_color="#1F2933",
            text_color="#F9FAFB",
        )
        self.entry_price.pack(side="left", padx=(5, 0))

        # Rodapé: botões Anterior / Próximo
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_prev = ctk.CTkButton(
            footer,
            text="Previous",
            width=110,
            fg_color="#4B5563",
            hover_color="#374151",
            text_color="white",
            command=self._on_prev,
        )
        self.btn_prev.pack(side="left")

        self.btn_next = ctk.CTkButton(
            footer,
            text="Next",
            width=110,
            fg_color="#E5A000",
            hover_color="#AF7B00",
            text_color="black",
            command=self._on_next,
        )
        self.btn_next.pack(side="right")

        # Atualiza preview do título quando nome/var/gen mudarem
        for v in (self.var_name, self.var_variation, self.var_gen):
            v.trace_add("write", lambda *_: self._update_title_preview())

    # ----------------------------------------------------------------
    # Carregar / salvar estado da página atual
    # ----------------------------------------------------------------

    def _update_title_preview(self):
        name = self.var_name.get().strip()
        variation = self.var_variation.get().strip()
        gen_raw = self.var_gen.get().strip()

        base = (name + (" " + variation if variation else "")).strip()

        if not gen_raw:
            self.var_title.set(base)
            return

        # Normaliza gen_raw para algo tipo "$12.5M/s"
        t = gen_raw.replace(" ", "")
        # se já parece algo como "$xx/s", só limpa levemente
        if "$" in t and "/s" in t:
            gen_norm = t
        else:
            # tira símbolos soltos e recompõe
            t = t.replace("$", "")
            t = re.sub(r"/s$", "", t, flags=re.IGNORECASE)
            gen_norm = f"${t}/s"

        title = f"{base} - {gen_norm}" if base else gen_norm
        self.var_title.set(title)

    def _load_current_item(self):
        item = self.items[self.current_index]

        # índice
        if self.lbl_index:
            self.lbl_index.configure(
                text=f"{self.current_index + 1} / {len(self.items)}"
            )

        # imagem
        img_path = item.get("image_path") or ""
        if img_path and Path(img_path).exists():
            pil_img = Image.open(img_path)
            # tamanho máximo do preview
            max_w, max_h = 220, 220
            pil_img.thumbnail((max_w, max_h), Image.LANCZOS)
            self._image_cache = ctk.CTkImage(light_image=pil_img, size=pil_img.size)
            if self.lbl_image:
                self.lbl_image.configure(image=self._image_cache, text="")
        else:
            if self.lbl_image:
                self.lbl_image.configure(image=None, text="(no image)")

        # campos
        self.var_name.set(item.get("name", ""))
        self.var_variation.set(item.get("variation", ""))
        self.var_gen.set(item.get("gen", ""))

        # descrição / checkbox
        self.var_use_default_desc.set(bool(item.get("use_default_desc", True)))
        desc_text = item.get("description", self.default_description)

        if self.txt_description:
            self.txt_description.configure(state="normal")
            self.txt_description.delete("1.0", "end")
            self.txt_description.insert("1.0", desc_text)
            self._apply_desc_state()

        # quantity / price
        self.var_quantity.set(str(item.get("quantity", 1)))
        self.var_price.set(str(item.get("price", "0.00")))

        # título
        self._update_title_preview()

        # estado dos botões
        if self.btn_prev:
            self.btn_prev.configure(state="normal" if self.current_index > 0 else "disabled")

        if self.btn_next:
            self.btn_next.configure(
                text="Finish" if self.current_index == len(self.items) - 1 else "Next"
            )

    def _apply_desc_state(self):
        if not self.txt_description:
            return
        if self.var_use_default_desc.get():
            # força descrição padrão e bloqueia
            self.txt_description.configure(state="normal")
            self.txt_description.delete("1.0", "end")
            self.txt_description.insert("1.0", self.default_description)
            self.txt_description.configure(state="disabled")
        else:
            self.txt_description.configure(state="normal")

    # ----------------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------------

    def _on_toggle_default_desc(self):
        self._apply_desc_state()

    def _on_prev(self):
        if self.current_index == 0:
            return
        if not self._save_current():
            return
        self.current_index -= 1
        self._load_current_item()

    def _on_next(self):
        """Valida o formulário atual e avança para o próximo brainrot."""
        if not self._save_current():
            return

        # Vai para o próximo
        if self.current_index >= len(self.items) - 1:
            # Último → abre resumo
            self._open_summary()
        else:
            self.current_index += 1
            self._load_current_item()

    def _save_current(self) -> bool:
        """Valida e grava os dados da página atual em self.items."""
        item = self.items[self.current_index]

        name = self.var_name.get().strip()
        gen = self.var_gen.get().strip()
        variation = self.var_variation.get().strip()
        title = self.var_title.get().strip()
        use_default_desc = bool(self.var_use_default_desc.get())

        # descrição
        if self.txt_description:
            if use_default_desc:
                desc = self.default_description
            else:
                desc = self.txt_description.get("1.0", "end").strip()
        else:
            desc = self.default_description

        # quantity
        qty_raw = self.var_quantity.get().strip()
        if not qty_raw.isdigit() or int(qty_raw) <= 0:
            messagebox.showerror(
                "Validation error",
                "Quantity must be a positive integer.",
                parent=self,
            )
            return False
        quantity = int(qty_raw)

        # price
        price_raw = self.var_price.get().strip().replace(",", ".")
        if not price_raw:
            messagebox.showerror(
                "Validation error",
                "Price is required.",
                parent=self,
            )
            return False

        try:
            price = float(price_raw)
            if price <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Validation error",
                "Price must be a number greater than zero.",
                parent=self,
            )
            return False

        if not name:
            messagebox.showerror(
                "Validation error",
                "Name is required.",
                parent=self,
            )
            return False

        # atualiza item
        item["name"] = name
        item["variation"] = variation
        item["gen"] = gen
        item["title"] = title
        item["use_default_desc"] = use_default_desc
        item["description"] = desc
        item["quantity"] = quantity
        item["price"] = f"{price:.2f}"

        return True

    # ----------------------------------------------------------------
    # Resumo final + callback
    # ----------------------------------------------------------------

    def _build_results(self) -> List[BrainrotReviewResult]:
        results: List[BrainrotReviewResult] = []
        for item in self.items:
            name = item.get("name", "").strip()
            variation = item.get("variation", "").strip()
            gen = item.get("gen", "").strip()
            image_path = item.get("image_path", "")

            # Recalcula título pra garantir consistência
            base = (name + (" " + variation if variation else "")).strip()
            if gen:
                t = gen.replace(" ", "")
                if "$" in t and "/s" in t:
                    gen_norm = t
                else:
                    t = t.replace("$", "")
                    t = re.sub(r"/s$", "", t, flags=re.IGNORECASE)
                    gen_norm = f"${t}/s"
                title = f"{base} - {gen_norm}" if base else gen_norm
            else:
                title = base

            desc = item.get("description", self.default_description)
            qty = int(item.get("quantity", 1))
            price = float(str(item.get("price", "0.00")).replace(",", "."))

            results.append(
                BrainrotReviewResult(
                    name=name,
                    variation=variation,
                    gen_per_s=gen,
                    title=title,
                    use_default_desc=bool(item.get("use_default_desc", True)),
                    description=desc,
                    quantity=qty,
                    price=price,
                    image_path=image_path,
                )
            )
        return results

    def _open_summary(self):
        # Monta a lista de BrainrotReviewResult
        results = self._build_results()

        def _on_confirm(final_items: List[BrainrotReviewResult]):
            # Converte os objetos em dicts simples, no formato que o app.py espera
            if self.on_done:
                payload = [
                    {
                        "name": it.name,
                        "variation": it.variation,
                        "gen_per_s": it.gen_per_s,
                        "title": it.title,
                        "use_default_desc": it.use_default_desc,
                        "description": it.description,
                        "quantity": it.quantity,
                        "price": it.price,
                        "image_path": it.image_path,
                    }
                    for it in final_items
                ]
                self.on_done(payload)

            self.grab_release()
            self.destroy()

        # Abre a janela de resumo passando a lista de BrainrotReviewResult
        BrainrotSummaryWindow(self, results, on_confirm=_on_confirm)
