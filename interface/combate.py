"""Janela de combate e estratégia humana. O dano e as regras ficam no núcleo."""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from nucleo.batalha import EstrategiaAutomatica, SolicitarDesistencia
from interface.componentes import CORES, tipos_texto, habilitar, fonte, centralizar_janela


class JanelaCombate(tk.Toplevel, EstrategiaAutomatica):
    def __init__(self,app,titulo,lado_jogador=0,captura=False,automatico=False,bonus_treinadores=None):
        tk.Toplevel.__init__(self,app.raiz)
        self.app=app
        self.lado_jogador=lado_jogador
        self.captura=captura
        self.pode_desistir=captura or lado_jogador==1
        self.bonus_treinadores=bonus_treinadores or (0,0)
        self.em_andamento=True
        self.esperando=False
        self.pedido_sair=False
        self.ativos={}
        self.pokemons={p.codigo:p for p in app.jogo.mundo._pokemons_existentes()}
        self.automatico=tk.BooleanVar(master=self,value=automatico)
        self.escolha=tk.StringVar(master=self)
        self.resultado=None
        self.title(titulo)
        self.geometry('990x740')
        self.minsize(780,650)
        self.transient(app.raiz)
        self.protocol('WM_DELETE_WINDOW',self.fechar)
        self.configure(background=CORES['fundo'])
        self.columnconfigure(0,weight=1)
        self.rowconfigure(2,weight=1)
        cabecalho=ttk.Frame(self,padding=(18,14))
        cabecalho.grid(row=0,column=0,sticky='ew')
        ttk.Label(cabecalho,text=titulo,style='Subtitulo.TLabel').pack(side='left')
        ttk.Checkbutton(cabecalho,text='Escolhas automáticas',variable=self.automatico,
                        command=self.alternar_automatico).pack(side='right')
        cards=ttk.Frame(self,padding=(18,0,18,10))
        cards.grid(row=1,column=0,sticky='ew')
        cards.columnconfigure((0,1),weight=1)
        self.cards={}
        for lado in (0,1):
            posicao=0 if lado==lado_jogador else 1
            rotulo='Seu Pokémon' if lado==lado_jogador else ('Selvagem' if captura else 'Oponente')
            frame=ttk.LabelFrame(cards,text=rotulo,padding=12)
            frame.grid(row=0,column=posicao,sticky='ew',padx=(0,8) if posicao==0 else (8,0))
            nome=tk.StringVar(master=self,value='Aguardando escolha')
            dados=tk.StringVar(master=self,value='')
            ttk.Label(frame,textvariable=nome,style='Subtitulo.TLabel').pack(anchor='w')
            ttk.Label(frame,textvariable=dados,wraplength=400).pack(anchor='w',pady=(6,7))
            barra=ttk.Progressbar(frame,maximum=100,value=0)
            barra.pack(fill='x')
            self.cards[lado]=(nome,dados,barra)
        self.log=ScrolledText(self,height=12,wrap='word',state='disabled',font=fonte(),
                              background='white',foreground=CORES['texto'],borderwidth=1,relief='solid')
        self.log.grid(row=2,column=0,sticky='nsew',padx=18,pady=(0,10))
        self.instrucao=tk.StringVar(master=self,value='Preparando os combatentes...')
        ttk.Label(self,textvariable=self.instrucao,style='Subtitulo.TLabel',wraplength=900).grid(row=3,column=0,sticky='w',padx=18,pady=(0,6))
        self.opcoes=ttk.Frame(self,padding=(18,0,18,8))
        self.opcoes.grid(row=4,column=0,sticky='ew')
        self.opcoes.columnconfigure((0,1),weight=1)
        rodape=ttk.Frame(self,padding=(18,6,18,16))
        rodape.grid(row=5,column=0,sticky='ew')
        self.aviso=ttk.Label(rodape,wraplength=620,style='Suave.TLabel',text=
            'Você pode abandonar esta captura.' if captura else
            'Você é o desafiado: começa atacando e pode desistir.' if lado_jogador==1 else
            'O desafiado ataca primeiro. Como desafiante, você não pode abandonar o duelo.')
        self.aviso.pack(side='left',fill='x',expand=True)
        self.btn_sair=ttk.Button(rodape,text='Abandonar captura' if captura else 'Desistir',command=self.solicitar_saida)
        if self.pode_desistir:
            self.btn_sair.pack(side='right',padx=(8,0))
        self.btn_voltar=ttk.Button(rodape,text='Voltar ao jogo',style='Principal.TButton',command=self.fechar)
        habilitar(self.btn_voltar,False)
        self.btn_voltar.pack(side='right')
        centralizar_janela(self, app.raiz, 990, 740)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.escrever('Os turnos pertencem a uma única batalha: ao final, o relógio avança 1 unidade.')

    def escrever(self,texto):
        self.log.configure(state='normal')
        self.log.insert('end',texto+'\n')
        self.log.see('end')
        self.log.configure(state='disabled')
        self.update_idletasks()

    def atualizar_cards(self):
        for lado,codigo in self.ativos.items():
            p=self.pokemons[codigo]
            nome,dados,barra=self.cards[lado]
            nome.set(p.nome+f' · {p.codigo}')
            bonus=self.bonus_treinadores[lado]
            dados.set(f'{tipos_texto(p.tipos)} · XP {p.xp}\nHP {p.hp:.1f}/100 · AP {p.ap+bonus:.1f} · DP {p.dp+bonus:.1f}\nAP/DP incluem +{bonus} do treinador.')
            barra.configure(value=p.hp)

    def observar(self,evento):
        if 'entrada' in evento:
            self.ativos[evento['lado']]=evento['entrada']
            self.escrever(f"{evento['nome']} entrou em combate.")
        elif 'golpe' in evento:
            extra=' Esquivou!' if evento['esquiva'] else ' Crítico!' if evento['critico'] else ''
            self.escrever(f"T{evento['turno']} · {evento['nome_atacante']} usou {evento['golpe']} "
                          f"contra {evento['nome_defensor']}: {evento['dano']:g} de dano "
                          f"(tipos {evento['multiplicador']:g}×). HP restante: {evento['hp']:g}.{extra}")
        elif 'nocaute' in evento:
            p=self.pokemons[evento['nocaute']]
            self.escrever(f'{p.nome} ficou inconsciente. '+('Precisa de PMC.' if p.grave else 'Precisa repousar.'))
            for nome in evento.get('evolucoes',[]):
                self.escrever('Evolução: '+nome+'!')
        self.atualizar_cards()

    def aguardar_escolha(self,instrucao,opcoes,automatico):
        if self.pedido_sair:
            raise SolicitarDesistencia()
        if self.automatico.get():
            return automatico()
        for filho in self.opcoes.winfo_children():
            filho.destroy()
        self.instrucao.set(instrucao)
        self.escolha.set('')
        self.botoes_escolha=[]
        for i,(texto,objeto) in enumerate(opcoes):
            botao=ttk.Button(self.opcoes,text=texto,command=lambda i=i:self.escolha.set(str(i)))
            botao.grid(row=i//2,column=i%2,sticky='ew',padx=(0,8) if i%2==0 else (8,0),pady=4)
            self.botoes_escolha.append(botao)
        self.esperando=True
        self.wait_variable(self.escolha)
        self.esperando=False
        valor=self.escolha.get()
        for filho in self.opcoes.winfo_children():
            filho.destroy()
        if valor=='sair':
            raise SolicitarDesistencia()
        if valor=='automatico':
            return automatico()
        return opcoes[int(valor)][1]

    def escolher_pokemon(self,opcoes,contexto):
        if len(opcoes)==1:
            return opcoes[0]
        return self.aguardar_escolha(f'Escolha seu Pokémon para {contexto}:',
            [(f'{p.nome} · HP {p.hp:.1f} · {tipos_texto(p.tipos)}',p) for p in opcoes],
            lambda:EstrategiaAutomatica.escolher_pokemon(self,opcoes,contexto))

    def escolher_ataque(self,atacante,defensor,tabela):
        self.atualizar_cards()
        return self.aguardar_escolha(f'{atacante.nome}: escolha um ataque contra {defensor.nome}',
            [(f'{a.nome} · {tipos_texto((a.tipo,))} · {tabela.multiplicador(a.tipo,defensor.tipos):g}×',a)
             for a in atacante.ataques],
            lambda:EstrategiaAutomatica.escolher_ataque(self,atacante,defensor,tabela))

    def desistir(self,turno,captura=False):
        return self.pedido_sair and self.pode_desistir

    def solicitar_saida(self):
        if not self.pode_desistir or not self.em_andamento:
            return
        self.pedido_sair=True
        if self.esperando:
            self.escolha.set('sair')

    def alternar_automatico(self):
        if self.automatico.get() and self.esperando:
            self.escolha.set('automatico')

    def finalizar(self,resultado):
        self.resultado=resultado
        self.em_andamento=False
        self.atualizar_cards()
        for filho in self.opcoes.winfo_children():
            filho.destroy()
        if 'erro' in resultado:
            texto=resultado['erro']
        elif resultado.get('aceitou') is False:
            texto='O treinador recusou o desafio. Não houve batalha nem gasto de tempo.'
        elif 'capturado' in resultado:
            texto=('Captura bem-sucedida: '+resultado['pokemon']['nome']+'!') if resultado['capturado'] else (
                'Captura abandonada: o selvagem ficará escondido até o fim da jornada.' if resultado['vencedor'] is None else 'A captura falhou: sua equipe foi derrotada.')
        elif 'venceu' in resultado:
            texto='Você venceu a batalha!' if resultado['venceu'] else 'Você perdeu a batalha.'
        else:
            texto='Treinamento concluído. A experiência dos Pokémon foi atualizada.'
        if resultado.get('insignia'):
            texto+=' Insígnia recebida: '+resultado['insignia']+'.'
        if resultado.get('pokemon_roubado'):
            texto+=' A Rocket roubou '+resultado['pokemon_roubado']+' e fugiu temporariamente!'
        if resultado.get('recuperados_no_laboratorio'):
            texto+=' Os Pokémon recuperados estão com o professor.'
        if resultado.get('motivo','').startswith('desistencia_do_desafiado_'):
            texto+=' O desafiado concedeu pelo limite de segurança; nenhum dano foi inventado.'
        if resultado.get('destino')=='selecao_pendente':
            texto+=' Na equipe, escolha quem enviar ao professor.'
        self.instrucao.set(texto)
        self.escrever(texto)
        habilitar(self.btn_sair,False)
        habilitar(self.btn_voltar,True)
        self.aviso.configure(text=f'Tempo da jornada: {self.app.jogo.mundo.agora}. Feche esta janela para continuar.')
        self.btn_voltar.focus_set()

    def fechar(self):
        if self.em_andamento:
            if self.pode_desistir:
                self.solicitar_saida()
            else:
                self.automatico.set(True)
                self.alternar_automatico()
                self.aviso.configure(text='O desafiante não pode abandonar. A batalha será concluída automaticamente.')
            return
        self.grab_release()
        self.destroy()
        self.app.combate=None
        self.app.ocupado=False
        self.app.atualizar()
