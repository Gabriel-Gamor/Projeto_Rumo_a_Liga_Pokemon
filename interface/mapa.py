"""Mapa clicável: retângulos, estradas ponderadas, rotas e ações do local."""

from math import cos, pi, sin, hypot
import tkinter as tk
from tkinter import ttk

from interface.componentes import CORES, NOMES_LOCAIS, habilitar, PainelRolavel, fonte


class TelaMapa(ttk.Frame):
    def __init__(self, mestre, app):
        super().__init__(mestre,padding=12)
        self.app=app
        self.selecionado=None
        self.rota=[]
        self.centros={}
        self.arestas_desenhadas=[]
        self.rotulos_pesos=[]
        self.columnconfigure(0,weight=1)
        self.rowconfigure(1,weight=1)
        ttk.Label(self,text="Clique em uma região para ver o caminho e escolher a viagem.",style="Subtitulo.TLabel").grid(row=0,column=0,sticky="w",pady=(0,9))
        self.canvas=tk.Canvas(self,bg="#fbfcfe",highlightthickness=1,
                              highlightbackground=CORES["borda"],width=800,height=590)
        self.canvas.grid(row=1,column=0,sticky="nsew")
        self.canvas.bind("<Configure>",lambda e:self.desenhar())
        self.legenda=ttk.Label(self,text="Laranja: você   ·   Azul: rota selecionada   ·   Verde: insígnia obtida",style="Suave.TLabel")
        self.legenda.grid(row=2,column=0,sticky="w",pady=(8,0))
        rolagem=PainelRolavel(self)
        self.painel_rolavel=rolagem
        rolagem.grid(row=0,column=1,rowspan=3,sticky='nsew')
        painel=rolagem.conteudo
        painel.configure(padding=(14,0,5,0))
        painel.columnconfigure(0,weight=1)
        self.destino=tk.StringVar(master=self)
        self.informacao=tk.StringVar(master=self)
        ttk.Label(painel,text="REGIÃO SELECIONADA",style="Suave.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(painel,textvariable=self.destino,style="Subtitulo.TLabel",wraplength=290).grid(row=1,column=0,sticky="w",pady=(5,5))
        ttk.Label(painel,textvariable=self.informacao,wraplength=290).grid(row=2,column=0,sticky="w",pady=(0,8))
        viagens=ttk.Frame(painel)
        viagens.grid(row=3,column=0,sticky="ew")
        viagens.columnconfigure((0,1),weight=1)
        self.btn_passo=ttk.Button(viagens,text="Uma estrada",command=self.um_passo)
        self.btn_passo.grid(row=0,column=0,sticky="ew",padx=(0,5))
        self.btn_viajar=ttk.Button(viagens,text="Seguir rota",style="Principal.TButton",command=self.viajar)
        self.btn_viajar.grid(row=0,column=1,sticky="ew")
        ttk.Separator(painel).grid(row=4,column=0,sticky="ew",pady=12)
        self.local=tk.StringVar(master=self)
        ttk.Label(painel,textvariable=self.local,wraplength=290,style="Subtitulo.TLabel").grid(row=5,column=0,sticky="w")
        ttk.Label(painel,text="Personagens neste local",style="Suave.TLabel").grid(row=6,column=0,sticky="w",pady=(10,4))
        self.atores=ttk.Combobox(painel,state="readonly",width=31)
        self.atores.grid(row=7,column=0,sticky="ew")
        self.atores.bind("<<ComboboxSelected>>",self.selecionar_ator)
        acoes=ttk.Frame(painel)
        acoes.grid(row=8,column=0,sticky="ew",pady=(5,0))
        acoes.columnconfigure((0,1),weight=1)
        self.btn_batalha=ttk.Button(acoes,text="Desafiar",command=self.batalhar)
        self.btn_batalha.grid(row=0,column=0,sticky="ew",padx=(0,5))
        self.aviso_batalha=tk.StringVar(master=self)
        ttk.Label(acoes,textvariable=self.aviso_batalha,style="Aviso.TLabel",wraplength=290,justify="left").grid(row=1,column=0,columnspan=2,sticky="w",pady=(6,0))
        self.btn_defender=ttk.Button(acoes,text="Aceitar desafio",command=lambda:self.batalhar(True))
        self.btn_defender.grid(row=0,column=1,sticky="ew")
        ttk.Label(painel,text="Itens neste local",style="Suave.TLabel").grid(row=9,column=0,sticky="w",pady=(10,4))
        itens=ttk.Frame(painel)
        itens.grid(row=10,column=0,sticky="ew")
        itens.columnconfigure(0,weight=1)
        self.itens=ttk.Combobox(itens,state="readonly",width=21)
        self.itens.grid(row=0,column=0,sticky="ew",padx=(0,5))
        self.itens.bind("<<ComboboxSelected>>",self.selecionar_item)
        self.btn_coletar=ttk.Button(itens,text="Coletar",command=self.coletar)
        self.btn_coletar.grid(row=0,column=1)
        ttk.Label(painel,text="Passar o tempo",style="Suave.TLabel").grid(row=11,column=0,sticky="w",pady=(12,4))
        espera=ttk.Frame(painel)
        espera.grid(row=12,column=0,sticky="ew")
        espera.columnconfigure(1,weight=1)
        self.tempo=tk.StringVar(master=self,value="10")
        ttk.Spinbox(espera,from_=1,to=1000,textvariable=self.tempo,width=7).grid(row=0,column=0,padx=(0,6))
        self.btn_esperar=ttk.Button(espera,text="Esperar",command=lambda:app.acao(lambda:app.jogo.esperar(int(self.tempo.get())),"Tempo avançado."))
        self.btn_esperar.grid(row=0,column=1,sticky="ew")
        self.btn_curar=ttk.Button(painel,text="Tratar a equipe neste PMC",command=lambda:app.acao(app.jogo.tratar,"Tratamento concluído."))
        self.btn_curar.grid(row=13,column=0,sticky="ew",pady=(10,5))
        self.btn_inscrever=ttk.Button(painel,text="Inscrever na Liga",style="Principal.TButton",command=self.inscrever)
        self.btn_inscrever.grid(row=14,column=0,sticky="ew")
        self.btn_planejar=ttk.Button(painel,text="Planejar ginásios restantes",command=app.planejar)
        self.btn_planejar.grid(row=15,column=0,sticky="ew",pady=(10,0))
        ttk.Label(painel,text="O relógio só avança ao agir. Consultar as telas não consome tempo. Cruzamentos sem retângulo não são locais de parada.",style="Suave.TLabel",wraplength=290).grid(row=16,column=0,sticky="sw",pady=(12,0))
        painel.rowconfigure(16,weight=1)
        self._atores=[]
        self._itens=[]

    def atualizar(self):
        j=self.app.jogo
        g=j.mundo.regiao.grafo
        if self.selecionado not in g.adj:
            self.selecionado=j.jogador.posicao
        self.local.set("Você está em " + g.vertices[j.jogador.posicao].nome)
        alvo_anterior=self.alvo()
        self._atores=j.mundo.presentes()
        nomes=[]
        for a in self._atores:
            if a.treinador:
                nomes.append(f"{a.codigo} · {a.treinador.nome} ({a.tipo})")
            else:
                nomes.append(f"{a.codigo} · {a.pokemon.nome} · HP {a.pokemon.hp:.0f}")
        self.atores.configure(values=nomes or ["Nenhum personagem disponível"])
        indice=next((i for i,a in enumerate(self._atores) if a.codigo==alvo_anterior),0)
        self.atores.current(indice)
        self._itens=[i for i in j.mundo.itens.values() if i.posicao==j.jogador.posicao and not i.recolhido]
        self.itens.configure(values=[f"{i.codigo} · "+("Ovo desconhecido" if i.tipo=="ovo" else "Erva (+10 HP)") for i in self._itens] or ["Nenhum item disponível"])
        self.itens.current(0)
        self.selecionar(self.selecionado)

    def selecionar(self,codigo):
        self.selecionado=codigo
        j=self.app.jogo
        regiao=j.mundo.regiao
        v=regiao.grafo.vertices[codigo]
        self.destino.set(v.nome)
        rota=j.rota(codigo)
        self.rota=rota["vertices"]
        texto=f"{codigo} · {NOMES_LOCAIS[v.tipo]}\nMenor tempo de viagem: {rota['tempo']}"
        for g in regiao.ginasios:
            if g.vertice==codigo:
                a=j.mundo.atores['L-'+g.codigo]
                presente=a.posicao==codigo and len(a.treinador.conscientes)>=3
                texto+=f"\nLíder: {g.lider} · "+("disponível" if presente else "fora / em recuperação")
                texto+=f"\nInsígnia: {g.insignia}"+(" · obtida" if g.insignia in j.jogador.insignias else "")
                if g.movel:
                    texto+=f"\nRetorno a cada {g.periodo}; permanece {g.permanencia}."
                break
        self.informacao.set(texto)
        self.atualizar_botoes()
        self.desenhar()

    def atualizar_botoes(self):
        j=self.app.jogo
        ativo=not(j.expirado or j.inscrito or j.jogador.pendente or self.app.ocupado)
        vizinhos={v for v,_ in j.mundo.regiao.grafo.adj[j.jogador.posicao]}
        habilitar(self.btn_passo,ativo and len(self.rota)>1)
        habilitar(self.btn_viajar,ativo and self.selecionado!=j.jogador.posicao)
        codigo=self.alvo()
        a=next((a for a in self._atores if a.codigo==codigo),None)
        protegido=j.mundo.regiao.grafo.vertices[j.jogador.posicao].tipo in {'pmc','laboratorio'}
        selvagem=bool(a and a.tipo=='selvagem')
        tem_trio=len(j.jogador.conscientes)>=3
        exige_trio=bool(a and not selvagem)
        ginasio_atual=next(
            (g for g in j.mundo.regiao.ginasios
            if g.vertice==j.jogador.posicao),
            None
        )
        lider_fora=False
        lider_ginasio=None
        if ginasio_atual and ginasio_atual.insignia not in j.jogador.insignias:
            lider_ginasio=j.mundo.atores.get(f"L-{ginasio_atual.codigo}")
            lider_fora=not (
                lider_ginasio
                and lider_ginasio.posicao==j.jogador.posicao
            )
        if protegido and a is not None:
            self.aviso_batalha.set(
                "Esta é uma área segura. Não é permitido batalhar no Laboratório ou em Centros Médicos."
            )
        elif lider_fora:
            self.aviso_batalha.set(
                f"O líder {ginasio_atual.lider} não está no ginásio neste momento. "
                "Espere até ele retornar."
            )
        elif exige_trio and not tem_trio:
            self.aviso_batalha.set(
                f"Você tem {len(j.jogador.conscientes)} Pokémon consciente(s). "
                "É preciso ter pelo menos 3 para batalhar contra outro Treinador."
            )
        else:
            self.aviso_batalha.set("")
        self.btn_batalha.configure(text="Capturar" if selvagem else "Desafiar")
        habilitar(self.btn_batalha,ativo and a is not None and not protegido)
        habilitar(self.btn_defender,ativo and a is not None and not selvagem and not protegido)
        if a is not None and not selvagem and len(j.jogador.conscientes)<3:
            self.btn_batalha.configure(state="disabled")
            self.btn_defender.configure(state="disabled")
        habilitar(self.btn_coletar,ativo and bool(self._itens))
        habilitar(self.btn_esperar,ativo)
        habilitar(self.btn_planejar,not self.app.ocupado)
        habilitar(self.btn_curar,not(j.expirado or j.inscrito or self.app.ocupado) and
                  j.mundo.regiao.grafo.vertices[j.jogador.posicao].tipo=='pmc')
        habilitar(self.btn_inscrever,not(j.expirado or j.inscrito or self.app.ocupado) and
                  len(j.jogador.insignias)>=8 and j.jogador.posicao==j.mundo.regiao.estadio)

    def selecionar_ator(self,event=None):
        self.atualizar_botoes()
        self.after(50,self.limpar_selecao_ator)

    def limpar_selecao_ator(self):
        self.atores.selection_clear()
        self.canvas.focus_force()

    def selecionar_item(self,event=None):
        self.after(50,self.limpar_selecao_item)

    def limpar_selecao_item(self):
        self.itens.selection_clear()
        self.canvas.focus_force()

    def alvo(self):
        i=self.atores.current()
        return self._atores[i].codigo if 0<=i<len(self._atores) else None

    def batalhar(self,defender=False):
        codigo=self.alvo()
        if codigo:
            self.app.iniciar_combate(codigo,como_desafiado=defender)

    def coletar(self):
        i=self.itens.current()
        if 0<=i<len(self._itens):
            item=self._itens[i]
            self.app.acao(lambda:self.app.jogo.coletar(item.codigo),
                          "Ovo colocado na incubadora." if item.tipo=="ovo" else "Erva utilizada nos Pokémon conscientes.")

    def inscrever(self):
        resultado=self.app.acao(
            self.app.jogo.inscrever,
            "Inscrição realizada! Você se classificou para a Liga."
        )
        if resultado and resultado.get("inscrito"):
            self.app.tela_final()

    def um_passo(self):
        if len(self.rota)>1:
            proximo=self.rota[1]
            self.app.acao(lambda:self.app.jogo.mover(proximo),"Estrada percorrida.")

    def viajar(self):
        self.app.acao(lambda:self.app.jogo.viajar(self.selecionado),"Viagem concluída.")

    def desenhar(self):
        if self.app.jogo is None or not self.canvas.winfo_exists():
            return
        regiao=self.app.jogo.mundo.regiao
        desenho=regiao.dados_originais.get('desenho',{})
        posicoes=desenho.get('posicoes',{})
        if not posicoes:
            vertices=list(regiao.grafo.adj)
            posicoes={v:(500+350*cos(2*pi*i/len(vertices)),400+300*sin(2*pi*i/len(vertices))) for i,v in enumerate(vertices)}
        desvios=desenho.get('desvios',{})
        pontos=list(posicoes.values())+[p for ps in desvios.values() for p in ps]
        largura=max(300,self.canvas.winfo_width())
        altura=max(250,self.canvas.winfo_height())
        limite_x=max(x for x,y in pontos)+85
        limite_y=max(y for x,y in pontos)+55
        escala=min((largura-28)/limite_x,(altura-28)/limite_y)
        ox=(largura-limite_x*escala)/2
        oy=(altura-limite_y*escala)/2
        transformar=lambda p:(ox+p[0]*escala,oy+p[1]*escala)
        self.centros={v:transformar(p) for v,p in posicoes.items()}
        bw,bh=150*escala,62*escala
        caixas=[(x-bw/2,y-bh/2,x+bw/2,y+bh/2) for x,y in self.centros.values()]
        c=self.canvas
        c.delete('all')
        rotas={frozenset((u,v)) for u,v in zip(self.rota,self.rota[1:])}
        self.arestas_desenhadas=[]
        self.rotulos_pesos=[]
        ocupados=[]
        rotulos=[]
        for u,v,peso in regiao.grafo.arestas:
            chave=f'{u}|{v}'
            meio=desvios.get(chave)
            if meio is None:
                meio=list(reversed(desvios.get(f'{v}|{u}',[])))
            if u==v and not meio:
                x,y=posicoes[u]
                meio=[(x+120,y),(x+120,y-65),(x,y-65)]
            caminho=[self.centros[u]]+[transformar(p) for p in meio]+[self.centros[v]]
            xy=[valor for p in caminho for valor in p]
            destaque=frozenset((u,v)) in rotas
            c.create_line(*xy,fill='#8bbad1' if destaque else '#d8e0e8',width=7,joinstyle='round')
            item=c.create_line(*xy,fill=CORES['azul'] if destaque else '#9aaebb',width=2,joinstyle='round')
            self.arestas_desenhadas.append((u,v,peso,item))
            segmentos=sorted(zip(caminho,caminho[1:]),key=lambda ps:hypot(ps[1][0]-ps[0][0],ps[1][1]-ps[0][1]),reverse=True)
            x,y=caminho[0]
            achou=False
            for p,q in segmentos:
                for f in (.5,.35,.65,.22,.78):
                    x,y=p[0]+f*(q[0]-p[0]),p[1]+f*(q[1]-p[1])
                    livre=all(not(a-18<x<d+18 and b-14<y<e+14) for a,b,d,e in caixas)
                    if livre and all(abs(x-a)>34 or abs(y-b)>25 for a,b in ocupados):
                        achou=True
                        break
                if achou:
                    break
            ocupados.append((x,y))
            rotulos.append((x,y,peso))
        for x,y,peso in rotulos:
            texto=c.create_text(x,y,text=str(peso),fill=CORES['texto'],font=fonte(10,'bold'))
            box=c.bbox(texto)
            fundo=c.create_rectangle(box[0]-5,box[1]-3,box[2]+5,box[3]+3,fill='white',outline='#cbd6df')
            c.tag_raise(texto,fundo)
            self.rotulos_pesos.append(texto)
        paleta={'laboratorio':'#dce9fb','pmc':'#d6eee6','ginasio':'#ebe1f6','estadio':'#f7e4b5','comum':'#e7edf3'}
        gyms={g.vertice:g for g in regiao.ginasios}
        for codigo,v in regiao.grafo.vertices.items():
            x,y=self.centros[codigo]
            atual=codigo==self.app.jogo.jogador.posicao
            ganhou=codigo in gyms and gyms[codigo].insignia in self.app.jogo.jogador.insignias
            cor='#d18122' if atual else CORES['verde'] if ganhou else CORES['azul'] if codigo==self.selecionado else '#7e91a5'
            tag='local:'+codigo
            c.create_rectangle(x-bw/2,y-bh/2,x+bw/2,y+bh/2,fill=paleta[v.tipo],outline=cor,width=3 if atual or codigo==self.selecionado else 2,tags=(tag,))
            legenda=gyms[codigo].insignia if codigo in gyms else {'laboratorio':'Laboratório','pmc':'C. médico','estadio':'Liga Pokémon'}.get(v.tipo,v.nome.replace(' dos Caminhos','').replace(' das Sementes','').replace(' da Travessia',''))
            c.create_text(x,y-9*escala,text=codigo+(' · você' if atual else ' · OK' if ganhou else ''),font=fonte(max(8,int(12*escala)),'bold'),fill=CORES['texto'],tags=(tag,))
            c.create_text(x,y+14*escala,text=legenda,width=bw-8,font=fonte(max(8,int(10*escala))),fill=CORES['suave'],tags=(tag,))
            c.tag_bind(tag,'<Button-1>',lambda e,codigo=codigo:self.selecionar(codigo))
            c.tag_bind(tag,'<Enter>',lambda e:c.configure(cursor='hand2'))
            c.tag_bind(tag,'<Leave>',lambda e:c.configure(cursor=''))
