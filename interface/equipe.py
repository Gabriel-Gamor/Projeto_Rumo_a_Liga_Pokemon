"""Equipe ativa, ovos, escolha do excedente, depósito e treinamento."""

import tkinter as tk
from tkinter import ttk

from interface.componentes import Tabela, tipos_texto, habilitar


class TelaEquipe(ttk.Frame):
    def __init__(self, mestre, app):
        super().__init__(mestre,padding=16)
        self.app=app
        self.columnconfigure(0,weight=1)
        self.rowconfigure(1,weight=3)
        self.rowconfigure(5,weight=2)
        self.resumo=tk.StringVar(master=self)
        ttk.Label(self,textvariable=self.resumo,style="Subtitulo.TLabel").grid(row=0,column=0,sticky="w",pady=(0,9))
        colunas=[('id','ID',80),('nome','Pokémon',145),('tipos','Tipos',150),('fase','Fase',50),
                 ('xp','XP',65),('hp','HP',65),('ap','AP',65),('dp','DP',65),('estado','Estado',120)]
        self.ativos=Tabela(self,colunas,altura=6)
        self.ativos.grid(row=1,column=0,sticky="nsew")
        self.ativos.arvore.bind('<<TreeviewSelect>>',lambda e:self.detalhar())
        linha=ttk.Frame(self)
        linha.grid(row=2,column=0,sticky="ew",pady=(8,0))
        self.btn_guardar=ttk.Button(linha,text="Enviar selecionado ao professor",command=self.guardar)
        self.btn_guardar.pack(side="left")
        self.btn_treinar=ttk.Button(linha,text="Treinar dois Pokémon",command=app.treinar)
        self.btn_treinar.pack(side="left",padx=8)
        self.detalhes=tk.StringVar(master=self,value="Selecione um Pokémon para ver os ataques disponíveis.")
        ttk.Label(self,textvariable=self.detalhes,wraplength=1040,style="Suave.TLabel").grid(row=3,column=0,sticky="ew",pady=(9,8))
        self.pendente_frame=ttk.LabelFrame(self,text="Sétima posição — escolha quem permanece",padding=10)
        self.pendente_frame.grid(row=4,column=0,sticky="ew",pady=(0,10))
        self.pendente_frame.columnconfigure(0,weight=1)
        self.pendente_texto=tk.StringVar(master=self)
        ttk.Label(self.pendente_frame,textvariable=self.pendente_texto,wraplength=750,style="Aviso.TLabel").grid(row=0,column=0,sticky="w")
        self.btn_pendente=ttk.Button(self.pendente_frame,text="Enviar o recém-chegado",command=self.guardar_pendente)
        self.btn_pendente.grid(row=0,column=1,padx=(8,0))
        inferior=ttk.Frame(self)
        inferior.grid(row=5,column=0,sticky="nsew")
        inferior.columnconfigure(0,weight=1)
        inferior.columnconfigure(1,weight=2)
        inferior.rowconfigure(0,weight=1)
        ovos=ttk.LabelFrame(inferior,text="Incubadora",padding=10)
        ovos.grid(row=0,column=0,sticky="nsew",padx=(0,12))
        ovos.columnconfigure(0,weight=1)
        ovos.rowconfigure(0,weight=1)
        self.ovos=Tabela(ovos,[('id','Ovo',65),('tipo','Conteúdo',135),('faltam','Faltam',65)],altura=3)
        self.ovos.grid(row=0,column=0,sticky="nsew")
        ttk.Label(ovos,text="Tipo desconhecido até chocar.\nOvos coletados não podem ser abandonados.",style="Suave.TLabel").grid(row=1,column=0,sticky="w",pady=(7,0))
        professor=ttk.LabelFrame(inferior,text="Depósito do Professor Carvalho",padding=10)
        professor.grid(row=0,column=1,sticky="nsew")
        professor.columnconfigure(0,weight=1)
        professor.rowconfigure(0,weight=1)
        self.deposito=Tabela(professor,[('id','ID',70),('nome','Pokémon',125),('tipos','Tipos',130),('hp','HP',55)],altura=3)
        self.deposito.grid(row=0,column=0,sticky="nsew")
        self.deposito.arvore.bind('<<TreeviewSelect>>',lambda e:self.atualizar_botoes())
        self.btn_retirar=ttk.Button(professor,text="Retirar selecionado (no laboratório)",command=self.retirar)
        self.btn_retirar.grid(row=1,column=0,sticky="w",pady=(7,0))
        self.insignias=tk.StringVar(master=self)
        ttk.Label(self,textvariable=self.insignias,wraplength=1050).grid(row=6,column=0,sticky="w",pady=(12,0))

    def atualizar(self):
        j=self.app.jogo.jogador
        self.resumo.set(f"Equipe: {len(j.equipe)}/6 ativos  ·  Ocupação: {j.ocupacao}/7 com ovos  ·  Pokébolas: {j.pokebolas}")
        linhas=[]
        for p in j.equipe:
            r=p.resumo()
            linhas.append((p.codigo,(p.codigo,p.nome,tipos_texto(p.tipos),p.fase+1,p.xp,
                                     f'{p.hp:.1f}',f'{p.ap:.1f}',f'{p.dp:.1f}',r['estado']),r['estado']))
        self.ativos.preencher(linhas)
        self.ovos.preencher([(o.codigo,(o.codigo,'Desconhecido',max(0,o.choca_em-self.app.jogo.mundo.agora)),'') for o in j.ovos])
        self.deposito.preencher([(p.codigo,(p.codigo,p.nome,tipos_texto(p.tipos),f'{p.hp:.1f}'),p.resumo()['estado']) for p in j.deposito])
        if j.pendente:
            p=j.pendente
            self.pendente_texto.set(f"{p.codigo} · {p.nome} · {tipos_texto(p.tipos)} · HP {p.hp:.1f}\nEle ainda não é ativo. Envie alguém da equipe acima ou o recém-chegado ao professor.")
            self.pendente_frame.grid()
        else:
            self.pendente_frame.grid_remove()
        self.insignias.set('Insígnias obtidas: '+(', '.join(sorted(j.insignias)) or 'nenhuma ainda')+f'  ({len(j.insignias)}/8)')
        self.detalhar()

    def detalhar(self):
        codigo=self.ativos.selecionado()
        p=next((p for p in self.app.jogo.jogador.equipe if p.codigo==codigo),None)
        if p:
            texto=f"{p.nome} — ataques: "+', '.join(f'{a.nome} ({tipos_texto((a.tipo,))})' for a in p.ataques)
            if p.grave:
                texto+='  ·  Ferimento grave: precisa de PMC.'
            elif not p.consciente:
                texto+=f'  ·  Repouso até o tempo {p.inconsciente_ate}.'
            self.detalhes.set(texto)
        else:
            self.detalhes.set('Selecione um Pokémon para consultar seus ataques e estado de saúde.')
        self.atualizar_botoes()

    def atualizar_botoes(self):
        jogo=self.app.jogo
        j=jogo.jogador
        livre=not self.app.ocupado
        ativo=livre and not(jogo.expirado or jogo.inscrito or j.pendente)
        habilitar(self.btn_guardar,livre and self.ativos.selecionado() is not None)
        habilitar(self.btn_pendente,livre and j.pendente is not None)
        local=jogo.mundo.regiao.grafo.vertices[j.posicao]
        habilitar(self.btn_treinar,ativo and len(j.conscientes)>=2 and local.tipo not in {'pmc','laboratorio'})
        habilitar(self.btn_retirar,ativo and self.deposito.selecionado() is not None and
                  j.posicao==jogo.mundo.regiao.laboratorio and len(j.equipe)<6 and j.ocupacao<7)

    def guardar(self):
        codigo=self.ativos.selecionado()
        if codigo:
            self.app.acao(lambda:self.app.jogo.guardar(codigo),'Pokémon enviado ao professor.')

    def guardar_pendente(self):
        p=self.app.jogo.jogador.pendente
        if p:
            self.app.acao(lambda:self.app.jogo.guardar(p.codigo),'Recém-chegado enviado ao professor; sua equipe foi mantida.')

    def retirar(self):
        codigo=self.deposito.selecionado()
        if codigo:
            self.app.acao(lambda:self.app.jogo.retirar(codigo),'Pokémon retirado do depósito.')
