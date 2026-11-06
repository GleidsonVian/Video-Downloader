"""Janela para escolher cortes já gerados (ou qualquer outro vídeo) e levá-los para a montagem."""
import os
import time
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import tema
from .arquivos import formatar_tamanho
from .biblioteca import listar_aulas
from .config import EXT_VIDEO, PASTA_CORTES, PASTA_SCRIPT


class SeletorCortes:
    def __init__(self, janela_pai, ao_escolher):
        """ao_escolher(caminhos): recebe os arquivos marcados, na ordem em que aparecem na tela"""
        self.ao_escolher = ao_escolher
        self.itens = []  # [(variável marcada, caminho)]
        self.janela = ctk.CTkToplevel(janela_pai, fg_color=tema.FUNDO)
        self.janela.title("Escolher cortes para a montagem")
        self.janela.geometry("660x640")
        self.janela.minsize(520, 460)
        self.janela.transient(janela_pai)
        tema.aplicar_icone(self.janela)

        tema.rotulo(self.janela, "Marque os cortes que quer juntar", 16, True).pack(anchor="w", padx=20, pady=(16, 0))
        tema.rotulo(self.janela, "A ordem na montagem você ajusta depois, com ▲ ▼.", 12, suave=True).pack(
            anchor="w", padx=20)
        self.quadro = ctk.CTkScrollableFrame(self.janela, fg_color=tema.CARTAO, corner_radius=14, border_width=1,
                                             border_color=tema.BORDA)
        self.quadro.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        botoes = ctk.CTkFrame(self.janela, fg_color="transparent")
        botoes.pack(fill=tk.X, padx=16, pady=(0, 14))
        tema.botao(botoes, "Outro vídeo do PC…", tema.CINZA, self.outro_arquivo, altura=40).pack(side=tk.LEFT)
        tema.botao(botoes, "Cancelar", tema.CINZA, self.janela.destroy, altura=40).pack(side=tk.RIGHT)
        self.btn_adicionar = tema.botao(botoes, "Adicionar", tema.AZUL, self.adicionar, altura=40)
        self.btn_adicionar.pack(side=tk.RIGHT, padx=(0, 8))
        self.preencher()
        self.atualizar_contagem()

    def preencher(self):
        aulas = listar_aulas(PASTA_CORTES)
        if not any(arquivos for _, arquivos in aulas):
            tema.rotulo(self.quadro, "Você ainda não gerou nenhum corte.\nUse \"Outro vídeo do PC…\" para escolher "
                        "arquivos de qualquer pasta.", 13, suave=True, justify="left").pack(padx=16, pady=20)
            return
        for pasta, arquivos in aulas:
            if not arquivos:
                continue
            titulo = ctk.CTkFrame(self.quadro, fg_color="transparent")
            titulo.pack(fill=tk.X, padx=8, pady=(12, 2))
            tema.rotulo(titulo, os.path.basename(pasta), 13, True, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
            variaveis = []
            tema.botao_pequeno(titulo, "marcar todos", lambda v=variaveis: self.marcar_todos(v), 90,
                               tema.SUAVE).pack(side=tk.RIGHT)
            for caminho, tamanho, data in sorted(arquivos, key=lambda a: os.path.basename(a[0]).lower()):
                variavel = tk.BooleanVar(value=False)
                variaveis.append(variavel)
                self.itens.append((variavel, caminho))
                texto = f"{os.path.basename(caminho)}    {formatar_tamanho(tamanho)} · {time.strftime('%d/%m %H:%M', time.localtime(data))}"
                ctk.CTkCheckBox(self.quadro, text=texto, variable=variavel, command=self.atualizar_contagem,
                                font=tema.fonte(12), text_color=tema.TEXTO, fg_color=tema.AZUL[0],
                                hover_color=tema.AZUL[1], border_color=tema.BORDA).pack(anchor="w", padx=18, pady=4)

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
            parent=self.janela, title="Escolha os vídeos", initialdir=PASTA_CORTES if os.path.isdir(PASTA_CORTES)
            else PASTA_SCRIPT, filetypes=[("Vídeos", " ".join("*" + e for e in EXT_VIDEO)), ("Todos", "*.*")])
        if caminhos:
            self.ao_escolher([os.path.normpath(c) for c in caminhos])
            self.janela.destroy()
