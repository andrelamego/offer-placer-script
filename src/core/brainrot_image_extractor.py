# src/core/brainrot_image_extractor.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import re
import logging

import cv2
import numpy as np
from ultralytics import YOLO
import easyocr

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------
# EasyOCR global
# ---------------------------------------------------------------------
# use gpu=False se der erro de CUDA
easy_reader = easyocr.Reader(['en', 'pt'], gpu=True)

# ---------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------

@dataclass
class BrainrotOCRResult:
    nome: Optional[str]
    geracao_por_segundo: Optional[str]
    imagem_full_path: str

@dataclass
class _DetectedBox:
    tipo: str                # ex: "brainrot_name", "brainrot_gen"
    bbox: Tuple[int, int, int, int]
    score: float

# ---------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------

class BrainrotImageExtractor:
    def __init__(
        self,
        yolo_weights_path: str | Path,
        class_map: Optional[Dict[int, str]] = None,
        conf_threshold: float = 0.15,
    ) -> None:

        self.yolo_weights_path = str(yolo_weights_path)
        self.model = YOLO(self.yolo_weights_path)
        self.conf_threshold = conf_threshold

        # ⚠️ mapeia EXATAMENTE as classes do seu data.yaml:
        # names:
        #   0: brainrot_name
        #   1: brainrot_var
        #   2: brainrot_gen
        self.class_map: Dict[int, str] = class_map or {
            0: "brainrot_name",
            1: "brainrot_var",
            2: "brainrot_gen",
        }

        logger.info("BrainrotImageExtractor iniciado com modelo %s", self.yolo_weights_path)

    # ------------------------- API pública -------------------------

    def extrair_de_imagem(self, image_path: str | Path) -> BrainrotOCRResult:
        """
        Recebe o caminho de UM card de brainrot (já recortado) e:
          - usa YOLO OCR pra detectar as regiões de texto
          - roda EasyOCR SOMENTE nos crops dessas regiões
          - extrai nome e geração por segundo
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            raise RuntimeError(f"Falha ao carregar imagem com OpenCV: {image_path}")

        logger.debug("Iniciando extração em %s", image_path)

        # 1) YOLO tenta achar caixas de texto
        boxes = self._detectar_caixas_texto(img_bgr)
        logger.debug("YOLO encontrou %d caixas de texto", len(boxes))

        textos: Dict[str, str] = {}
        if boxes:
            textos = self._ler_textos_por_tipo(img_bgr, boxes)
            logger.debug("Textos por tipo (via caixas): %s", textos)
        else:
            logger.debug("Nenhuma caixa de texto detectada pelo YOLO; não será feito OCR no card inteiro.")

        # 2) Usar SOMENTE os textos vindos das labels do YOLO
        #    mapeando labels -> campos lógicos
        nome_raw = textos.get("brainrot_name") or textos.get("brainrot_var")
        geracao_raw = textos.get("brainrot_gen")

        nome = self._clean_nome(nome_raw)
        geracao = self._clean_geracao(geracao_raw)

        logger.debug("Resultado final -> nome=%r, geracao=%r", nome, geracao)

        return BrainrotOCRResult(
            nome=nome,
            geracao_por_segundo=geracao,
            imagem_full_path=str(image_path.resolve()),
        )

    # ------------------- YOLO OCR BOXES -------------------

    def _detectar_caixas_texto(self, img_bgr: np.ndarray) -> List[_DetectedBox]:
        h, w = img_bgr.shape[:2]
        results = self.model.predict(img_bgr, verbose=False)[0]

        boxes: List[_DetectedBox] = []
        for box in results.boxes:
            score = float(box.conf[0])
            if score < self.conf_threshold:
                continue

            cls_id = int(box.cls[0])
            tipo = self.class_map.get(cls_id)
            if not tipo:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))

            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h))

            boxes.append(_DetectedBox(tipo, (x1, y1, x2, y2), score))

        return boxes

    # ------------------- OCR com EasyOCR -------------------

    def _ler_textos_por_tipo(
        self,
        img_bgr: np.ndarray,
        boxes: List[_DetectedBox],
    ) -> Dict[str, str]:

        textos: Dict[str, str] = {}

        for box in boxes:
            x1, y1, x2, y2 = box.bbox
            crop = img_bgr[y1:y2, x1:x2]

            if crop.size == 0:
                continue

            texto = self._ocr_crop(crop)
            logger.debug("OCR box tipo=%s texto=%r", box.tipo, texto)

            if not texto:
                continue

            # agrupa textos por tipo de label do YOLO
            if box.tipo in textos:
                textos[box.tipo] += " " + texto
            else:
                textos[box.tipo] = texto

        return textos

    def _ocr_crop(self, crop_bgr: np.ndarray) -> str:
        """
        Roda EasyOCR APENAS no crop vindo de uma caixa YOLO.
        """
        # pré-processamento: cinza + zoom + binarização (ajuda em texto pequeno)
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        scale = 2.0
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        results = easy_reader.readtext(thresh)

        textos = [text for (_box, text, _conf) in results]
        return " ".join(textos).strip()

    # ------------------- LIMPEZA DE CAMPOS -------------------

    @staticmethod
    def _clean_nome(texto: Optional[str]) -> Optional[str]:
        if not texto:
            return None

        t = texto.strip()

        # corta tudo a partir do primeiro dígito (nome normalmente vem antes de números)
        t = re.split(r"\d", t, maxsplit=1)[0]

        # limpa lixo
        t = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()

        return t or None

    @staticmethod
    def _clean_geracao(texto: Optional[str]) -> Optional[str]:
        if not texto:
            return None

        t = texto

        # normalizações básicas de OCR:
        t = t.replace("O", "0").replace("o", "0")
        t = t.replace(",", ".")
        t = t.replace("S", "$")  # às vezes o $ vira S

        # tenta primeiro achar algo tipo $12.5
        m = re.search(r"\$?\s*(\d+(?:\.\d+)?)", t)
        if m:
            valor = m.group(1)
            return f"${valor}M/s"

        # fallback: procura qualquer número decimal
        m2 = re.search(r"(\d+(?:\.\d+)?)", t)
        if m2:
            valor = m2.group(1)
            return f"${valor}M/s"

        return None


# ---------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------

from src.core.paths import get_base_dir

BASE_DIR = get_base_dir()
MODELS_DIR = BASE_DIR / "src" /"models"

DEFAULT_MODEL_PATH = MODELS_DIR / "brainrot_ocr.pt"

_extractor_singleton: Optional[BrainrotImageExtractor] = None

def get_extractor() -> BrainrotImageExtractor:
    global _extractor_singleton
    if _extractor_singleton is None:
        _extractor_singleton = BrainrotImageExtractor(DEFAULT_MODEL_PATH)
    return _extractor_singleton

def extrair_brainrot(image_path: str | Path) -> BrainrotOCRResult:
    return get_extractor().extrair_de_imagem(image_path)
