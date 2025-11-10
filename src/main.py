# main.py
from __future__ import annotations

import customtkinter as ctk

from src.ui.app import BotApp, LicenseWindow
from src.core.license_client import load_config, verify_license, save_config, LicenseConfig


def ensure_valid_license(root: ctk.CTk) -> bool:
    """
    Garante que existe uma key válida.
    Abre janela de licença se precisar.
    Retorna True se estiver tudo ok, False se o usuário cancelar.
    """
    cfg: LicenseConfig = load_config()

    # 1) se já tem key salva, verifica
    if cfg.license_key:
        result = verify_license(cfg.license_key, cfg.client_id)
        if result.valid:
            return True  # tudo certo

    # 2) se não tem key ou key inválida -> abrir janela
    done = {"ok": False}

    def _on_success(new_key: str):
        done["ok"] = True

    win = LicenseWindow(root, cfg, on_success=_on_success)
    root.wait_window(win)  # bloqueia até a janela fechar

    return done["ok"]


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    #root "invisível" só pra gerenciar janelas
    root = ctk.CTk()
    root.withdraw()  # esconde até ter licença válida

    if not ensure_valid_license(root):
        # usuário cancelou ou algo deu muito errado
        return

    #abrir o app principal
    app = BotApp()
    # opcional: destruir o root invisível
    root.destroy()
    app.mainloop()


if __name__ == "__main__":
    main()
