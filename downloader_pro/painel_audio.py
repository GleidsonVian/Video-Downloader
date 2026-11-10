"""Painel "Áudio do corte": áudio original, música de fundo (mistura) ou só a música (uma ou várias)."""
import os
import tkinter as tk

import customtkinter as ctk

from . import tema
from .lista_arquivos import ListaArquivos
from .seletor import SeletorMusicas
from .tempos import para_segundos

MODOS = {"Original": "original", "Música de fundo": "mistura", "Trocar pela música": "musica"}


class PainelAudio(ctk.CTkFrame):
    def __init__(self, pai):
        super().__init__(pai, fg_color=tema.CARTAO, corner_radius=14, border_width=1, border_color=tema.BORDA)
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
        topo = ctk.CTkFrame(self.opcoes_musica, fg_color="transparent")
        topo.pack(fill=tk.X)
        self.btn_adicionar = tema.botao(topo, "+ Adicionar músicas…", tema.CINZA, self.escolher, altura=32)
        self.btn_adicionar.pack(side=tk.LEFT)
        self.resumo = tema.rotulo(topo, "", 12, suave=True)
        self.resumo.pack(side=tk.LEFT, padx=10)
        self.lista = ListaArquivos(self.opcoes_musica, "Nenhuma música. Clique em \"+ Adicionar músicas…\".",
                                   self.atualizar_resumo)
        self.lista.pack(fill=tk.X, pady=(6, 0))
        self.atualizar_resumo()

        linha = ctk.CTkFrame(self.opcoes_musica, fg_color="transparent")
        linha.pack(fill=tk.X, pady=(8, 0))
        tema.rotulo(linha, "1ª música começa em", 12, suave=True).pack(side=tk.LEFT)
        self.inicio = tema.campo(linha, width=60, justify="center")
        self.inicio.insert(0, "00:00")
        self.inicio.pack(side=tk.LEFT, padx=(6, 12))
        tema.rotulo(linha, "Volume", 12, suave=True).pack(side=tk.LEFT)
        self.volume = ctk.CTkSlider(linha, from_=5, to=100, number_of_steps=19, width=90, command=self.mostrar_volume,
                                    progress_color=tema.AZUL[0], button_color=tema.TEXTO,
                                    button_hover_color=tema.TEXTO)
        self.volume.set(30)
        self.volume.pack(side=tk.LEFT, padx=8)
        self.volume_label = tema.rotulo(linha, "30%", 12, True, width=40, anchor="w")
        self.volume_label.pack(side=tk.LEFT)
        self.atualizar_opcoes()

    def mostrar_volume(self, valor):
        self.volume_label.configure(text=f"{int(round(valor))}%")

    def escolheu_modo(self, nome):
        self.modo.set(MODOS[nome])
        self.atualizar_opcoes()

    # --- Lista de músicas ---
    def escolher(self):
        janela = SeletorMusicas(self.winfo_toplevel(), self.lista.adicionar)
        janela.janela.after(150, janela.janela.focus_force)

    def atualizar_musicas(self, adicionar=None):
        """Chamado quando uma música acaba de ser baixada: entra no fim da lista"""
        if adicionar and adicionar not in self.lista.arquivos:
            self.lista.adicionar([adicionar])

    def atualizar_resumo(self):
        n = len(self.lista.arquivos)
        self.resumo.configure(text=f"{n} músicas em sequência" if n > 1 else ("1 música (repete)" if n else ""))

    # --- Modo ---
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
        for widget in (self.btn_adicionar, self.inicio, self.volume):
            widget.configure(state=estado)

    def opcoes(self):
        """Opções para gerar_corte(): dict com modo_audio (e as músicas, se forem usadas).

        Levanta ValueError com a mensagem a mostrar ao usuário, se algo estiver faltando.
        """
        opcoes = {"modo_audio": self.modo.get()}
        if opcoes["modo_audio"] == "original":
            return opcoes
        if not self.lista.arquivos:
            raise ValueError("Escolha pelo menos uma música em \"Áudio do corte\", "
                             "ou baixe uma com o botão ♪ Só áudio (MP3).")
        faltando = [os.path.basename(c) for c in self.lista.arquivos if not os.path.exists(c)]
        if faltando:
            raise ValueError("Estas músicas não existem mais:\n" + "\n".join(faltando))
        try:
            inicio = para_segundos(self.inicio.get() or "0")
        except ValueError:
            raise ValueError("\"Começar em\" da música deve ser minutos:segundos (ex: 00:45).") from None
        opcoes.update(musica=list(self.lista.arquivos), volume_musica=int(round(self.volume.get())),
                      inicio_musica=inicio)
        return opcoes
