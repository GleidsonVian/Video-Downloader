"""Janela do editor: escolher o vídeo, marcar cortes (player), definir o áudio e gerar."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import cortes
from .arquivos import abrir_pasta
from .config import EXT_VIDEO, ICONE, PASTA_CORTES, PASTA_SCRIPT, PASTA_VIDEOS
from .lista_cortes import ListaCortes
from .painel_audio import PainelAudio
from .player import PlayerCortes, carregar_vlc
from .sistema import agendar, encerrar_processo
from .tempos import formatar_tempo


class JanelaEditor:
    def __init__(self, janela_pai, ao_iniciar_processo, video=None):
        """ao_iniciar_processo(processo): avisa a janela principal do ffmpeg em andamento (para encerrar ao fechar)"""
        self.ao_iniciar_processo = ao_iniciar_processo
        self.video_atual = None
        self.player = None
        self.processo_corte = None

        self.janela = tk.Toplevel(janela_pai)
        self.janela.title("Editar vídeo — cortes e música")
        self.janela.geometry("580x720")
        self.janela.configure(padx=20, pady=15)
        if os.path.exists(ICONE):
            self.janela.iconbitmap(ICONE)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        self.criar_widgets()
        if video:
            self.selecionar_video(video)
        # A detecção testa o ffmpeg de verdade; roda em segundo plano para a janela abrir sem demora
        threading.Thread(target=self.detectar_placa, daemon=True).start()

    def criar_widgets(self):
        j = self.janela
        tk.Label(j, text="Vídeo", font=("Arial", 10, "bold")).pack()
        self.video_label = tk.Label(j, text="Nenhum vídeo selecionado", font=("Arial", 8), fg="gray", wraplength=520)
        self.video_label.pack(pady=(4, 2))
        botoes = tk.Frame(j)
        botoes.pack()
        self.btn_assistir = tk.Button(botoes, text="▶ ASSISTIR E MARCAR CORTES", command=self.abrir_player,
                                      state="disabled", bg="#2b6cc4", fg="white", font=("Arial", 9, "bold"))
        self.btn_assistir.pack(side=tk.LEFT, padx=4)
        tk.Button(botoes, text="Escolher vídeo do PC...", command=self.escolher_video).pack(side=tk.LEFT, padx=4)

        ttk.Separator(j, orient="horizontal").pack(fill=tk.X, pady=10)
        tk.Label(j, text="Cortes", font=("Arial", 10, "bold")).pack()
        self.lista = ListaCortes(j)
        self.lista.pack(fill=tk.X)

        # Opções em grade (2 por linha) para nada ficar cortado
        opcoes = tk.Frame(j)
        opcoes.pack(fill=tk.X, pady=(4, 0))
        self.whatsapp_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opcoes, text="Caber no WhatsApp (até 180 MB)",
                       variable=self.whatsapp_var).grid(row=0, column=0, sticky="w", padx=8)
        self.volume_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opcoes, text="Equilibrar volume do áudio",
                       variable=self.volume_var).grid(row=0, column=1, sticky="w", padx=8)
        # Desligada por padrão: o ganho é pequeno com o equilíbrio de volume ligado e o arquivo sai maior
        self.gpu_var = tk.BooleanVar(value=False)
        self.check_gpu = tk.Checkbutton(opcoes, text="Usar placa de vídeo (mais rápido)", variable=self.gpu_var)
        self.check_gpu.grid(row=1, column=0, columnspan=2, sticky="w", padx=8)

        self.painel_audio = PainelAudio(j)
        self.painel_audio.pack(fill=tk.X, pady=(8, 0))

        self.btn_corte = tk.Button(j, text="GERAR CORTES", command=self.start_corte_thread, state="disabled",
                                   bg="#2b6cc4", fg="white", font=("Arial", 10, "bold"), height=2)
        self.btn_corte.pack(pady=6, fill=tk.X)
        self.corte_label = tk.Label(j, text="", font=("Arial", 8), wraplength=520)
        self.corte_label.pack()
        self.corte_bar = ttk.Progressbar(j, orient="horizontal", length=400, mode="determinate")
        self.corte_bar.pack(pady=5)

    def na_tela(self, funcao, *args, **kwargs):
        agendar(self.janela, funcao, *args, **kwargs)

    def detectar_placa(self):
        if not cortes.placa_amd_disponivel():
            self.na_tela(self.gpu_var.set, False)
            self.na_tela(self.check_gpu.config, state="disabled", text="Placa de vídeo AMD não detectada")

    # --- Vídeo e player ---
    def selecionar_video(self, caminho):
        self.video_atual = caminho
        self.video_label.config(text=f"Vídeo: {os.path.basename(caminho)}", fg="black")
        self.btn_corte.config(state="normal")
        self.btn_assistir.config(state="normal")

    def escolher_video(self):
        caminho = filedialog.askopenfilename(
            parent=self.janela, title="Escolha o vídeo para cortar",
            initialdir=PASTA_VIDEOS if os.path.isdir(PASTA_VIDEOS) else PASTA_SCRIPT,
            filetypes=[("Vídeos", " ".join("*" + e for e in EXT_VIDEO)), ("Todos os arquivos", "*.*")])
        if caminho:
            self.selecionar_video(os.path.normpath(caminho))

    def abrir_player(self):
        vlc = carregar_vlc()
        if vlc is None:
            messagebox.showerror("VLC não encontrado",
                                 "Para assistir e marcar os cortes, instale o VLC de 64 bits:\n\n"
                                 "winget install VideoLAN.VLC\n\nou baixe em videolan.org", parent=self.janela)
            return
        if self.player and self.player.janela.winfo_exists():  # só um player por vez
            self.player.fechar()
        self.player = PlayerCortes(self.janela, self.video_atual, vlc, self.lista)

    # --- Cortes ---
    def registrar_processo(self, processo):
        self.processo_corte = processo
        self.ao_iniciar_processo(processo)

    def start_corte_thread(self):
        lista, erros = self.lista.ler_cortes()
        if erros:
            messagebox.showwarning("Aviso", "Corrija os cortes:\n\n" + "\n".join(erros), parent=self.janela)
            return
        if not lista:
            messagebox.showwarning("Aviso", "Preencha pelo menos um corte (início e fim), ex: 15:05 e 16:20",
                                   parent=self.janela)
            return
        try:
            audio = self.painel_audio.opcoes()
        except ValueError as e:
            messagebox.showwarning("Aviso", str(e), parent=self.janela)
            return
        opcoes = dict(limitar_whatsapp=self.whatsapp_var.get(), equilibrar_volume=self.volume_var.get(),
                      usar_gpu=self.gpu_var.get(), **audio)
        threading.Thread(target=self.fazer_cortes, args=(lista, opcoes), daemon=True).start()

    def fazer_cortes(self, lista, opcoes):
        video = self.video_atual
        pasta = os.path.join(PASTA_CORTES, os.path.splitext(os.path.basename(video))[0])
        os.makedirs(pasta, exist_ok=True)

        self.na_tela(self.btn_corte.config, state="disabled")
        gerados, usados = [], set()
        try:
            for i, (inicio, fim, nome) in enumerate(lista):
                nome = nome or f"corte {formatar_tempo(inicio)} a {formatar_tempo(fim)}"
                # Dois cortes com o mesmo nome na lista: numera o segundo
                final, n = nome, 2
                while final.lower() in usados:
                    final, n = f"{nome} ({n})", n + 1
                usados.add(final.lower())

                def progresso(fracao, i=i, final=final):
                    self.na_tela(self.corte_bar.config, value=(i + fracao) / len(lista) * 100)
                    self.na_tela(self.corte_label.config, fg="black",
                                 text=f"Corte {i + 1} de {len(lista)} — {final} ({fracao * 100:.0f}%)")

                caminho = os.path.join(pasta, final + ".mp4")
                gerar = lambda **extra: cortes.gerar_corte(
                    video, inicio, fim, caminho, ao_progresso=progresso,
                    ao_iniciar=self.registrar_processo, **{**opcoes, **extra})
                try:
                    gerar()
                except RuntimeError:
                    if not opcoes["usar_gpu"]:
                        raise
                    gerar(usar_gpu=False)  # a placa falhou neste corte: refaz pelo processador
                gerados.append(final)

            self.na_tela(self.corte_label.config, fg="green",
                         text=f"✓ {len(gerados)} corte(s) gerado(s) em Cortes\\{os.path.basename(pasta)}")
            self.na_tela(abrir_pasta, pasta)
        except Exception as e:
            self.na_tela(self.corte_label.config, fg="red",
                         text=f"Erro no corte {len(gerados) + 1} — {len(gerados)} gerado(s) antes do erro")
            self.na_tela(messagebox.showerror, "Erro", str(e), parent=self.janela)
        finally:
            self.na_tela(self.btn_corte.config, state="normal")
            self.na_tela(self.corte_bar.config, value=0)

    def fechar(self):
        if self.processo_corte and self.processo_corte.poll() is None:
            if not messagebox.askyesno("Cortes em andamento",
                                       "Ainda há cortes sendo gerados. Fechar e cancelar?", parent=self.janela):
                return
            encerrar_processo(self.processo_corte)
        if self.player and self.player.janela.winfo_exists():
            self.player.fechar()
        self.janela.destroy()
