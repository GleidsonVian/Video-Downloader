"""Tabela de cortes da janela principal: uma linha por corte (início, fim e nome)."""
import tkinter as tk
from tkinter import ttk

from .arquivos import nome_de_arquivo
from .tempos import formatar_tempo, para_segundos, tempo_curto

LARGURAS_COLUNAS = (75, 75, 300, 30)


def configurar_colunas(frame):
    """Mesma largura de colunas no cabeçalho e nas linhas, para ficarem alinhados"""
    for coluna, largura in enumerate(LARGURAS_COLUNAS):
        frame.columnconfigure(coluna, minsize=largura)


class ListaCortes(tk.Frame):
    def __init__(self, pai):
        super().__init__(pai)
        self.linhas = []

        # Cabeçalho
        cabecalho = tk.Frame(self)
        cabecalho.pack(fill=tk.X, pady=(10, 0))
        configurar_colunas(cabecalho)
        for coluna, texto in enumerate(("Início", "Fim", "Nome do corte (opcional)")):
            tk.Label(cabecalho, text=texto, font=("Arial", 8, "bold")).grid(row=0, column=coluna, sticky="w")

        # Linhas, com rolagem
        container = tk.Frame(self)
        container.pack(fill=tk.X)
        self.canvas = tk.Canvas(container, height=150, highlightthickness=0)
        rolagem = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.quadro = tk.Frame(self.canvas)
        self.quadro.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.quadro, anchor="nw")
        self.canvas.configure(yscrollcommand=rolagem.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        rolagem.pack(side=tk.RIGHT, fill=tk.Y)
        # Rolagem com a roda do mouse só enquanto o mouse está sobre a lista
        rolar = lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units")
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", rolar))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.adicionar_linha()
        tk.Button(self, text="+ Adicionar corte", command=self.adicionar_linha).pack(anchor="w", pady=(4, 6))
        tk.Label(self, text="Tempos em minutos:segundos (ex: 15:05)  •  Enter no nome adiciona outro corte",
                 font=("Arial", 8), fg="gray").pack()

    def rolar_ate_o_fim(self):
        self.after(50, lambda: self.canvas.yview_moveto(1.0))

    def adicionar_linha(self, focar=True):
        linha = tk.Frame(self.quadro)
        linha.pack(fill=tk.X, pady=2)
        configurar_colunas(linha)
        inicio = tk.Entry(linha, width=8, justify="center")
        fim = tk.Entry(linha, width=8, justify="center")
        nome = tk.Entry(linha, width=40)
        inicio.grid(row=0, column=0, sticky="w")
        fim.grid(row=0, column=1, sticky="w")
        nome.grid(row=0, column=2, sticky="w")
        tk.Button(linha, text="✕", fg="#c4302b", relief="flat",
                  command=lambda: self.remover_linha(linha)).grid(row=0, column=3)
        nome.bind("<Return>", lambda e: self.adicionar_linha())

        self.linhas.append({"frame": linha, "inicio": inicio, "fim": fim, "nome": nome})
        if focar:
            inicio.focus_set()
        self.rolar_ate_o_fim()
        return self.linhas[-1]

    def adicionar_corte(self, inicio, fim):
        """Coloca um corte marcado no player na lista (usa a primeira linha vazia, se houver)"""
        vazia = next((l for l in self.linhas
                      if not any(l[campo].get().strip() for campo in ("inicio", "fim", "nome"))), None)
        # focar=False: não tira o foco do player, senão os atalhos de teclado param de funcionar
        linha = vazia or self.adicionar_linha(focar=False)
        linha["inicio"].insert(0, tempo_curto(inicio))
        linha["fim"].insert(0, tempo_curto(fim))
        self.rolar_ate_o_fim()

    def remover_linha(self, linha):
        if len(self.linhas) == 1:
            # Sempre fica pelo menos uma linha: só limpa os campos
            for campo in ("inicio", "fim", "nome"):
                self.linhas[0][campo].delete(0, tk.END)
            return
        self.linhas = [l for l in self.linhas if l["frame"] is not linha]
        linha.destroy()

    def ler_cortes(self):
        """Lê os cortes da tela. Retorna ([(início, fim, nome)], [mensagens de erro])"""
        cortes, erros = [], []
        for n, linha in enumerate(self.linhas, start=1):
            inicio_txt = linha["inicio"].get().strip()
            fim_txt = linha["fim"].get().strip()
            nome = nome_de_arquivo(linha["nome"].get())
            if not (inicio_txt or fim_txt or nome):
                continue  # linha vazia
            try:
                inicio, fim = para_segundos(inicio_txt), para_segundos(fim_txt)
            except ValueError:
                erros.append(f"Corte {n}: preencha início e fim como minutos:segundos (ex: 15:05)")
                continue
            if fim <= inicio:
                erros.append(f"Corte {n}: o fim ({formatar_tempo(fim)}) precisa ser depois do início "
                             f"({formatar_tempo(inicio)})")
                continue
            cortes.append((inicio, fim, nome))
        return cortes, erros
