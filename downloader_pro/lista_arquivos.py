"""Lista de arquivos escolhidos, numerada, com ▲ ▼ para mudar a ordem e ✕ para tirar."""
import os
import tkinter as tk

import customtkinter as ctk

from . import tema


class ListaArquivos(ctk.CTkFrame):
    def __init__(self, pai, vazio, ao_mudar=None):
        """vazio: texto mostrado quando não há nada; ao_mudar(): chamado quando a lista muda"""
        super().__init__(pai, fg_color=tema.CAMPO, corner_radius=10)
        self.vazio = vazio
        self.ao_mudar = ao_mudar
        self.arquivos = []  # caminhos, na ordem
        self.redesenhar(avisar=False)

    def adicionar(self, caminhos):
        self.arquivos += caminhos
        self.redesenhar()

    def mover(self, indice, direcao):
        destino = indice + direcao
        if 0 <= destino < len(self.arquivos):
            self.arquivos[indice], self.arquivos[destino] = self.arquivos[destino], self.arquivos[indice]
            self.redesenhar()

    def remover(self, indice):
        del self.arquivos[indice]
        self.redesenhar()

    def redesenhar(self, avisar=True):
        for filho in self.winfo_children():
            filho.destroy()
        if not self.arquivos:
            tema.rotulo(self, self.vazio, 12, suave=True).pack(pady=14)
        for i, caminho in enumerate(self.arquivos):
            linha = ctk.CTkFrame(self, fg_color="transparent")
            linha.pack(fill=tk.X, pady=1, padx=2)
            tema.rotulo(linha, f"{i + 1}.  {os.path.basename(caminho)}", 12, anchor="w").pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
            tema.botao_pequeno(linha, "▲", lambda i=i: self.mover(i, -1), 26).pack(side=tk.LEFT)
            tema.botao_pequeno(linha, "▼", lambda i=i: self.mover(i, 1), 26).pack(side=tk.LEFT)
            tema.botao_pequeno(linha, "✕", lambda i=i: self.remover(i), 26, cor_texto=tema.VERMELHO_TEXTO).pack(
                side=tk.LEFT)
        if avisar and self.ao_mudar:
            self.ao_mudar()
