"""Janela principal: baixar vídeo ou música e abrir o editor."""
import os
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import cookies, ytdlp
from .arquivos import limpar_temporarios
from .config import ICONE, PASTA_MUSICAS, PASTA_VIDEOS
from .editor import JanelaEditor
from .sistema import agendar, encerrar_processo


class JanelaPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Downloader Pro (1080p/720p)")
        self.root.geometry("540x380")
        self.root.configure(padx=20, pady=15)
        if os.path.exists(ICONE):
            self.root.iconbitmap(ICONE)
        self.editor = None
        self.video_pendente = None  # último vídeo baixado, que o editor usa na próxima vez que for aberto
        self.processos = {}  # processos externos em andamento ("download", "corte"), para encerrar ao fechar
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.criar_widgets()

    def criar_widgets(self):
        root = self.root
        tk.Label(root, text="URL do Vídeo (Prioridade 1080p):", font=("Arial", 10, "bold")).pack()
        self.url_entry = tk.Entry(root, width=55)
        self.url_entry.pack(pady=8)

        botoes = tk.Frame(root)
        botoes.pack(pady=5, fill=tk.X)
        self.btn_download = tk.Button(botoes, text="BAIXAR VÍDEO", command=self.start_download_thread,
                                      bg="#c4302b", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_download.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_audio = tk.Button(botoes, text="♪ SÓ ÁUDIO (MP3)",
                                   command=lambda: self.start_download_thread(somente_audio=True),
                                   bg="#7a3db8", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_audio.pack(side=tk.LEFT, padx=(6, 0))

        self.progress_label = tk.Label(root, text="Aguardando link...")
        self.progress_label.pack()
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=5)
        texto, cor = cookies.texto_status()
        self.status_label = tk.Label(root, text=texto, font=("Arial", 8), fg=cor, wraplength=480)
        self.status_label.pack()

        ttk.Separator(root, orient="horizontal").pack(fill=tk.X, pady=14)
        tk.Button(root, text="✂  EDITAR VÍDEO  (cortes e música de fundo)", command=self.abrir_editor,
                  bg="#2b6cc4", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill=tk.X)
        self.editar_dica = tk.Label(root, text="Abre com o último vídeo baixado (ou escolha outro dentro do editor)",
                                    font=("Arial", 8), fg="gray")
        self.editar_dica.pack(pady=(4, 0))

    def na_tela(self, funcao, *args, **kwargs):
        agendar(self.root, funcao, *args, **kwargs)

    def ao_fechar(self):
        for processo in self.processos.values():
            encerrar_processo(processo)
        self.root.destroy()

    # --- Editor ---
    def abrir_editor(self):
        """Abre o editor (ou traz o que já está aberto para a frente).

        Se um vídeo acabou de ser baixado, o editor já abre com ele; fora isso, o vídeo
        é escolhido dentro do editor.
        """
        if not (self.editor and self.editor.janela.winfo_exists()):
            self.editor = JanelaEditor(self.root, lambda p: self.processos.__setitem__("corte", p))
        if self.video_pendente:
            self.editor.selecionar_video(self.video_pendente)
            self.video_pendente = None
        self.editor.janela.deiconify()
        self.editor.janela.lift()

    def musica_baixada(self, caminho):
        self.progress_label.config(text="Música pronta! Escolha-a em \"Áudio do corte\" no editor.")
        if self.editor and self.editor.janela.winfo_exists():
            self.editor.painel_audio.atualizar_musicas(caminho)

    # --- Download ---
    def start_download_thread(self, somente_audio=False):
        threading.Thread(target=self.download, args=(somente_audio,), daemon=True).start()

    def mostrar_progresso(self, percent, somente_audio):
        if percent >= 100:
            texto = "Convertendo para MP3..." if somente_audio else "Mesclando áudio e vídeo (quase pronto)..."
        else:
            texto = f"Baixando: {percent}%"
        self.na_tela(self.progress_bar.config, value=percent)
        self.na_tela(self.progress_label.config, text=texto)

    def download(self, somente_audio=False):
        url = self.url_entry.get().strip()
        if not url:
            self.na_tela(messagebox.showwarning, "Aviso", "Por favor, cole um link!")
            return

        self.na_tela(self.btn_download.config, state="disabled")
        self.na_tela(self.btn_audio.config, state="disabled")
        os.makedirs(PASTA_MUSICAS if somente_audio else PASTA_VIDEOS, exist_ok=True)
        arquivo_cookies = cookies.achar_cookies()
        baixar = lambda paralelos: ytdlp.baixar(
            url, paralelos, arquivo_cookies, somente_audio,
            ao_progresso=lambda p: self.mostrar_progresso(p, somente_audio),
            ao_iniciar=lambda p: self.processos.__setitem__("download", p))

        try:
            # Se o vídeo já foi baixado antes, o yt-dlp reaproveita o arquivo
            caminho, erro, avisos = baixar(8)
            if erro and "not a bot" not in erro and "live event" not in erro:
                # Pedaços quebrados no YouTube travam o download em paralelo; um por vez, o
                # yt-dlp pula esses pedaços. Continua de onde parou, sem baixar tudo de novo.
                self.na_tela(self.progress_label.config, text="Tentando de novo em modo seguro (mais lento)...")
                caminho, erro, avisos = baixar(1)
            if erro:
                raise RuntimeError(erro)
            limpar_temporarios(caminho)
            self.na_tela(self.status_label.config, text="Concluído com sucesso!", fg="green")
            if any("no longer valid" in aviso for aviso in avisos):
                self.na_tela(self.status_label.config, fg="#c47a00",
                             text="Baixou, mas seus cookies não valem mais — exporte de novo antes que o YouTube bloqueie")
            titulo = os.path.splitext(os.path.basename(caminho))[0]
            if somente_audio:
                self.na_tela(self.musica_baixada, caminho)
                self.na_tela(messagebox.showinfo, "Sucesso", f"Música baixada:\n{titulo}")
            else:
                self.video_pendente = caminho
                self.na_tela(self.progress_label.config, text="Pronto! Clique em EDITAR VÍDEO para cortar.")
        except Exception as e:
            erro = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            self.na_tela(messagebox.showerror, "Erro",
                         f"Ocorreu um problema: {erro}\n\n{ytdlp.dica_do_erro(erro, bool(arquivo_cookies))}")
            self.na_tela(self.status_label.config, text="Erro no processo", fg="red")
        finally:
            self.na_tela(self.btn_download.config, state="normal")
            self.na_tela(self.btn_audio.config, state="normal")
            self.na_tela(self.progress_bar.config, value=0)
