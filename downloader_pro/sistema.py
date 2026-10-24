"""Pequenas funções de sistema/janela usadas por mais de uma tela."""
import subprocess
import tkinter as tk

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def agendar(janela, funcao, *args, **kwargs):
    """Executa uma atualização da interface na thread principal (o tkinter não é thread-safe).

    Se a janela já foi fechada quando a hora chegar, a atualização é simplesmente ignorada.
    """
    def executar():
        try:
            funcao(*args, **kwargs)
        except tk.TclError:
            pass
    try:
        janela.after(0, executar)
    except (tk.TclError, RuntimeError):
        pass


def encerrar_processo(processo):
    """Encerra um processo externo (ffmpeg, yt-dlp) e os que ele iniciou"""
    if processo and processo.poll() is None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(processo.pid)], capture_output=True,
                           creationflags=SEM_JANELA)
        except Exception:
            try:
                processo.kill()
            except Exception:
                pass
