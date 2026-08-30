"""Consulta gráfica da matriz de tipos e cálculo de alvos com dois tipos."""

import tkinter as tk
from tkinter import ttk

from nucleo.tipos import TIPOS
from interface.componentes import CORES, NOMES_TIPOS, fonte

ABREVIACOES=('NOR','FOG','ÁGU','ELÉ','PLA','GEL','LUT','VEN','TER','VOA','PSÍ','INS','PED','FAN','DRA','SOM','AÇO','FAD')


class TelaTipos(ttk.Frame):
    def __init__(self,mestre,app):
        super().__init__(mestre,padding=16)
        self.app=app
        self.columnconfigure(0,weight=1)
        self.rowconfigure(2,weight=1)
        ttk.Label(self,text="Vantagens e desvantagens nas batalhas",style='Subtitulo.TLabel').grid(row=0,column=0,sticky='w')
        self.estado=tk.StringVar(master=self)
        ttk.Label(self,textvariable=self.estado,style='Suave.TLabel',wraplength=1080).grid(row=1,column=0,sticky='w',pady=(5,12))
        moldura=ttk.Frame(self)
        moldura.grid(row=2,column=0,sticky='nsew')
        moldura.rowconfigure(0,weight=1)
        moldura.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(moldura,bg='white',highlightthickness=1,highlightbackground=CORES['borda'])
        self.canvas.grid(row=0,column=0,sticky='nsew')
        sx=ttk.Scrollbar(moldura,orient='horizontal',command=self.canvas.xview)
        sy=ttk.Scrollbar(moldura,orient='vertical',command=self.canvas.yview)
        sx.grid(row=1,column=0,sticky='ew')
        sy.grid(row=0,column=1,sticky='ns')
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        ttk.Label(self,text='Linha = tipo do ataque  ·  Coluna = tipo do alvo  ·  2×: vantagem  ·  ½×: resistência  ·  0×: imune  ·  1×: normal',style='Suave.TLabel').grid(row=3,column=0,sticky='w',pady=(8,12))
        simulador=ttk.LabelFrame(self,text='Consultar um confronto',padding=12)
        simulador.grid(row=4,column=0,sticky='ew')
        self.ataque=tk.StringVar(master=self,value='Água')
        self.defesa1=tk.StringVar(master=self,value='Pedra')
        self.defesa2=tk.StringVar(master=self,value='Terra')
        valores=[NOMES_TIPOS[t] for t in TIPOS]
        for i,(label,var,opcoes) in enumerate((('Ataque',self.ataque,valores),('Alvo: tipo 1',self.defesa1,valores),('Alvo: tipo 2',self.defesa2,['Nenhum']+valores))):
            ttk.Label(simulador,text=label).grid(row=0,column=i,sticky='w',padx=(0,12))
            combo=ttk.Combobox(simulador,textvariable=var,values=opcoes,state='readonly',width=17)
            combo.grid(row=1,column=i,sticky='ew',padx=(0,12),pady=5)
            combo.bind('<<ComboboxSelected>>',lambda e:self.calcular())
        self.resultado=tk.StringVar(master=self)
        ttk.Label(simulador,textvariable=self.resultado,style='Subtitulo.TLabel',wraplength=440).grid(row=0,column=3,rowspan=2,sticky='w')
        simulador.columnconfigure(3,weight=1)

    def atualizar(self):
        ativo=self.app.jogo.mundo.tipos.habilitada
        self.estado.set(('Ativadas nesta região. ' if ativo else 'Desativadas no arquivo desta região. ')+
                        'Os fatores são lidos do JSON. Em Pokémon com dois tipos, multiplicam-se as duas células. Clique em uma célula para consultar.')
        self.desenhar()
        self.calcular()

    def desenhar(self):
        c=self.canvas
        c.delete('all')
        w,h,esquerda,topo=47,25,110,32
        cores={0:('#cfd8e0','#263644'),.5:('#f9e6d2','#854519'),1:('#f7f9fb','#81909b'),2:('#cceade','#21573f')}
        tabela=self.app.jogo.mundo.regiao.vantagens
        c.create_text(7,16,text='ATAQUE',anchor='w',font=fonte(9,'bold'),fill=CORES['texto'])
        for j,nome in enumerate(ABREVIACOES):
            c.create_text(esquerda+j*w+w/2,16,text=nome,font=fonte(9,'bold'),fill=CORES['texto'])
        for i,a in enumerate(TIPOS):
            c.create_text(8,topo+i*h+h/2,text=NOMES_TIPOS[a],anchor='w',font=fonte(9),fill=CORES['texto'])
            for j,d in enumerate(TIPOS):
                valor=tabela.get(a,{}).get(d,1)
                fundo,texto=cores[valor]
                x,y=esquerda+j*w,topo+i*h
                tag=f'celula:{i}:{j}'
                c.create_rectangle(x,y,x+w,y+h,fill=fundo,outline='white',tags=(tag,))
                c.create_text(x+w/2,y+h/2,text={0:'0×',.5:'½×',1:'1×',2:'2×'}[valor],fill=texto,font=fonte(9,'bold' if valor!=1 else 'normal'),tags=(tag,))
                c.tag_bind(tag,'<Button-1>',lambda e,a=a,d=d:self.selecionar(a,d))
        c.configure(scrollregion=(0,0,esquerda+18*w+4,topo+18*h+4))

    def selecionar(self,ataque,defesa):
        self.ataque.set(NOMES_TIPOS[ataque])
        self.defesa1.set(NOMES_TIPOS[defesa])
        self.defesa2.set('Nenhum')
        self.calcular()

    def calcular(self):
        reverso={v:k for k,v in NOMES_TIPOS.items()}
        a=reverso[self.ataque.get()]
        d=[reverso[self.defesa1.get()]]
        if self.defesa2.get()!='Nenhum':
            segundo=reverso[self.defesa2.get()]
            if segundo==d[0]:
                self.resultado.set('Escolha dois tipos diferentes.')
                return
            d.append(segundo)
        tabela=self.app.jogo.mundo.tipos
        fatores=[tabela.multiplicador(a,(t,)) for t in d]
        valor=tabela.multiplicador(a,d)
        efeito='imune' if valor==0 else 'vantagem' if valor>1 else 'resistência' if valor<1 else 'dano normal'
        self.resultado.set(' × '.join(f'{f:g}' for f in fatores)+f' = {valor:g}×  ·  {efeito}')
