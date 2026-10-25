"""Painel "Montagem": juntar todos os cortes num vídeo só."""
import tkinter as tk

import customtkinter as ctk

from . import tema
from .arquivos import nome_de_arquivo
from .juncao import TRANSICOES


class PainelMontagem(ctk.CTkFrame):
    def __init__(self, pai, ao_mudar=None):
        super().__init__(pai, fg_color=tema.CARTAO, corner_radius=14, border_width=1, border_color=tema.BORDA)
        self.ao_mudar = ao_mudar  # chamado quando a opção de juntar é ligada/desligada
        tema.rotulo(self, "MONTAGEM", 11, True, suave=True).pack(anchor="w", padx=16, pady=(12, 0))
        self.juntar = tk.BooleanVar(value=False)
        tema.chave(self, "Juntar todos os cortes num vídeo só", self.juntar, self.atualizar).pack(
            anchor="w", padx=16, pady=(8, 0))

        self.detalhes = ctk.CTkFrame(self, fg_color="transparent")
        self.detalhes.pack(fill=tk.X, padx=16, pady=(8, 0))
        tema.rotulo(self.detalhes, "Nome", 12, suave=True).grid(row=0, column=0, sticky="w")
        self.nome = tema.campo(self.detalhes)
        self.nome.insert(0, "Vídeo montado")
        self.nome.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        tema.rotulo(self.detalhes, "Transição", 12, suave=True).grid(row=0, column=1, sticky="w")
        self.transicao = tema.menu(self.detalhes, list(TRANSICOES), largura=170)
        self.transicao.set("Fade suave (0,5 s)")
        self.transicao.grid(row=1, column=1, sticky="e")
        self.detalhes.columnconfigure(0, weight=1)

        tema.rotulo(self, "A ordem é a da lista (use ▲ ▼). Os nomes dos cortes não são usados.", 11, suave=True).pack(
            anchor="w", padx=16, pady=(6, 12))
        self.atualizar()

    def atualizar(self):
        estado = "normal" if self.juntar.get() else "disabled"
        self.nome.configure(state=estado)
        self.transicao.configure(state=estado)
        if self.ao_mudar:
            self.ao_mudar(self.juntar.get())

    def opcoes(self):
        """None se for para gerar cortes separados; senão {'nome': ..., 'transicao': segundos}"""
        if not self.juntar.get():
            return None
        return {"nome": nome_de_arquivo(self.nome.get()) or "Vídeo montado",
                "transicao": TRANSICOES[self.transicao.get()]}
