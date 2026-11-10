"""Janelas para escolher arquivos já existentes (cortes gerados ou músicas) marcando caixinhas."""
import os
import time
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import tema
from .arquivos import formatar_tamanho
from .biblioteca import listar, listar_aulas
from .config import EXT_AUDIO, EXT_VIDEO, PASTA_CORTES, PASTA_MUSICAS, PASTA_SCRIPT


class SeletorArquivos:
    """Lista de arquivos agrupados, com caixinhas. Entrega os marcados a ao_escolher(caminhos)."""

    def __init__(self, janela_pai, ao_escolher, titulo, dica, grupos, vazio, tipos, pasta_inicial,
                 rotulo_outro="Outro arquivo do PC…"):
        """grupos: [(nome do grupo, [(caminho, tamanho, data)])]; tipos: filtros do 'Outro arquivo…'"""
        self.ao_escolher = ao_escolher
        self.tipos = tipos
        self.pasta_inicial = pasta_inicial
        self.itens = []  # [(variável marcada, caminho)]
        self.janela = ctk.CTkToplevel(janela_pai, fg_color=tema.FUNDO)
        self.janela.title(titulo)
        self.janela.geometry("660x640")
        self.janela.minsize(520, 460)
        self.janela.transient(janela_pai)
        tema.aplicar_icone(self.janela)

        tema.rotulo(self.janela, titulo, 16, True).pack(anchor="w", padx=20, pady=(16, 0))
        tema.rotulo(self.janela, dica, 12, suave=True).pack(anchor="w", padx=20)
        self.quadro = ctk.CTkScrollableFrame(self.janela, fg_color=tema.CARTAO, corner_radius=14, border_width=1,
                                             border_color=tema.BORDA)
        self.quadro.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        botoes = ctk.CTkFrame(self.janela, fg_color="transparent")
        botoes.pack(fill=tk.X, padx=16, pady=(0, 14))
        tema.botao(botoes, rotulo_outro, tema.CINZA, self.outro_arquivo, altura=40).pack(side=tk.LEFT)
        tema.botao(botoes, "Cancelar", tema.CINZA, self.janela.destroy, altura=40).pack(side=tk.RIGHT)
        self.btn_adicionar = tema.botao(botoes, "Adicionar", tema.AZUL, self.adicionar, altura=40)
        self.btn_adicionar.pack(side=tk.RIGHT, padx=(0, 8))
        self.preencher(grupos, vazio)
        self.atualizar_contagem()

    def preencher(self, grupos, vazio):
        grupos = [(nome, arquivos) for nome, arquivos in grupos if arquivos]
        if not grupos:
            tema.rotulo(self.quadro, vazio, 13, suave=True, justify="left").pack(padx=16, pady=20)
            return
        for nome, arquivos in grupos:
            titulo = ctk.CTkFrame(self.quadro, fg_color="transparent")
            titulo.pack(fill=tk.X, padx=8, pady=(12, 2))
            tema.rotulo(titulo, nome, 13, True, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
            variaveis = []
            tema.botao_pequeno(titulo, "marcar todos", lambda v=variaveis: self.marcar_todos(v), 90,
                               tema.SUAVE).pack(side=tk.RIGHT)
            for caminho, tamanho, data in sorted(arquivos, key=lambda a: os.path.basename(a[0]).lower()):
                variavel = tk.BooleanVar(value=False)
                variaveis.append(variavel)
                self.itens.append((variavel, caminho))
                hora = time.strftime("%d/%m %H:%M", time.localtime(data))
                ctk.CTkCheckBox(self.quadro, text=f"{os.path.basename(caminho)}    {formatar_tamanho(tamanho)} · {hora}",
                                variable=variavel, command=self.atualizar_contagem, font=tema.fonte(12),
                                text_color=tema.TEXTO, fg_color=tema.AZUL[0], hover_color=tema.AZUL[1],
                                border_color=tema.BORDA).pack(anchor="w", padx=18, pady=4)

    def marcar_todos(self, variaveis):
        marcar = not all(v.get() for v in variaveis)
        for variavel in variaveis:
            variavel.set(marcar)
        self.atualizar_contagem()

    def marcados(self):
        return [caminho for variavel, caminho in self.itens if variavel.get()]

    def atualizar_contagem(self):
        n = len(self.marcados())
        self.btn_adicionar.configure(text=f"Adicionar ({n})" if n else "Adicionar",
                                     state="normal" if n else "disabled")

    def adicionar(self):
        self.ao_escolher(self.marcados())
        self.janela.destroy()

    def outro_arquivo(self):
        caminhos = filedialog.askopenfilenames(
            parent=self.janela, title="Escolha os arquivos", filetypes=self.tipos,
            initialdir=self.pasta_inicial if os.path.isdir(self.pasta_inicial) else PASTA_SCRIPT)
        if caminhos:
            self.ao_escolher([os.path.normpath(c) for c in caminhos])
            self.janela.destroy()


class SeletorCortes(SeletorArquivos):
    """Escolher cortes já gerados (agrupados por aula) para a montagem"""

    def __init__(self, janela_pai, ao_escolher):
        super().__init__(
            janela_pai, ao_escolher, "Escolher cortes para a montagem", "A ordem na montagem você ajusta depois, com ▲ ▼.",
            [(os.path.basename(pasta), arquivos) for pasta, arquivos in listar_aulas(PASTA_CORTES)],
            "Você ainda não gerou nenhum corte.\nUse \"Outro vídeo do PC…\" para escolher arquivos de qualquer pasta.",
            [("Vídeos", " ".join("*" + e for e in EXT_VIDEO)), ("Todos", "*.*")], PASTA_CORTES,
            "Outro vídeo do PC…")


class SeletorMusicas(SeletorArquivos):
    """Escolher músicas da pasta Músicas/ para a trilha de fundo"""

    def __init__(self, janela_pai, ao_escolher):
        super().__init__(
            janela_pai, ao_escolher, "Escolher músicas", "Elas tocam na ordem da lista (ajuste com ▲ ▼).",
            [("Músicas baixadas", listar(PASTA_MUSICAS, EXT_AUDIO))],
            "Você ainda não baixou nenhuma música.\nUse o botão ♪ Só áudio (MP3) na tela principal, ou \"Outra "
            "música do PC…\".", [("Áudio", " ".join("*" + e for e in EXT_AUDIO)), ("Todos", "*.*")],
            PASTA_MUSICAS, "Outra música do PC…")
