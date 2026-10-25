"""Tabela de cortes: uma linha por corte (início, fim e nome), com ordem ajustável."""
import tkinter as tk

import customtkinter as ctk

from . import tema
from .arquivos import nome_de_arquivo
from .tempos import formatar_tempo, para_segundos, tempo_curto


class ListaCortes(ctk.CTkFrame):
    def __init__(self, pai, nomes_existentes=None, altura=250):
        """nomes_existentes(): nomes já usados por cortes gravados (para o nome padrão não repetir)"""
        super().__init__(pai, fg_color="transparent")
        self.nomes_existentes = nomes_existentes or (lambda: [])
        self.linhas = []

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill=tk.X, padx=(6, 22))
        for texto, largura in (("INÍCIO", 74), ("FIM", 74), ("NOME DO CORTE", 0)):
            tema.rotulo(cabecalho, texto, 10, True, suave=True, width=largura, anchor="w").pack(
                side=tk.LEFT, padx=(0, 6), fill=tk.X, expand=not largura)

        # Botão e dica primeiro (embaixo): a lista ocupa o que sobrar e nunca esconde o botão
        tema.rotulo(self, "Tempos em minutos:segundos (ex: 15:05)  •  Enter no nome cria outro corte", 11,
                    suave=True).pack(side=tk.BOTTOM, anchor="w", padx=6, pady=(6, 0))
        tema.botao(self, "+ Adicionar corte", tema.CINZA, self.adicionar_linha, altura=34).pack(
            side=tk.BOTTOM, anchor="w", padx=6, pady=(6, 0))
        self.quadro = ctk.CTkScrollableFrame(self, fg_color="transparent", height=altura)
        self.quadro.pack(fill=tk.BOTH, expand=True)
        self.adicionar_linha()

    # --- Nome padrão ---
    def nome_padrao(self):
        """'Corte 1', 'Corte 2'...: o primeiro número que ainda não está na lista nem nos cortes já gravados"""
        usados = {l["nome"].get().strip().lower() for l in self.linhas}
        usados |= {nome.lower() for nome in self.nomes_existentes()}
        n = 1
        while f"corte {n}" in usados:
            n += 1
        return f"Corte {n}"

    @staticmethod
    def vazia(linha):
        """Linha sem tempos e com o nome ainda no padrão (ou sem nome): conta como linha em branco"""
        return (not linha["inicio"].get().strip() and not linha["fim"].get().strip()
                and linha["nome"].get().strip() in ("", linha["nome_padrao"]))

    # --- Linhas ---
    def rolar_ate_o_fim(self):
        self.after(60, lambda: self.quadro._parent_canvas.yview_moveto(1.0))

    def adicionar_linha(self, focar=True):
        padrao = self.nome_padrao()
        linha = ctk.CTkFrame(self.quadro, fg_color="transparent")
        linha.pack(fill=tk.X, pady=3)
        inicio = tema.campo(linha, width=74, justify="center", placeholder_text="00:00")
        fim = tema.campo(linha, width=74, justify="center", placeholder_text="00:00")
        nome = tema.campo(linha)
        nome.insert(0, padrao)
        inicio.pack(side=tk.LEFT, padx=(0, 6))
        fim.pack(side=tk.LEFT, padx=(0, 6))
        nome.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)
        tema.botao_pequeno(linha, "▲", lambda: self.mover_linha(linha, -1), 28).pack(side=tk.LEFT)
        tema.botao_pequeno(linha, "▼", lambda: self.mover_linha(linha, 1), 28).pack(side=tk.LEFT)
        tema.botao_pequeno(linha, "✕", lambda: self.remover_linha(linha), 28, cor_texto=tema.VERMELHO_TEXTO).pack(
            side=tk.LEFT)
        nome.bind("<Return>", lambda e: self.adicionar_linha())

        self.linhas.append({"frame": linha, "inicio": inicio, "fim": fim, "nome": nome, "nome_padrao": padrao})
        if focar:
            inicio.focus_set()
        self.rolar_ate_o_fim()
        return self.linhas[-1]

    def adicionar_corte(self, inicio, fim):
        """Coloca um corte marcado no player na lista (usa a primeira linha em branco, se houver)"""
        # focar=False: não tira o foco do player, senão os atalhos de teclado param de funcionar
        linha = next((l for l in self.linhas if self.vazia(l)), None) or self.adicionar_linha(focar=False)
        linha["inicio"].delete(0, tk.END)
        linha["fim"].delete(0, tk.END)
        linha["inicio"].insert(0, tempo_curto(inicio))
        linha["fim"].insert(0, tempo_curto(fim))
        self.rolar_ate_o_fim()

    def mover_linha(self, linha, direcao):
        """Sobe (-1) ou desce (+1) um corte na lista; a ordem da lista é a ordem do vídeo montado"""
        posicao = next(i for i, l in enumerate(self.linhas) if l["frame"] is linha)
        destino = posicao + direcao
        if not 0 <= destino < len(self.linhas):
            return
        self.linhas[posicao], self.linhas[destino] = self.linhas[destino], self.linhas[posicao]
        for l in self.linhas:  # reempilha as linhas na nova ordem
            l["frame"].pack_forget()
            l["frame"].pack(fill=tk.X, pady=3)

    def remover_linha(self, linha):
        if len(self.linhas) == 1:
            # Sempre fica pelo menos uma linha: volta ao estado em branco
            unica = self.linhas[0]
            for campo in ("inicio", "fim", "nome"):
                unica[campo].delete(0, tk.END)
            unica["nome"].insert(0, unica["nome_padrao"])
            return
        self.linhas = [l for l in self.linhas if l["frame"] is not linha]
        linha.destroy()

    def ler_cortes(self):
        """Lê os cortes da tela. Retorna ([(início, fim, nome)], [mensagens de erro])"""
        cortes, erros = [], []
        for n, linha in enumerate(self.linhas, start=1):
            if self.vazia(linha):
                continue
            nome = nome_de_arquivo(linha["nome"].get())
            try:
                inicio = para_segundos(linha["inicio"].get().strip())
                fim = para_segundos(linha["fim"].get().strip())
            except ValueError:
                erros.append(f"Corte {n}: preencha início e fim como minutos:segundos (ex: 15:05)")
                continue
            if fim <= inicio:
                erros.append(f"Corte {n}: o fim ({formatar_tempo(fim)}) precisa ser depois do início "
                             f"({formatar_tempo(inicio)})")
                continue
            cortes.append((inicio, fim, nome))
        return cortes, erros
