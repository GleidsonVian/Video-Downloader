"""Painel "Áudio do corte": áudio original, música de fundo (mistura) ou só a música."""
import os
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import tema
from .arquivos import listar_musicas
from .config import EXT_AUDIO, PASTA_MUSICAS, PASTA_SCRIPT
from .tempos import para_segundos

MODOS = {"Original": "original", "Música de fundo": "mistura", "Trocar pela música": "musica"}
SEM_MUSICA = "(nenhuma música baixada)"


class PainelAudio(ctk.CTkFrame):
    def __init__(self, pai):
        super().__init__(pai, fg_color=tema.CARTAO, corner_radius=14, border_width=1, border_color=tema.BORDA)
        self.musicas = {}  # nome mostrado -> caminho do arquivo
        # Cada modo lembra o próprio volume: a música ao fundo pede baixinho, no lugar do áudio pede alto
        self.volumes = {"mistura": 30, "musica": 100}
        self.modo_anterior = "original"
        self.modo = tk.StringVar(value="original")

        tema.rotulo(self, "ÁUDIO DO CORTE", 11, True, suave=True).pack(anchor="w", padx=16, pady=(12, 0))
        self.seletor = ctk.CTkSegmentedButton(
            self, values=list(MODOS), command=self.escolheu_modo, height=34, corner_radius=8,
            fg_color=tema.CAMPO, selected_color=tema.AZUL[0], selected_hover_color=tema.AZUL[1],
            unselected_color=tema.CAMPO, unselected_hover_color=tema.CINZA[0], font=tema.fonte(12, True))
        self.seletor.set("Original")
        self.seletor.pack(fill=tk.X, padx=16, pady=(8, 0))

        self.opcoes_musica = ctk.CTkFrame(self, fg_color="transparent")
        self.opcoes_musica.pack(fill=tk.X, padx=16, pady=(8, 12))
        linha1 = ctk.CTkFrame(self.opcoes_musica, fg_color="transparent")
        linha1.pack(fill=tk.X)
        self.musica = tk.StringVar()
        self.menu_musica = tema.menu(linha1, [SEM_MUSICA], self.musica, largura=250)
        self.menu_musica.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_procurar = tema.botao(linha1, "…", tema.CINZA, self.escolher, altura=34, width=40)
        self.btn_procurar.pack(side=tk.LEFT, padx=(6, 0))

        linha2 = ctk.CTkFrame(self.opcoes_musica, fg_color="transparent")
        linha2.pack(fill=tk.X, pady=(8, 0))
        tema.rotulo(linha2, "Começar em", 12, suave=True).pack(side=tk.LEFT)
        self.inicio = tema.campo(linha2, width=64, justify="center")
        self.inicio.insert(0, "00:00")
        self.inicio.pack(side=tk.LEFT, padx=(6, 14))
        tema.rotulo(linha2, "Volume", 12, suave=True).pack(side=tk.LEFT)
        self.volume = ctk.CTkSlider(linha2, from_=5, to=100, number_of_steps=19, width=120, command=self.mostrar_volume,
                                    progress_color=tema.AZUL[0], button_color=tema.TEXTO,
                                    button_hover_color=tema.TEXTO)
        self.volume.set(30)
        self.volume.pack(side=tk.LEFT, padx=8)
        self.volume_label = tema.rotulo(linha2, "30%", 12, True, width=40, anchor="w")
        self.volume_label.pack(side=tk.LEFT)

        self.atualizar_musicas()
        self.atualizar_opcoes()

    def mostrar_volume(self, valor):
        self.volume_label.configure(text=f"{int(round(valor))}%")

    def escolheu_modo(self, nome):
        self.modo.set(MODOS[nome])
        self.atualizar_opcoes()

    def atualizar_musicas(self, selecionar=None):
        """Lê a pasta Músicas/ e preenche a lista; 'selecionar' escolhe uma música (ex: a que acabou de baixar)"""
        if selecionar and os.path.dirname(os.path.abspath(selecionar)) != PASTA_MUSICAS:
            self.musicas[os.path.basename(selecionar)] = selecionar  # música de outra pasta
        self.musicas.update(listar_musicas())
        self.musicas = {n: c for n, c in self.musicas.items() if os.path.exists(c)}
        self.menu_musica.configure(values=list(self.musicas) or [SEM_MUSICA])
        if selecionar:
            self.musica.set(os.path.basename(selecionar))
        elif self.musica.get() not in self.musicas:
            self.musica.set(next(iter(self.musicas), SEM_MUSICA))

    def escolher(self):
        caminho = filedialog.askopenfilename(
            title="Escolha a música", initialdir=PASTA_MUSICAS if os.path.isdir(PASTA_MUSICAS) else PASTA_SCRIPT,
            filetypes=[("Áudio", " ".join("*" + e for e in EXT_AUDIO)), ("Todos os arquivos", "*.*")])
        if caminho:
            self.atualizar_musicas(selecionar=os.path.normpath(caminho))

    def atualizar_opcoes(self):
        """Libera as opções da música só quando o modo precisa dela e troca para o volume daquele modo"""
        modo = self.modo.get()
        if self.modo_anterior in self.volumes:
            self.volumes[self.modo_anterior] = self.volume.get()
        if modo in self.volumes:
            self.volume.set(self.volumes[modo])
            self.mostrar_volume(self.volumes[modo])
        self.modo_anterior = modo
        estado = "normal" if modo != "original" else "disabled"
        for widget in (self.menu_musica, self.btn_procurar, self.inicio, self.volume):
            widget.configure(state=estado)

    def opcoes(self):
        """Opções para gerar_corte(): dict com modo_audio (e a música, se for usada).

        Levanta ValueError com a mensagem a mostrar ao usuário, se algo estiver faltando.
        """
        opcoes = {"modo_audio": self.modo.get()}
        if opcoes["modo_audio"] == "original":
            return opcoes
        if self.musica.get() not in self.musicas:
            raise ValueError("Escolha uma música em \"Áudio do corte\", "
                             "ou baixe uma com o botão ♪ Só áudio (MP3).")
        try:
            inicio = para_segundos(self.inicio.get() or "0")
        except ValueError:
            raise ValueError("\"Começar em\" da música deve ser minutos:segundos (ex: 00:45).") from None
        opcoes.update(musica=self.musicas[self.musica.get()], volume_musica=int(round(self.volume.get())),
                      inicio_musica=inicio)
        return opcoes
