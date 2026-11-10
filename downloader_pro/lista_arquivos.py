"""Lista de arquivos escolhidos: numerada, com a duração de cada um, ▲ ▼ para mudar a ordem e ✕ para tirar."""
import os
import threading
import tkinter as tk

import customtkinter as ctk

from . import midia, tema
from .sistema import agendar
from .tempos import tempo_curto


class ListaArquivos(ctk.CTkFrame):
    def __init__(self, pai, vazio, ao_mudar=None):
        """vazio: texto mostrado quando não há nada; ao_mudar(): chamado quando a lista (ou as durações) mudam"""
        super().__init__(pai, fg_color=tema.CAMPO, corner_radius=10)
        self.vazio = vazio
        self.ao_mudar = ao_mudar
        self.arquivos = []         # caminhos, na ordem
        self.rotulos_duracao = []  # um por linha, preenchidos conforme as durações são lidas
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

    # --- Durações ---
    def duracoes(self):
        """Duração (s) de cada arquivo da lista; None para os que ainda estão sendo lidos"""
        return [midia.duracao_em_cache(c) for c in self.arquivos]

    @staticmethod
    def texto_duracao(caminho):
        duracao = midia.duracao_em_cache(caminho)
        return "…" if duracao is None else tempo_curto(duracao)

    def carregar_duracoes(self):
        """Lê, em segundo plano, a duração dos arquivos que ainda não foram lidos"""
        faltando = [c for c in dict.fromkeys(self.arquivos) if midia.duracao_em_cache(c) is None]
        if not faltando:
            return

        def trabalho():
            for caminho in faltando:
                try:
                    midia.duracao_arquivo(caminho)
                except (OSError, ValueError):
                    pass
            agendar(self.winfo_toplevel(), self.atualizar_duracoes)
        threading.Thread(target=trabalho, daemon=True).start()

    def atualizar_duracoes(self):
        for rotulo, caminho in zip(self.rotulos_duracao, self.arquivos):
            rotulo.configure(text=self.texto_duracao(caminho))
        if self.ao_mudar:
            self.ao_mudar()

    # --- Desenho ---
    @staticmethod
    def cortar(texto, limite):
        """Encurta o texto para 'limite' caracteres, terminando com …"""
        return texto if len(texto) <= limite else texto[:max(limite - 1, 1)] + "…"

    def ajustar_nome(self, largura_linha, rotulo, texto):
        # sobra = largura da linha menos os 3 botões, a duração e as folgas; ~7,5 px por caractere na fonte 12
        limite = int((largura_linha - 3 * 30 - 56 - 20) / 7.5)
        if limite >= 8:
            rotulo.configure(text=self.cortar(texto, limite))

    def redesenhar(self, avisar=True):
        for filho in self.winfo_children():
            filho.destroy()
        self.rotulos_duracao = []
        if not self.arquivos:
            tema.rotulo(self, self.vazio, 12, suave=True).pack(pady=14)
        for i, caminho in enumerate(self.arquivos):
            linha = ctk.CTkFrame(self, fg_color="transparent")
            linha.pack(fill=tk.X, pady=1, padx=2)
            # Os botões e a duração entram primeiro (à direita) para nunca serem empurrados para fora pelo nome:
            # o nome tem largura mínima pequena e ocupa só o espaço que sobrar
            tema.botao_pequeno(linha, "✕", lambda i=i: self.remover(i), 26, cor_texto=tema.VERMELHO_TEXTO).pack(
                side=tk.RIGHT)
            tema.botao_pequeno(linha, "▼", lambda i=i: self.mover(i, 1), 26).pack(side=tk.RIGHT)
            tema.botao_pequeno(linha, "▲", lambda i=i: self.mover(i, -1), 26).pack(side=tk.RIGHT)
            duracao = tema.rotulo(linha, self.texto_duracao(caminho), 12, suave=True, width=52, anchor="e")
            duracao.pack(side=tk.RIGHT)
            self.rotulos_duracao.append(duracao)
            texto = f"{i + 1}.  {os.path.basename(caminho)}"
            nome = tema.rotulo(linha, self.cortar(texto, 30), 12, anchor="w", width=10)
            nome.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
            # Quando a linha ganha sua largura real, o nome é encurtado (com "…") para caber ao lado dos botões
            linha.bind("<Configure>", lambda e, nome=nome, texto=texto: self.ajustar_nome(e.width, nome, texto))
        self.carregar_duracoes()
        if avisar and self.ao_mudar:
            self.ao_mudar()
