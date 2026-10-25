"""Janela principal: baixar vídeo ou música e abrir o editor e a biblioteca."""
import os
import re
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from . import cookies, tema, ytdlp
from .arquivos import limpar_temporarios
from .biblioteca import JanelaBiblioteca
from .config import PASTA_MUSICAS, PASTA_VIDEOS
from .editor import JanelaEditor
from .sistema import agendar, encerrar_processo


class JanelaPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Downloader Pro")
        self.root.geometry("600x500")
        self.root.minsize(520, 480)
        self.root.configure(fg_color=tema.FUNDO)
        tema.aplicar_icone(self.root)
        self.editor = None
        self.biblioteca = None
        self.video_pendente = None  # último vídeo baixado, que o editor usa na próxima vez que for aberto
        self.processos = {}  # processos externos em andamento ("download", "corte"), para encerrar ao fechar
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.criar_widgets()

    def criar_widgets(self):
        root = self.root
        tema.rotulo(root, "Downloader Pro", 28, True).pack(anchor="w", padx=24, pady=(20, 0))
        tema.rotulo(root, "Baixe vídeos e músicas do YouTube e gere cortes prontos para o WhatsApp.", 12,
                    suave=True).pack(anchor="w", padx=24)

        quadro = tema.cartao(root, "Download")
        quadro.pack(fill=tk.X, padx=24, pady=(16, 0))
        self.url_entry = tema.campo(quadro, height=44, placeholder_text="Cole o link do YouTube aqui…")
        self.url_entry.pack(fill=tk.X, padx=16, pady=(10, 0))

        botoes = ctk.CTkFrame(quadro, fg_color="transparent")
        botoes.pack(fill=tk.X, padx=16, pady=(12, 0))
        self.btn_download = tema.botao(botoes, "⬇  Baixar vídeo", tema.VERMELHO, self.start_download_thread, altura=46)
        self.btn_download.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_audio = tema.botao(botoes, "♪  Só áudio (MP3)", tema.ROXO,
                                    lambda: self.start_download_thread(somente_audio=True), altura=46)
        self.btn_audio.pack(side=tk.LEFT, padx=(8, 0))

        self.progress_label = tema.rotulo(quadro, "Aguardando link…", 12, suave=True)
        self.progress_label.pack(anchor="w", padx=16, pady=(14, 0))
        self.progress_bar = tema.barra_progresso(quadro, tema.VERMELHO)
        self.progress_bar.pack(fill=tk.X, padx=16, pady=(6, 0))
        texto, cor = cookies.texto_status()
        self.status_label = tema.rotulo(quadro, texto, 11, suave=True, wraplength=500, justify="left")
        self.status_label.configure(text_color=tema.AMARELO if cor != "gray" else tema.SUAVE)
        self.status_label.pack(anchor="w", padx=16, pady=(6, 14))

        edicao = ctk.CTkFrame(root, fg_color="transparent")
        edicao.pack(fill=tk.X, padx=24, pady=(16, 0))
        tema.botao(edicao, "✂  Editar vídeo", tema.AZUL, self.abrir_editor, altura=52).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        tema.botao(edicao, "📚  Biblioteca", tema.CINZA, self.abrir_biblioteca, altura=52).pack(
            side=tk.LEFT, padx=(8, 0))
        tema.rotulo(root, "O editor abre com o último vídeo baixado (ou escolha outro dentro dele).", 11,
                    suave=True).pack(pady=(8, 0))

    def na_tela(self, funcao, *args, **kwargs):
        agendar(self.root, funcao, *args, **kwargs)

    def ao_fechar(self):
        for processo in self.processos.values():
            encerrar_processo(processo)
        self.root.destroy()

    # --- Editor e biblioteca ---
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
        tema.trazer_para_frente(self.editor.janela)

    def abrir_biblioteca(self):
        """Abre a biblioteca (ou traz a que já está aberta para a frente)"""
        if not (self.biblioteca and self.biblioteca.janela.winfo_exists()):
            self.biblioteca = JanelaBiblioteca(self.root, self.editar_video)
        self.biblioteca.atualizar()
        tema.trazer_para_frente(self.biblioteca.janela)

    def editar_video(self, caminho):
        """Abre o editor com um vídeo específico (usado pela biblioteca)"""
        self.video_pendente = caminho
        self.abrir_editor()

    def atualizar_biblioteca(self):
        if self.biblioteca and self.biblioteca.janela.winfo_exists():
            self.biblioteca.atualizar()

    def musica_baixada(self, caminho):
        self.progress_label.configure(text="Música pronta! Escolha-a em \"Áudio do corte\" no editor.")
        if self.editor and self.editor.janela.winfo_exists():
            self.editor.painel_audio.atualizar_musicas(caminho)
        self.atualizar_biblioteca()

    # --- Download ---
    def start_download_thread(self, somente_audio=False):
        threading.Thread(target=self.download, args=(somente_audio,), daemon=True).start()

    def mostrar_progresso(self, percent, somente_audio):
        if percent >= 100:
            texto = "Convertendo para MP3…" if somente_audio else "Mesclando áudio e vídeo (quase pronto)…"
        else:
            texto = f"Baixando: {percent}%"
        self.na_tela(self.progress_bar.set, percent / 100)
        self.na_tela(self.progress_label.configure, text=texto)

    def download(self, somente_audio=False):
        url = self.url_entry.get().strip()
        if not url:
            self.na_tela(messagebox.showwarning, "Aviso", "Por favor, cole um link!")
            return

        self.na_tela(self.btn_download.configure, state="disabled")
        self.na_tela(self.btn_audio.configure, state="disabled")
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
                self.na_tela(self.progress_label.configure, text="Tentando de novo em modo seguro (mais lento)…")
                caminho, erro, avisos = baixar(1)
            if erro:
                raise RuntimeError(erro)
            limpar_temporarios(caminho)
            self.na_tela(self.status_label.configure, text="Concluído com sucesso!", text_color=tema.VERDE_TEXTO)
            if any("no longer valid" in aviso for aviso in avisos):
                self.na_tela(self.status_label.configure, text_color=tema.AMARELO,
                             text="Baixou, mas seus cookies não valem mais — exporte de novo antes que o YouTube bloqueie")
            titulo = os.path.splitext(os.path.basename(caminho))[0]
            if somente_audio:
                self.na_tela(self.musica_baixada, caminho)
                self.na_tela(messagebox.showinfo, "Sucesso", f"Música baixada:\n{titulo}")
            else:
                self.video_pendente = caminho
                self.na_tela(self.progress_label.configure, text="Pronto! Clique em Editar vídeo para cortar.")
                self.na_tela(self.atualizar_biblioteca)
        except Exception as e:
            erro = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            self.na_tela(messagebox.showerror, "Erro",
                         f"Ocorreu um problema: {erro}\n\n{ytdlp.dica_do_erro(erro, bool(arquivo_cookies))}")
            self.na_tela(self.status_label.configure, text="Erro no processo", text_color=tema.VERMELHO_TEXTO)
        finally:
            self.na_tela(self.btn_download.configure, state="normal")
            self.na_tela(self.btn_audio.configure, state="normal")
            self.na_tela(self.progress_bar.set, 0)
