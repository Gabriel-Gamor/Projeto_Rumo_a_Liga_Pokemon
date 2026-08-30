"""Tela de inventário: itens gerais e insígnias conquistadas."""

import tkinter as tk
from tkinter import ttk


class TelaInventario(ttk.Frame):
    def __init__(self,mestre,app):
        super().__init__(mestre,padding=18)

        self.app=app

        self.columnconfigure(0,weight=1)
        self.rowconfigure(3,weight=1)

        ttk.Label(
            self,
            text="Inventário",
            style="Subtitulo.TLabel"
        ).grid(row=0,column=0,sticky="w",pady=(0,12))

        # ---------------------------------------------------------
        # ITENS
        # ---------------------------------------------------------

        itens=ttk.LabelFrame(
            self,
            text="Itens da jornada",
            padding=15
        )
        itens.grid(row=1,column=0,sticky="ew",pady=(0,15))
        itens.columnconfigure(0,weight=1)

        self.texto_itens=tk.StringVar(master=self)

        ttk.Label(
            itens,
            textvariable=self.texto_itens,
            justify="left"
        ).grid(row=0,column=0,sticky="w")

        ttk.Label(
            itens,
            text="As ervas são utilizadas imediatamente ao serem coletadas.",
            style="Suave.TLabel"
        ).grid(row=1,column=0,sticky="w",pady=(10,0))

        # ---------------------------------------------------------
        # INSÍGNIAS
        # ---------------------------------------------------------

        insignias=ttk.LabelFrame(
            self,
            text="Insígnias conquistadas",
            padding=15
        )
        insignias.grid(row=2,column=0,sticky="ew")
        insignias.columnconfigure(0,weight=1)

        self.contagem_insignias=tk.StringVar(master=self)

        ttk.Label(
            insignias,
            textvariable=self.contagem_insignias,
            style="Subtitulo.TLabel"
        ).grid(row=0,column=0,sticky="w",pady=(0,10))

        self.texto_insignias=tk.StringVar(master=self)

        ttk.Label(
            insignias,
            textvariable=self.texto_insignias,
            justify="left"
        ).grid(row=1,column=0,sticky="w")

    def atualizar(self):
        j=self.app.jogo.jogador
        m=self.app.jogo.mundo

        # Conta quantas ervas já foram encontradas durante a jornada.
        ervas=sum(
            1
            for evento in m.historico
            if evento.get("tipo")=="item_coletado" and evento.get("erva")
        )

        self.texto_itens.set(
            f"Incubadora: {'Sim' if j.incubadora else 'Não'}\n"
            f"Ovos incubando: {len(j.ovos)}\n"
            f"Pokémon ativos: {len(j.equipe)}\n"
            f"Posições ocupadas: {j.ocupacao}/7\n"
            f"Pokémon no depósito: {len(j.deposito)}\n"
            f"Número de ervas coletadas: {ervas}"
        )

        ordem=[
            g.insignia
            for g in m.regiao.ginasios
            if g.insignia in j.insignias
        ]

        self.contagem_insignias.set(
            f"{len(ordem)} / 8 insígnias"
        )

        if ordem:
            self.texto_insignias.set(
                "\n".join(f"✓ {insignia}" for insignia in ordem)
            )
        else:
            self.texto_insignias.set(
                "Nenhuma insígnia conquistada."
            )