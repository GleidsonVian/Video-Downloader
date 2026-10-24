"""Ponto de entrada do Downloader Pro."""
import sys


def baixar_com_ytdlp():
    """Modo usado pelo .exe para baixar num processo separado (equivale a "python -m yt_dlp")"""
    import yt_dlp
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    yt_dlp.main(sys.argv[2:])
    sys.exit(0)


def abrir_programa():
    import tkinter as tk
    from downloader_pro.interface import JanelaPrincipal
    root = tk.Tk()
    JanelaPrincipal(root)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ytdlp":
        baixar_com_ytdlp()
    abrir_programa()
