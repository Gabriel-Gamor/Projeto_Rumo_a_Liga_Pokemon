"""Janela principal, início da partida e ligação dos botões aos casos de uso."""

from pathlib import Path
from random import SystemRandom
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from nucleo.erros import ErroProjeto
from nucleo.regiao import carregar_regiao
from nucleo.salvamento import salvar, carregar
from nucleo.jogo import Jogo
from interface.componentes import (CORES, configurar_estilo, escolher_grupo, habilitar, fonte,
                                   centralizar_janela)
from interface.mapa import TelaMapa
from interface.equipe import TelaEquipe
from interface.inventario import TelaInventario
from interface.tipos import TelaTipos
from interface.combate import JanelaCombate

RAIZ=Path(__file__).resolve().parents[1]

PASTA_SAVES=RAIZ/'Saves'
PASTA_SAVES.mkdir(parents=True,exist_ok=True)


class Aplicacao:
    def __init__(self,raiz,jogo=None):
        self.raiz=raiz
        self.jogo=jogo
        self.ocupado=False
        self.combate=None
        self.arquivo_partida=None
        self.raiz.title('Rumo à Liga Pokémon')
        largura=min(1280,max(1000,raiz.winfo_screenwidth()-70))
        altura=min(830,max(680,raiz.winfo_screenheight()-100))
        self.raiz.geometry(f'{largura}x{altura}')
        self.raiz.minsize(1000,680)
        self.raiz.protocol('WM_DELETE_WINDOW',self.fechar)
        configurar_estilo(raiz)
        self.conteudo=ttk.Frame(raiz)
        self.conteudo.pack(fill='both',expand=True)
        self.mensagem=tk.StringVar(master=raiz)
        self.mostrar_npcs=tk.BooleanVar(master=raiz,value=False)
        if jogo:
            self.montar_jogo()
        else:
            self.abertura()

    def limpar(self):
        for filho in self.conteudo.winfo_children():
            filho.destroy()

    def abertura(self):
        if self.ocupado:
            return
        self.limpar()
        self.conteudo.columnconfigure(0,weight=1)
        self.conteudo.rowconfigure(0,weight=1)
        for linha in (1,2,3):
            self.conteudo.rowconfigure(linha,weight=0)
        painel=ttk.Frame(self.conteudo,padding=30)
        painel.grid(row=0,column=0)
        painel.columnconfigure(0,weight=1)
        ttk.Label(painel,text='Rumo à Liga Pokémon',style='Titulo.TLabel').grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(painel,text='Viaje pelo mapa, conquiste oito insígnias e chegue ao estádio a tempo.',style='Suave.TLabel').grid(row=1,column=0,columnspan=2,sticky='w',pady=(7,24))
        ttk.Label(painel,text='Nome do treinador').grid(row=2,column=0,sticky='w')
        self.nome=tk.StringVar(master=self.raiz,value='Treinador')
        ttk.Entry(painel,textvariable=self.nome,width=54).grid(row=3,column=0,columnspan=2,sticky='ew',pady=(5,14))
        ttk.Label(painel,text='Arquivo texto da região (JSON)').grid(row=4,column=0,sticky='w')
        self.caminho_regiao=tk.StringVar(master=self.raiz,value=str(RAIZ/'dados/regiao.json'))
        ttk.Entry(painel,textvariable=self.caminho_regiao,width=58).grid(row=5,column=0,sticky='ew',pady=(5,14),padx=(0,8))
        ttk.Button(painel,text='Procurar...',command=self.escolher_regiao).grid(row=5,column=1,pady=(5,14))
        ttk.Label(painel,text='Semente da distribuição aleatória').grid(row=6,column=0,sticky='w')
        semente_frame=ttk.Frame(painel)
        semente_frame.grid(row=7,column=0,columnspan=2,sticky='ew',pady=(5,14))
        self.semente=tk.StringVar(master=self.raiz,value='3')
        ttk.Entry(semente_frame,textvariable=self.semente,width=17).pack(side='left')
        ttk.Button(semente_frame,text='Sortear',command=lambda:self.semente.set(str(SystemRandom().randrange(2**31)))).pack(side='left',padx=8)
        ttk.Label(semente_frame,text='O mesmo valor repete a distribuição inicial.',style='Suave.TLabel').pack(side='left')
        iniciais=ttk.LabelFrame(painel,text='Oferta do Professor Carvalho',padding=12)
        iniciais.grid(row=8,column=0,columnspan=2,sticky='ew',pady=(0,16))
        self.iniciais=tk.StringVar(master=self.raiz,value='trio')
        ttk.Radiobutton(iniciais,text='Aceitar o trio: água, fogo e planta',variable=self.iniciais,value='trio').pack(anchor='w',pady=4)
        ttk.Radiobutton(iniciais,text='Recusar o trio e receber apenas um Pokémon aleatório',variable=self.iniciais,value='aleatorio').pack(anchor='w',pady=4)
        ttk.Label(painel,text='Todos começam na primeira fase. Você recebe uma incubadora e sete pokébolas.',style='Suave.TLabel').grid(row=9,column=0,columnspan=2,sticky='w')
        botoes=ttk.Frame(painel)
        botoes.grid(row=10,column=0,columnspan=2,sticky='ew',pady=(22,8))
        self.btn_iniciar=ttk.Button(botoes,text='Iniciar jornada',style='Principal.TButton',command=self.iniciar)
        self.btn_iniciar.pack(side='left')
        ttk.Button(botoes,text='Carregar partida',command=self.carregar_partida).pack(side='left',padx=8)
        if self.jogo:
            ttk.Button(botoes,text='Voltar à partida atual',command=self.montar_jogo).pack(side='left')
        self.aviso=ttk.Label(painel,textvariable=self.mensagem,wraplength=690,style='Erro.TLabel')
        self.aviso.grid(row=11,column=0,columnspan=2,sticky='w',pady=10)
        self.mensagem.set('Iniciar outra jornada substitui a sessão atual; arquivos salvos não serão apagados.' if self.jogo else '')

    def escolher_regiao(self):
        caminho=filedialog.askopenfilename(parent=self.raiz,title='Abrir arquivo da região',filetypes=[('Região JSON','*.json'),('Arquivos texto','*.txt'),('Todos os arquivos','*')])
        if caminho:
            self.caminho_regiao.set(caminho)

    def iniciar(self):
        try:
            nome=self.nome.get().strip()
            if not nome:
                raise ValueError('Informe o nome do treinador.')
            regiao=carregar_regiao(self.caminho_regiao.get())
            semente=int(self.semente.get())
            jogo=Jogo(regiao,semente,nome,self.iniciais.get())
        except (ErroProjeto,ValueError,OSError) as e:
            self.mensagem.set(str(e))
            return
        self.jogo=jogo
        self.arquivo_partida=None
        self.montar_jogo()
        self.notificar('Jornada iniciada! Clique em uma região do mapa para escolher sua viagem.')

    def montar_jogo(self):
        self.prazo_popup_mostrado=False
        self.limpar()
        # O conteúdo usa somente grid para que redimensionar a janela seja estável.
        self.conteudo.columnconfigure(0,weight=1)
        self.conteudo.rowconfigure(0,weight=0)
        self.conteudo.rowconfigure(1,weight=0)
        self.conteudo.rowconfigure(2,weight=1)
        topo=ttk.Frame(self.conteudo,padding=(18,12,18,5))
        topo.grid(row=0,column=0,sticky='ew')
        ttk.Label(topo,text='Rumo à Liga Pokémon',style='Titulo.TLabel').pack(side='left')
        self.btn_novo=ttk.Button(topo,text='Nova jornada',command=self.abertura)
        self.btn_novo.pack(side='right',padx=(7,0))
        self.btn_carregar=ttk.Button(topo,text='Carregar',command=self.carregar_partida)
        self.btn_carregar.pack(side='right',padx=(7,0))
        self.btn_salvar=ttk.Button(topo,text='Salvar partida',command=self.salvar_partida)
        self.btn_salvar.pack(side='right')
        status=ttk.Frame(self.conteudo,padding=(18,3,18,8))
        status.grid(row=1,column=0,sticky='ew')
        self.cabecalho=tk.StringVar(master=self.raiz)
        ttk.Label(status,textvariable=self.cabecalho).pack(side='left')
        self.barra_prazo=ttk.Progressbar(status,maximum=100,length=170)
        self.barra_prazo.pack(side='right',padx=(15,0))
        self.abas=ttk.Notebook(self.conteudo)
        self.abas.grid(row=2,column=0,sticky='nsew',padx=10)
        self.mapa=TelaMapa(self.abas,self)
        self.equipe=TelaEquipe(self.abas,self)
        self.inventario=TelaInventario(self.abas,self)
        self.tipos=TelaTipos(self.abas,self)
        self.registro=ttk.Frame(self.abas,padding=14)
        self.abas.add(self.mapa,text='Mapa e viagem')
        self.abas.add(self.equipe,text='Minha equipe')
        self.abas.add(self.inventario,text='Inventário')
        self.abas.add(self.tipos,text='Tabela de tipos')
        self.abas.add(self.registro,text='Registro da jornada')
        ttk.Checkbutton(self.registro,text='Incluir movimentação dos NPCs',variable=self.mostrar_npcs,command=self.atualizar_registro).pack(anchor='w',pady=(0,8))
        self.log=ScrolledText(self.registro,state='disabled',font=fonte(),wrap='word',background='white',foreground=CORES['texto'])
        self.log.pack(fill='both',expand=True)
        self.aviso=ttk.Label(self.conteudo,textvariable=self.mensagem,wraplength=1210,padding=(18,9),style='Suave.TLabel')
        self.aviso.grid(row=3,column=0,sticky='ew')
        self.notificar('Escolha um local no mapa. Não há passagem de tempo enquanto você consulta as telas.')
        self.atualizar()

    def notificar(self,texto,erro=False):
        self.mensagem.set(texto)
        if hasattr(self,'aviso') and self.aviso.winfo_exists():
            self.aviso.configure(style='Erro.TLabel' if erro else 'Suave.TLabel')

    def atualizar(self):
        if self.jogo is None or not hasattr(self,'abas') or not self.abas.winfo_exists():
            return
        j,m=self.jogo.jogador,self.jogo.mundo
        self.cabecalho.set(f'{j.nome} · XP {j.xp}    |    Tempo {m.agora}/{m.regiao.prazo}    |    Insígnias {len(j.insignias)}/8    |    Distância {m.distancia_percorrida}')
        self.barra_prazo.configure(value=min(100,100*m.agora/m.regiao.prazo))
        self.mapa.atualizar()
        self.equipe.atualizar()
        self.inventario.atualizar()
        self.tipos.atualizar()
        self.atualizar_registro()
        for b in (self.btn_salvar,self.btn_carregar,self.btn_novo):
            habilitar(b,not self.ocupado)
        if j.pendente and not self.ocupado:
            self.abas.select(self.equipe)
            self.notificar('Há um Pokémon na sétima posição. Escolha quem enviar ao professor para continuar.')
        elif self.jogo.inscrito:
            self.notificar('Inscrição concluída! Você conquistou oito insígnias e chegou ao estádio dentro do prazo.')
        elif self.jogo.expirado:
            self.notificar('O prazo terminou sem inscrição. Você está inapto para esta edição da Liga.',True)
            self.tela_prazo_encerrado()

    def acao(self,funcao,mensagem):
        if self.ocupado:
            return None
        try:
            resultado=funcao()
        except (ErroProjeto,ValueError,OSError) as e:
            self.notificar(str(e),True)
            return None
        if isinstance(resultado,dict) and resultado.get('chegou') is False:
            mensagem='Viagem interrompida no próximo vértice: confira a equipe ou o prazo.'
        if isinstance(resultado,dict) and 'tempos_individuais' in resultado:
            mensagem=f"Tratamento concluído em {resultado['duracao']} unidades, sem fila. HP restaurado."
        self.notificar(mensagem)
        self.atualizar()
        return resultado

    def salvar_partida(self):
        if self.ocupado or self.jogo is None:
            return
        caminho=filedialog.asksaveasfilename(parent=self.raiz,title='Salvar partida',initialdir=str(PASTA_SAVES),initialfile='partida.json',
                                    defaultextension='.json',filetypes=[('Partida JSON','*.json')])
        if not caminho:
            return
        try:
            salvar(self.jogo,caminho)
        except (OSError,ValueError) as e:
            self.notificar('Não foi possível salvar: '+str(e),True)
            return
        self.arquivo_partida=caminho
        self.notificar('Partida salva em '+str(caminho))

    def carregar_partida(self):
        if self.ocupado:
            return
        caminho=filedialog.askopenfilename(parent=self.raiz,title='Carregar partida salva',initialdir=str(PASTA_SAVES),filetypes=[('Partida JSON','*.json'),('Todos os arquivos','*')])
        if not caminho:
            return
        try:
            jogo=carregar(caminho)
        except (ErroProjeto,OSError,ValueError) as e:
            self.notificar(str(e),True)
            return
        self.jogo=jogo
        self.arquivo_partida=caminho
        self.montar_jogo()
        self.notificar('Partida retomada com relógio, equipe, NPCs e aleatoriedade preservados.')

    def iniciar_combate(self,codigo,como_desafiado=False,automatico=False,trio=None):
        if self.ocupado:
            return None
        try:
            self.jogo._local_batalha()
            ator=self.jogo._encontrar_ator(codigo,{'selvagem','treinador','lider','rocket'})
            captura=ator.tipo=='selvagem'
            if captura:
                if not self.jogo.jogador.conscientes:
                    raise ValueError('Você precisa de um Pokémon consciente para capturar.')
            else:
                disponiveis=self.jogo.jogador.conscientes
                if len(disponiveis)>3 and trio is None and not automatico:
                    trio=escolher_grupo(self.raiz,disponiveis,3,'Escolha o trio para a batalha')
                    if trio is None:
                        return None
                self.jogo.jogador.escolher_trio(trio)
                ator.treinador.escolher_trio()
        except (ErroProjeto,ValueError) as e:
            self.notificar(str(e),True)
            return None
        titulo='Capturar '+ator.pokemon.nome if captura else 'Batalha contra '+ator.treinador.nome
        bonus=(self.jogo.jogador.xp,ator.treinador.xp if ator.treinador else 0)
        if como_desafiado and not captura:
            bonus=tuple(reversed(bonus))
        janela=JanelaCombate(self,titulo,1 if como_desafiado and not captura else 0,captura,automatico,bonus)
        self.combate=janela
        self.ocupado=True
        self.atualizar()
        try:
            if captura:
                resultado=self.jogo.capturar(codigo,estrategia=janela,observador=janela.observar)
            else:
                resultado=self.jogo.desafiar(codigo,trio=trio,estrategia=janela,
                                             como_desafiado=como_desafiado,observador=janela.observar)
        except (ErroProjeto,ValueError) as e:
            resultado={'erro':str(e)}
        janela.finalizar(resultado)
        self.atualizar()
        return resultado

    def treinar(self,ids=None,automatico=False):
        if self.ocupado:
            return
        disponiveis=self.jogo.jogador.conscientes
        if len(disponiveis)<2:
            self.notificar('Treinamento exige dois Pokémon conscientes.',True)
            return
        if ids is None:
            ids=escolher_grupo(self.raiz,disponiveis,2,'Escolha dois Pokémon para treinar')
        if not ids:
            return
        janela=JanelaCombate(self,'Treinamento da equipe',automatico=automatico,
                            bonus_treinadores=(self.jogo.jogador.xp,self.jogo.jogador.xp))
        self.combate=janela
        self.ocupado=True
        self.atualizar()
        try:
            resultado=self.jogo.treinar(*ids,estrategia=janela,observador=janela.observar)
        except (ErroProjeto,ValueError) as e:
            resultado={'erro':str(e)}
        janela.finalizar(resultado)
        self.atualizar()
        return resultado

    def planejar(self):
        if self.ocupado:
            return
        try:
            plano=self.jogo.plano()
        except ErroProjeto as e:
            self.notificar(str(e),True)
            return
        popup=tk.Toplevel(self.raiz)
        popup.withdraw()
        popup.title('Planejamento da jornada')
        popup.transient(self.raiz)
        corpo=ttk.Frame(popup,padding=22)
        corpo.pack(fill='both',expand=True)
        ttk.Label(corpo,text='Ordem sugerida de ginásios',style='Subtitulo.TLabel').pack(anchor='w')
        ordem=' → '.join(plano['ginasios']) or 'Oito insígnias obtidas: vá ao estádio.'
        ttk.Label(corpo,text=ordem,wraplength=650).pack(anchor='w',pady=12)
        ttk.Label(corpo,text=f"Menor tempo logístico: {plano['tempo_minimo']}\nChegada otimista: {plano['chegada_otimista']} / prazo {self.jogo.mundo.regiao.prazo}").pack(anchor='w')
        ttk.Label(corpo,text='Este cálculo considera viagens e uma vitória por ginásio. Não prevê curas, derrotas ou a ausência de líderes móveis.',wraplength=650,style='Aviso.TLabel').pack(anchor='w',pady=12)
        def selecionar():
            destino=self.jogo.mundo.ginasios[plano['ginasios'][0]].vertice if plano['ginasios'] else self.jogo.mundo.regiao.estadio
            self.mapa.mostrar_planejamento(plano['vertices'],destino)
            self.abas.select(self.mapa)
            popup.destroy()
        ttk.Button(corpo,text='Mostrar rota completa no mapa',command=selecionar,style='Principal.TButton').pack(anchor='e')

        # O popup começa oculto para não piscar enquanto é montado. Depois de
        # calcular o tamanho, ele é centralizado e exibido antes de receber o
        # grab. Sem o deiconify(), o grab ficava preso em uma janela invisível
        # e a aplicação aparentava travar ao clicar em "Planejar ginásios restantes".
        popup.resizable(False,False)
        centralizar_janela(popup,self.raiz)
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        popup.grab_set()

    def atualizar_registro(self):
        if not hasattr(self,'log') or not self.log.winfo_exists():
            return
        linhas=[]
        for evento in self.jogo.mundo.historico:
            tipo=evento['tipo']
            if tipo=='movimento_npc' and not self.mostrar_npcs.get():
                continue
            if tipo in {'movimento_jogador','movimento_npc'}:
                texto=f"{evento.get('ator','Você')}: {evento['origem']} → {evento['destino']}."
            elif tipo=='batalha_treinador':
                texto=f"Batalha com {evento['alvo']}: "+('vitória.' if evento['venceu'] else 'derrota.')
                if evento.get('pokemon_roubado'):
                    texto+=' Rocket roubou '+evento['pokemon_roubado']+'.'
            elif tipo=='ovo_chocou':
                texto=f"O ovo chocou! {evento['nome']} ({evento['pokemon']}) nasceu."
            elif tipo=='captura':
                texto=f"Captura de {evento['alvo']}: {evento['resultado'].replace('_',' ')}."
            elif tipo=='inscricao':
                texto='Inscrição na Liga realizada com oito insígnias distintas.'
            elif tipo=='rocket_expulsa':
                texto=f"Equipe Rocket derrotada e enviada para {evento['destino']}."
            elif tipo=='rocket_reapareceu':
                texto=f"Equipe Rocket voltou a aparecer em {evento['local']}."
            elif tipo=='inicio':
                texto=evento.get('mensagem','Jornada iniciada.')
            else:
                partes=[f'{k.replace("_"," ")}: {v}' for k,v in evento.items() if k not in {'tempo','tipo'}]
                texto=tipo.replace('_',' ').capitalize()+(' · '+'; '.join(partes) if partes else '')
            linhas.append(f"[tempo {evento['tempo']}] {texto}")
        self.log.configure(state='normal')
        self.log.delete('1.0','end')
        self.log.insert('end','\n'.join(linhas))
        self.log.see('end')
        self.log.configure(state='disabled')

    def tela_prazo_encerrado(self):
        if getattr(self,"prazo_popup_mostrado",False):
            return
        self.prazo_popup_mostrado=True
        popup=tk.Toplevel(self.raiz)
        popup.withdraw()
        popup.title("Prazo encerrado")
        popup.transient(self.raiz)
        popup.resizable(False,False)
        corpo=ttk.Frame(popup,padding=30)
        corpo.pack(fill="both",expand=True)
        j=self.jogo.jogador
        m=self.jogo.mundo
        ttk.Label(
            corpo,
            text="Prazo encerrado!",
            style="Titulo.TLabel"
        ).pack(pady=(0,12))
        ttk.Label(
            corpo,
            text="Você não conseguiu se inscrever na Liga Pokémon dentro do prazo.",
            style="Subtitulo.TLabel",
            wraplength=420,
            justify="center"
        ).pack(pady=(0,18))
        ttk.Label(
            corpo,
            text=(
                f"Treinador: {j.nome}\n"
                f"Insígnias conquistadas: {len(j.insignias)}/8\n"
                f"Tempo utilizado: {m.agora}/{m.regiao.prazo}\n"
                f"Distância percorrida: {m.distancia_percorrida}\n"
                f"XP do treinador: {j.xp}"
            ),
            justify="center"
        ).pack(pady=(0,20))
        ttk.Label(
            corpo,
            text="Você está inapto para esta edição da Liga.",
            style="Suave.TLabel"
        ).pack(pady=(0,20))
        botoes=ttk.Frame(corpo)
        botoes.pack()
        ttk.Button(
            botoes,
            text="Nova jornada",
            command=lambda:(
                popup.destroy(),
                self.abertura()
            )
        ).pack(side="left",padx=5)
        ttk.Button(
            botoes,
            text="Continuar vendo a partida",
            command=popup.destroy
        ).pack(side="left",padx=5)
        # Centraliza sobre a janela principal
        self.raiz.update_idletasks()
        popup.update_idletasks()
        largura=popup.winfo_reqwidth()
        altura=popup.winfo_reqheight()
        x=self.raiz.winfo_rootx()+(self.raiz.winfo_width()-largura)//2
        y=self.raiz.winfo_rooty()+(self.raiz.winfo_height()-altura)//2
        popup.geometry(f"{largura}x{altura}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        popup.grab_set()

    def tela_final(self):
        popup=tk.Toplevel(self.raiz)
        popup.withdraw()
        popup.title("Classificação concluída")
        popup.transient(self.raiz)
        popup.resizable(False,False)
        corpo=ttk.Frame(popup,padding=30)
        corpo.pack(fill="both",expand=True)
        j=self.jogo.jogador
        m=self.jogo.mundo
        ttk.Label(
            corpo,
            text="Parabéns!",
            style="Titulo.TLabel"
        ).pack(pady=(0,12))
        ttk.Label(
            corpo,
            text="Você se classificou para a Liga Pokémon!",
            style="Subtitulo.TLabel"
        ).pack(pady=(0,18))
        ttk.Label(
            corpo,
            text=(
                f"Treinador: {j.nome}\n"
                f"Insígnias: {len(j.insignias)}/8\n"
                f"Tempo utilizado: {m.agora}/{m.regiao.prazo}\n"
                f"Distância percorrida: {m.distancia_percorrida}\n"
                f"XP do treinador: {j.xp}"
            ),
            justify="center"
        ).pack(pady=(0,20))
        ttk.Label(
            corpo,
            text="Jornada concluída com sucesso!",
            style="Suave.TLabel"
        ).pack(pady=(0,20))
        botoes=ttk.Frame(corpo)
        botoes.pack()
        ttk.Button(
            botoes,
            text="Nova jornada",
            command=lambda:(
                popup.destroy(),
                self.abertura()
            )
        ).pack(side="left",padx=5)
        ttk.Button(
            botoes,
            text="Continuar vendo a partida",
            command=popup.destroy
        ).pack(side="left",padx=5)
        # Centraliza a janela final sobre a janela principal.
        self.raiz.update_idletasks()
        popup.update_idletasks()
        largura=popup.winfo_reqwidth()
        altura=popup.winfo_reqheight()
        x=self.raiz.winfo_rootx()+(self.raiz.winfo_width()-largura)//2
        y=self.raiz.winfo_rooty()+(self.raiz.winfo_height()-altura)//2
        popup.geometry(f"{largura}x{altura}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        popup.grab_set()

    def fechar(self):
        if self.ocupado:
            if self.combate:
                self.combate.lift()
            return
        if self.jogo and not messagebox.askokcancel('Encerrar','Encerrar a janela? Alterações desde o último salvamento serão perdidas.',parent=self.raiz):
            return
        self.raiz.destroy()
