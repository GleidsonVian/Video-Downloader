"""Janela do editor: escolher o vídeo, marcar cortes (player), definir o áudio e gerar."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import cortes, juncao, tema
from .arquivos import abrir_pasta
from .config import EXT_VIDEO, PASTA_CORTES, PASTA_SCRIPT, PASTA_VIDEOS
from .lista_cortes import ListaCortes
from .painel_audio import PainelAudio
from .painel_montagem import PainelMontagem
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

        self.janela = ctk.CTkToplevel(janela_pai, fg_color=tema.FUNDO)
        self.janela.title("Editar vídeo — cortes e música")
        self.janela.geometry("1080x700")
        self.janela.minsize(960, 660)
        tema.aplicar_icone(self.janela)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        self.criar_widgets()
        if video:
            self.selecionar_video(video)
        # A detecção testa o ffmpeg de verdade; roda em segundo plano para a janela abrir sem demora
        threading.Thread(target=self.detectar_placa, daemon=True).start()

    def criar_widgets(self):
        j = self.janela
        j.columnconfigure(0, weight=3)
        j.columnconfigure(1, weight=2)
        j.rowconfigure(0, weight=1)
        esquerda = ctk.CTkFrame(j, fg_color="transparent")
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=(16, 8))
        direita = ctk.CTkFrame(j, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=(16, 8))

        # --- Esquerda: vídeo e cortes ---
        quadro_video = tema.cartao(esquerda, "Vídeo")
        quadro_video.pack(fill=tk.X)
        self.video_label = tema.rotulo(quadro_video, "Nenhum vídeo selecionado", 13, True, suave=True,
                                       wraplength=520, justify="left", anchor="w")
        self.video_label.pack(fill=tk.X, padx=16, pady=(6, 0))
        botoes = ctk.CTkFrame(quadro_video, fg_color="transparent")
        botoes.pack(fill=tk.X, padx=16, pady=(10, 14))
        self.btn_assistir = tema.botao(botoes, "▶  Assistir e marcar cortes", tema.AZUL, self.abrir_player,
                                       state="disabled")
        self.btn_assistir.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tema.botao(botoes, "Escolher vídeo do PC…", tema.CINZA, self.escolher_video).pack(side=tk.LEFT, padx=(8, 0))

        quadro_cortes = tema.cartao(esquerda, "Cortes")
        quadro_cortes.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.lista = ListaCortes(quadro_cortes, nomes_existentes=self.nomes_gravados, altura=300)
        self.lista.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 12))

        # --- Direita: saída, montagem e áudio ---
        quadro_saida = tema.cartao(direita, "Saída")
        quadro_saida.pack(fill=tk.X)
        self.whatsapp_var = tk.BooleanVar(value=True)
        self.volume_var = tk.BooleanVar(value=True)
        # Desligada por padrão: o ganho é pequeno com o equilíbrio de volume ligado e o arquivo sai maior
        self.gpu_var = tk.BooleanVar(value=False)
        tema.chave(quadro_saida, "Caber no WhatsApp (até 180 MB)", self.whatsapp_var).pack(anchor="w", padx=16, pady=(8, 0))
        tema.chave(quadro_saida, "Equilibrar volume do áudio", self.volume_var).pack(anchor="w", padx=16, pady=(8, 0))
        self.check_gpu = tema.chave(quadro_saida, "Usar placa de vídeo (mais rápido)", self.gpu_var)
        self.check_gpu.pack(anchor="w", padx=16, pady=(8, 14))

        embaixo = ctk.CTkFrame(self.janela, fg_color="transparent")
        self.btn_corte = tema.botao(embaixo, "GERAR CORTES", tema.AZUL, self.start_corte_thread, altura=50,
                                    state="disabled")
        self.painel_montagem = PainelMontagem(
            direita, ao_mudar=lambda juntar: self.btn_corte.configure(
                text="GERAR VÍDEO MONTADO" if juntar else "GERAR CORTES"))
        self.painel_montagem.pack(fill=tk.X, pady=(12, 0))
        self.painel_audio = PainelAudio(direita)
        self.painel_audio.pack(fill=tk.X, pady=(12, 0))

        # --- Embaixo: gerar e andamento ---
        embaixo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        self.btn_corte.grid(row=0, column=0, sticky="ew")
        embaixo.columnconfigure(0, weight=1)
        self.corte_label = tema.rotulo(embaixo, "", 12, suave=True)
        self.corte_label.grid(row=1, column=0, pady=(8, 0))
        self.corte_bar = tema.barra_progresso(embaixo)
        self.corte_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def na_tela(self, funcao, *args, **kwargs):
        agendar(self.janela, funcao, *args, **kwargs)

    def detectar_placa(self):
        if not cortes.placa_amd_disponivel():
            self.na_tela(self.gpu_var.set, False)
            self.na_tela(self.check_gpu.configure, state="disabled", text="Placa de vídeo AMD não detectada")

    # --- Vídeo e player ---
    def selecionar_video(self, caminho):
        self.video_atual = caminho
        self.video_label.configure(text=os.path.basename(caminho), text_color=tema.TEXTO)
        self.btn_corte.configure(state="normal")
        self.btn_assistir.configure(state="normal")

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

    def pasta_da_aula(self, criar=True):
        pasta = os.path.join(PASTA_CORTES, os.path.splitext(os.path.basename(self.video_atual))[0])
        if criar:
            os.makedirs(pasta, exist_ok=True)
        return pasta

    def nomes_gravados(self):
        """Nomes (sem extensão) dos cortes já gravados desta aula, para o nome padrão não repetir"""
        if not self.video_atual:
            return []
        try:
            return [os.path.splitext(nome)[0] for nome in os.listdir(self.pasta_da_aula(criar=False))]
        except OSError:
            return []

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
        montagem = self.painel_montagem.opcoes()
        if montagem and len(lista) > 1:
            alvo, argumentos = self.fazer_montagem, (lista, opcoes, montagem)
        else:  # com um corte só, "juntar" não muda nada: sai como corte comum
            alvo, argumentos = self.fazer_cortes, (lista, opcoes)
        threading.Thread(target=alvo, args=argumentos, daemon=True).start()

    @staticmethod
    def com_plano_b(gerar, usar_gpu):
        """Roda gerar(); se a placa de vídeo falhar, refaz pelo processador (mais lento, mas funciona)"""
        try:
            gerar()
        except RuntimeError:
            if not usar_gpu:
                raise
            gerar(usar_gpu=False)

    def mostrar_andamento(self, texto, fracao):
        self.na_tela(self.corte_bar.set, fracao)
        self.na_tela(self.corte_label.configure, text=texto, text_color=tema.TEXTO)

    def terminar(self, texto=None, erro=False):
        if texto:
            self.na_tela(self.corte_label.configure, text=texto,
                         text_color=tema.VERMELHO_TEXTO if erro else tema.VERDE_TEXTO)
        self.na_tela(self.btn_corte.configure, state="normal")
        self.na_tela(self.corte_bar.set, 0)

    def fazer_montagem(self, lista, opcoes, montagem):
        """Junta todos os cortes da lista, na ordem dela, num vídeo só"""
        video, pasta = self.video_atual, self.pasta_da_aula()
        caminho = os.path.join(pasta, montagem["nome"] + ".mp4")
        trechos = [(inicio, fim) for inicio, fim, _ in lista]
        self.na_tela(self.btn_corte.configure, state="disabled")
        try:
            gerar = lambda **extra: juncao.juntar_cortes(
                video, trechos, caminho, montagem["transicao"], ao_iniciar=self.registrar_processo,
                ao_progresso=lambda f: self.mostrar_andamento(
                    f"Montando {montagem['nome']} ({len(trechos)} cortes) — {f * 100:.0f}%", f),
                **{**opcoes, **extra})
            self.com_plano_b(gerar, opcoes["usar_gpu"])
            self.terminar(f"✓ {montagem['nome']}.mp4 gerado em Cortes\\{os.path.basename(pasta)}")
            self.na_tela(abrir_pasta, pasta)
        except Exception as e:
            self.terminar("Erro ao montar o vídeo", erro=True)
            self.na_tela(messagebox.showerror, "Erro", str(e), parent=self.janela)

    def fazer_cortes(self, lista, opcoes):
        video, pasta = self.video_atual, self.pasta_da_aula()
        self.na_tela(self.btn_corte.configure, state="disabled")
        gerados, usados = [], set()
        try:
            for i, (inicio, fim, nome) in enumerate(lista):
                nome = nome or f"corte {formatar_tempo(inicio)} a {formatar_tempo(fim)}"
                # Dois cortes com o mesmo nome na lista: numera o segundo
                final, n = nome, 2
                while final.lower() in usados:
                    final, n = f"{nome} ({n})", n + 1
                usados.add(final.lower())

                caminho = os.path.join(pasta, final + ".mp4")
                gerar = lambda **extra: cortes.gerar_corte(
                    video, inicio, fim, caminho, ao_iniciar=self.registrar_processo,
                    ao_progresso=lambda f, i=i, final=final: self.mostrar_andamento(
                        f"Corte {i + 1} de {len(lista)} — {final} ({f * 100:.0f}%)", (i + f) / len(lista)),
                    **{**opcoes, **extra})
                self.com_plano_b(gerar, opcoes["usar_gpu"])
                gerados.append(final)

            self.terminar(f"✓ {len(gerados)} corte(s) gerado(s) em Cortes\\{os.path.basename(pasta)}")
            self.na_tela(abrir_pasta, pasta)
        except Exception as e:
            self.terminar(f"Erro no corte {len(gerados) + 1} — {len(gerados)} gerado(s) antes do erro", erro=True)
            self.na_tela(messagebox.showerror, "Erro", str(e), parent=self.janela)

    def fechar(self):
        if self.processo_corte and self.processo_corte.poll() is None:
            if not messagebox.askyesno("Cortes em andamento",
                                       "Ainda há cortes sendo gerados. Fechar e cancelar?", parent=self.janela):
                return
            encerrar_processo(self.processo_corte)
        if self.player and self.player.janela.winfo_exists():
            self.player.fechar()
        self.janela.destroy()
