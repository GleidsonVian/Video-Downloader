"""Janela "Biblioteca": vídeos baixados, músicas e cortes, com tamanho, abrir e apagar."""
import os
import subprocess
import time
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from . import tema
from .arquivos import abrir_pasta, enviar_para_lixeira, formatar_tamanho, tamanho_de
from .config import EXT_AUDIO, EXT_VIDEO, PASTA_CORTES, PASTA_MUSICAS, PASTA_VIDEOS

ABAS = ("Vídeos", "Músicas", "Cortes")


def listar(pasta, extensoes):
    """Arquivos da pasta com as extensões dadas: [(caminho, tamanho, data)], do mais novo para o mais antigo"""
    if not os.path.isdir(pasta):
        return []
    itens = []
    for nome in os.listdir(pasta):
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho) and nome.lower().endswith(extensoes):
            itens.append((caminho, os.path.getsize(caminho), os.path.getmtime(caminho)))
    return sorted(itens, key=lambda item: item[2], reverse=True)


def listar_aulas(pasta):
    """Pastas de cortes: [(pasta, [arquivos])], da aula mais recente para a mais antiga"""
    if not os.path.isdir(pasta):
        return []
    aulas = []
    for nome in os.listdir(pasta):
        caminho = os.path.join(pasta, nome)
        if os.path.isdir(caminho):
            aulas.append((caminho, listar(caminho, EXT_VIDEO)))
    return sorted(aulas, key=lambda aula: os.path.getmtime(aula[0]), reverse=True)


def estilizar_tabelas():
    """Deixa as tabelas (ttk) combinando com o tema escuro"""
    estilo = ttk.Style()
    estilo.theme_use("clam")
    estilo.configure("Treeview", background=tema.CARTAO, fieldbackground=tema.CARTAO, foreground=tema.TEXTO,
                     rowheight=30, borderwidth=0, bordercolor=tema.CARTAO, lightcolor=tema.CARTAO,
                     darkcolor=tema.CARTAO, font=("Segoe UI", 10))
    estilo.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # sem a moldura branca em volta
    estilo.map("Treeview", background=[("selected", tema.AZUL[0])], foreground=[("selected", "white")])
    estilo.configure("Treeview.Heading", background=tema.BORDA, foreground=tema.SUAVE, relief="flat",
                     font=("Segoe UI", 9, "bold"), padding=6)
    estilo.map("Treeview.Heading", background=[("active", tema.BORDA)])


class JanelaBiblioteca:
    def __init__(self, janela_pai, editar_video):
        """editar_video(caminho): abre o editor com aquele vídeo"""
        self.editar_video = editar_video
        self.janela = ctk.CTkToplevel(janela_pai, fg_color=tema.FUNDO)
        self.janela.title("Biblioteca")
        self.janela.geometry("820x580")
        self.janela.minsize(640, 460)
        tema.aplicar_icone(self.janela)
        estilizar_tabelas()

        self.resumo = tema.rotulo(self.janela, "", 13, True)
        self.resumo.pack(anchor="w", padx=20, pady=(16, 0))
        self.abas = ctk.CTkTabview(self.janela, fg_color=tema.CARTAO, corner_radius=14, border_width=1,
                                   border_color=tema.BORDA, segmented_button_fg_color=tema.CAMPO,
                                   segmented_button_selected_color=tema.AZUL[0],
                                   segmented_button_selected_hover_color=tema.AZUL[1],
                                   segmented_button_unselected_color=tema.CAMPO)
        self.abas.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 0))
        self.arvores, self.totais = {}, {}
        for nome in ABAS:
            quadro = self.abas.add(nome)
            self.totais[nome] = tema.rotulo(quadro, "", 11, suave=True)
            self.totais[nome].pack(anchor="w", pady=(0, 6))
            arvore = ttk.Treeview(quadro, columns=("tamanho", "data"), selectmode="extended")
            arvore.heading("#0", text="Nome", anchor="w")
            arvore.heading("tamanho", text="Tamanho")
            arvore.heading("data", text="Data")
            arvore.column("#0", width=430)
            arvore.column("tamanho", width=90, anchor="e")
            arvore.column("data", width=130, anchor="center")
            rolagem = ctk.CTkScrollbar(quadro, command=arvore.yview)
            arvore.configure(yscrollcommand=rolagem.set)
            rolagem.pack(side=tk.RIGHT, fill=tk.Y)
            arvore.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            arvore.bind("<Double-1>", lambda e: self.abrir())
            self.arvores[nome] = arvore
        self.caminhos = {}  # id da linha -> caminho do arquivo ou pasta
        self.contador = 0

        botoes = ctk.CTkFrame(self.janela, fg_color="transparent")
        botoes.pack(fill=tk.X, padx=16, pady=14)
        for texto, cor, comando in (("▶  Abrir", tema.CINZA, self.abrir),
                                    ("📂  Mostrar na pasta", tema.CINZA, self.mostrar_na_pasta),
                                    ("✂  Editar", tema.AZUL, self.editar),
                                    ("🗑  Apagar", tema.VERMELHO, self.apagar),
                                    ("⟳  Atualizar", tema.CINZA, self.atualizar)):
            tema.botao(botoes, texto, cor, comando, altura=38).pack(side=tk.LEFT, padx=(0, 8))
        self.janela.bind("<F5>", lambda e: self.atualizar())
        self.janela.bind("<Delete>", lambda e: self.apagar())
        self.atualizar()

    # --- Conteúdo ---
    @staticmethod
    def data(timestamp):
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp))

    def inserir(self, arvore, pai, caminho, tamanho, timestamp, nome=None):
        # O id da linha tem que ser único entre TODAS as abas: por padrão cada tabela numera as suas
        # linhas começando do mesmo número, e aí o caminho de uma aba se misturaria com o de outra.
        self.contador += 1
        iid = arvore.insert(pai, "end", iid=f"L{self.contador}", text="  " + (nome or os.path.basename(caminho)),
                            open=True, values=(formatar_tamanho(tamanho), self.data(timestamp)))
        self.caminhos[iid] = caminho
        return iid

    def atualizar(self):
        self.caminhos.clear()
        for arvore in self.arvores.values():
            arvore.delete(*arvore.get_children())
        total = {}
        for nome, pasta, extensoes in (("Vídeos", PASTA_VIDEOS, EXT_VIDEO), ("Músicas", PASTA_MUSICAS, EXT_AUDIO)):
            itens = listar(pasta, extensoes)
            for caminho, tamanho, timestamp in itens:
                self.inserir(self.arvores[nome], "", caminho, tamanho, timestamp)
            total[nome] = (len(itens), sum(t for _, t, _ in itens))
        quantidade, bytes_ = 0, 0
        for pasta, arquivos in listar_aulas(PASTA_CORTES):
            soma = sum(t for _, t, _ in arquivos)
            pai = self.inserir(self.arvores["Cortes"], "", pasta, soma, os.path.getmtime(pasta),
                               nome=f"{os.path.basename(pasta)}  ({len(arquivos)} arquivos)")
            for caminho, tamanho, timestamp in arquivos:
                self.inserir(self.arvores["Cortes"], pai, caminho, tamanho, timestamp)
            quantidade, bytes_ = quantidade + len(arquivos), bytes_ + soma
        total["Cortes"] = (quantidade, bytes_)
        for nome in ABAS:
            self.totais[nome].configure(text=f"{total[nome][0]} arquivo(s) · {formatar_tamanho(total[nome][1])}")
        self.resumo.configure(text=f"Biblioteca — {formatar_tamanho(sum(b for _, b in total.values()))} ocupados")

    # --- Ações ---
    def selecionados(self):
        arvore = self.arvores[self.abas.get()]
        return [self.caminhos[i] for i in arvore.selection() if i in self.caminhos]

    def primeiro(self):
        itens = self.selecionados()
        if not itens:
            messagebox.showinfo("Biblioteca", "Selecione um item na lista.", parent=self.janela)
        return itens[0] if itens else None

    def abrir(self):
        caminho = self.primeiro()
        if caminho:
            os.startfile(caminho)  # abre no player/explorador padrão do Windows

    def mostrar_na_pasta(self):
        caminho = self.primeiro()
        if not caminho:
            return
        if os.path.isdir(caminho):
            abrir_pasta(caminho)
        else:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(caminho)])

    def editar(self):
        caminho = self.primeiro()
        if not caminho:
            return
        if not caminho.lower().endswith(EXT_VIDEO):
            messagebox.showinfo("Biblioteca", "Só vídeos podem ser abertos no editor.", parent=self.janela)
            return
        self.editar_video(caminho)

    def apagar(self):
        itens = self.selecionados()
        if not itens:
            messagebox.showinfo("Biblioteca", "Selecione o que quer apagar.", parent=self.janela)
            return
        # Selecionar uma aula e um corte dentro dela ao mesmo tempo: a pasta já inclui o arquivo
        itens = [c for c in itens if not any(o != c and c.startswith(o + os.sep) for o in itens)]
        tamanho = sum(tamanho_de(c) for c in itens)
        nomes = "\n".join("• " + os.path.basename(c) for c in itens[:8])
        nomes += f"\n… e mais {len(itens) - 8}" if len(itens) > 8 else ""
        if not messagebox.askyesno("Apagar", f"Mandar {len(itens)} item(ns) ({formatar_tamanho(tamanho)}) para a "
                                   f"Lixeira?\n\n{nomes}", parent=self.janela):
            return
        falhas = [os.path.basename(c) for c in itens if not enviar_para_lixeira(c)]
        if falhas:
            messagebox.showwarning("Apagar", "Não consegui apagar (algum programa está usando?):\n\n"
                                   + "\n".join(falhas), parent=self.janela)
        self.atualizar()
