"""Painel "Montagem": juntar vários cortes num vídeo só (da lista de tempos ou de cortes já gerados)."""
import os
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import tema
from .arquivos import nome_de_arquivo
from .config import EXT_IMAGEM, EXT_VIDEO, PASTA_SCRIPT, PASTA_VINHETAS
from .juncao import TRANSICOES
from .seletor_cortes import SeletorCortes

FONTES = {"Cortes da lista": "lista", "Cortes já gerados": "prontos"}
DICAS = {"lista": "A ordem é a da lista de cortes (use ▲ ▼). Os nomes dos cortes não são usados.",
         "prontos": "Usa os arquivos escolhidos acima, na ordem mostrada. A lista de cortes não é usada."}


class SeletorVinheta(ctk.CTkFrame):
    """Escolha de uma vinheta (imagem ou vídeo) entre os arquivos da pasta Vinhetas/, ou de qualquer lugar"""
    NENHUMA = "Nenhuma"

    def __init__(self, pai, titulo):
        super().__init__(pai, fg_color="transparent")
        self.arquivos = {}  # nome mostrado -> caminho
        self.escolha = tk.StringVar(value=self.NENHUMA)
        tema.rotulo(self, titulo, 12, suave=True, width=84, anchor="w").pack(side=tk.LEFT)
        self.menu = tema.menu(self, [self.NENHUMA], self.escolha, largura=190)
        self.menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tema.botao(self, "…", tema.CINZA, self.procurar, altura=34, width=40).pack(side=tk.LEFT, padx=(6, 0))
        self.atualizar()

    def atualizar(self):
        """Relê a pasta Vinhetas/ (a escolha atual é mantida se o arquivo ainda existir)"""
        if os.path.isdir(PASTA_VINHETAS):
            for nome in sorted(os.listdir(PASTA_VINHETAS)):
                if nome.lower().endswith(EXT_IMAGEM + EXT_VIDEO):
                    self.arquivos[nome] = os.path.join(PASTA_VINHETAS, nome)
        self.arquivos = {n: c for n, c in self.arquivos.items() if os.path.exists(c)}
        self.menu.configure(values=[self.NENHUMA] + list(self.arquivos))
        if self.escolha.get() not in self.arquivos:
            self.escolha.set(self.NENHUMA)

    def procurar(self):
        caminho = filedialog.askopenfilename(
            title="Escolha a vinheta (imagem ou vídeo)",
            initialdir=PASTA_VINHETAS if os.path.isdir(PASTA_VINHETAS) else PASTA_SCRIPT,
            filetypes=[("Imagem ou vídeo", " ".join("*" + e for e in EXT_IMAGEM + EXT_VIDEO)), ("Todos", "*.*")])
        if caminho:
            self.arquivos[os.path.basename(caminho)] = os.path.normpath(caminho)
            self.atualizar()
            self.escolha.set(os.path.basename(caminho))

    def caminho(self):
        """Arquivo escolhido, ou None se for 'Nenhuma'"""
        return self.arquivos.get(self.escolha.get())

    def configurar(self, estado):
        self.menu.configure(state=estado)


class PainelMontagem(ctk.CTkFrame):
    def __init__(self, pai, ao_mudar=None):
        super().__init__(pai, fg_color=tema.CARTAO, corner_radius=14, border_width=1, border_color=tema.BORDA)
        self.ao_mudar = ao_mudar  # chamado quando a opção de juntar é ligada/desligada
        self.arquivos = []        # cortes já gerados escolhidos para a montagem, na ordem
        self.fonte = tk.StringVar(value="lista")
        tema.rotulo(self, "MONTAGEM", 11, True, suave=True).pack(anchor="w", padx=16, pady=(12, 0))
        self.juntar = tk.BooleanVar(value=False)
        tema.chave(self, "Juntar os cortes num vídeo só", self.juntar, self.atualizar).pack(
            anchor="w", padx=16, pady=(8, 0))

        self.seletor = ctk.CTkSegmentedButton(
            self, values=list(FONTES), command=self.escolheu_fonte, height=32, corner_radius=8,
            fg_color=tema.CAMPO, selected_color=tema.AZUL[0], selected_hover_color=tema.AZUL[1],
            unselected_color=tema.CAMPO, unselected_hover_color=tema.CINZA[0], font=tema.fonte(12, True))
        self.seletor.set("Cortes da lista")
        self.seletor.pack(fill=tk.X, padx=16, pady=(8, 0))

        # Só aparece na fonte "Cortes já gerados"
        self.quadro_prontos = ctk.CTkFrame(self, fg_color="transparent")
        topo = ctk.CTkFrame(self.quadro_prontos, fg_color="transparent")
        topo.pack(fill=tk.X)
        tema.botao(topo, "+ Escolher cortes…", tema.CINZA, self.escolher, altura=32).pack(side=tk.LEFT)
        self.resumo = tema.rotulo(topo, "", 12, suave=True)
        self.resumo.pack(side=tk.LEFT, padx=10)
        # Sem rolagem própria (a coluna do editor já rola): a lista cresce conforme os cortes escolhidos
        self.lista = ctk.CTkFrame(self.quadro_prontos, fg_color=tema.CAMPO, corner_radius=10)
        self.lista.pack(fill=tk.X, pady=(6, 0))

        self.detalhes = ctk.CTkFrame(self, fg_color="transparent")
        self.detalhes.pack(fill=tk.X, padx=16, pady=(10, 0))
        tema.rotulo(self.detalhes, "Nome", 12, suave=True).grid(row=0, column=0, sticky="w")
        self.nome = tema.campo(self.detalhes)
        self.nome.insert(0, "Vídeo montado")
        self.nome.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        tema.rotulo(self.detalhes, "Transição", 12, suave=True).grid(row=0, column=1, sticky="w")
        self.transicao = tema.menu(self.detalhes, list(TRANSICOES), largura=170)
        self.transicao.set("Fade suave (0,5 s)")
        self.transicao.grid(row=1, column=1, sticky="e")
        self.detalhes.columnconfigure(0, weight=1)

        # Vinhetas: entram antes e depois de todos os cortes da montagem
        self.quadro_vinhetas = ctk.CTkFrame(self, fg_color="transparent")
        self.quadro_vinhetas.pack(fill=tk.X, padx=16, pady=(10, 0))
        self.abertura = SeletorVinheta(self.quadro_vinhetas, "Abertura")
        self.abertura.pack(fill=tk.X)
        self.encerramento = SeletorVinheta(self.quadro_vinhetas, "Encerramento")
        self.encerramento.pack(fill=tk.X, pady=(6, 0))
        linha_imagem = ctk.CTkFrame(self.quadro_vinhetas, fg_color="transparent")
        linha_imagem.pack(fill=tk.X, pady=(6, 0))
        tema.rotulo(linha_imagem, "Imagem fica na tela por", 12, suave=True).pack(side=tk.LEFT)
        self.segundos_imagem = tema.campo(linha_imagem, width=48, justify="center")
        self.segundos_imagem.insert(0, "3")
        self.segundos_imagem.pack(side=tk.LEFT, padx=6)
        tema.rotulo(linha_imagem, "segundos", 12, suave=True).pack(side=tk.LEFT)

        self.dica = tema.rotulo(self, DICAS["lista"], 11, suave=True, wraplength=300, justify="left")
        self.dica.pack(anchor="w", padx=16, pady=(6, 12))
        self.atualizar()

    # --- Fonte dos cortes ---
    def escolheu_fonte(self, nome):
        self.fonte.set(FONTES[nome])
        self.atualizar()

    def escolher(self):
        janela = SeletorCortes(self.winfo_toplevel(), self.adicionar)
        janela.janela.after(150, janela.janela.focus_force)

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

    def redesenhar(self):
        for filho in self.lista.winfo_children():
            filho.destroy()
        for i, caminho in enumerate(self.arquivos):
            linha = ctk.CTkFrame(self.lista, fg_color="transparent")
            linha.pack(fill=tk.X, pady=1, padx=2)
            tema.rotulo(linha, f"{i + 1}.  {os.path.basename(caminho)}", 12, anchor="w").pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
            tema.botao_pequeno(linha, "▲", lambda i=i: self.mover(i, -1), 26).pack(side=tk.LEFT)
            tema.botao_pequeno(linha, "▼", lambda i=i: self.mover(i, 1), 26).pack(side=tk.LEFT)
            tema.botao_pequeno(linha, "✕", lambda i=i: self.remover(i), 26, cor_texto=tema.VERMELHO_TEXTO).pack(
                side=tk.LEFT)
        if not self.arquivos:
            tema.rotulo(self.lista, "Clique em \"+ Escolher cortes…\" para começar.", 12, suave=True).pack(pady=14)
        n = len(self.arquivos)
        self.resumo.configure(text=f"{n} corte(s) escolhido(s)" if n else "nenhum corte escolhido")

    def atualizar(self):
        ligado = self.juntar.get()
        estado = "normal" if ligado else "disabled"
        self.seletor.configure(state=estado)
        self.nome.configure(state=estado)
        self.transicao.configure(state=estado)
        self.abertura.configurar(estado)
        self.encerramento.configurar(estado)
        self.segundos_imagem.configure(state=estado)
        if ligado:
            self.abertura.atualizar()
            self.encerramento.atualizar()
        fonte = self.fonte.get()
        if fonte == "prontos":
            self.quadro_prontos.pack(fill=tk.X, padx=16, pady=(8, 0), before=self.detalhes)
            self.redesenhar()
        else:
            self.quadro_prontos.pack_forget()
        self.dica.configure(text=DICAS[fonte])
        if self.ao_mudar:
            self.ao_mudar(ligado)

    def opcoes(self):
        """None se for para gerar cortes separados; senão
        {'nome', 'transicao' (segundos), 'fonte' ('lista' ou 'prontos'), 'arquivos' (se fonte 'prontos'),
        'abertura' e 'encerramento' (arquivo ou None), 'duracao_imagem' (segundos)}"""
        if not self.juntar.get():
            return None
        try:
            segundos = min(max(float(self.segundos_imagem.get().replace(",", ".")), 1.0), 15.0)
        except ValueError:
            segundos = 3.0
        return {"nome": nome_de_arquivo(self.nome.get()) or "Vídeo montado",
                "transicao": TRANSICOES[self.transicao.get()], "fonte": self.fonte.get(),
                "arquivos": list(self.arquivos), "abertura": self.abertura.caminho(),
                "encerramento": self.encerramento.caminho(), "duracao_imagem": segundos}
