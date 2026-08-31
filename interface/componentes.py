"""Cores, nomes legíveis e componentes pequenos compartilhados pelas telas."""

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

CORES = {"fundo":"#f2f5f8", "cartao":"#ffffff", "texto":"#20364c",
         "suave":"#5d7185", "azul":"#246b8a", "verde":"#288064",
         "aviso":"#a85c19", "erro":"#aa3544", "borda":"#d9e2eb"}
NOMES_TIPOS = {"normal":"Normal", "fogo":"Fogo", "agua":"Água", "eletrico":"Elétrico",
               "planta":"Planta", "gelo":"Gelo", "lutador":"Lutador", "venenoso":"Venenoso",
               "terra":"Terra", "voador":"Voador", "psiquico":"Psíquico", "inseto":"Inseto",
               "pedra":"Pedra", "fantasma":"Fantasma", "dragao":"Dragão", "sombrio":"Sombrio",
               "aco":"Aço", "fada":"Fada"}
NOMES_LOCAIS = {"comum":"Região", "laboratorio":"Laboratório", "pmc":"Centro médico",
                "ginasio":"Ginásio", "estadio":"Estádio da Liga"}
FAMILIA_FONTE = "Arial"


def fonte(tamanho=10, peso=None):
    """Usa uma família instalada, inclusive em sistemas sem DejaVu Sans."""
    return (FAMILIA_FONTE,tamanho,peso) if peso else (FAMILIA_FONTE,tamanho)


def tipos_texto(tipos):
    return " / ".join(NOMES_TIPOS.get(t,t) for t in tipos)


def configurar_estilo(raiz):
    global FAMILIA_FONTE
    disponiveis={nome.casefold():nome for nome in tkfont.families(raiz)}
    for nome in ('DejaVu Sans','Noto Sans','Segoe UI','Arial','Helvetica','Latin Modern Sans'):
        if nome.casefold() in disponiveis:
            FAMILIA_FONTE=disponiveis[nome.casefold()]
            break
    for nome in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
        tkfont.nametofont(nome,root=raiz).configure(family=FAMILIA_FONTE,size=10)
    raiz.configure(background=CORES["fundo"])
    estilo=ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure(".", font=fonte(), background=CORES["fundo"], foreground=CORES["texto"])
    estilo.configure("TButton", padding=(10,7))
    estilo.configure("Principal.TButton", background=CORES["azul"], foreground="white")
    estilo.map("Principal.TButton", background=[("active","#1b536b"),("disabled","#bdcbd3")],
               foreground=[("disabled","#edf2f5")])
    estilo.configure("Titulo.TLabel", font=fonte(20,"bold"))
    estilo.configure("Subtitulo.TLabel", font=fonte(12,"bold"))
    estilo.configure("Suave.TLabel", foreground=CORES["suave"])
    estilo.configure("Aviso.TLabel", foreground=CORES["aviso"])
    estilo.configure("Erro.TLabel", foreground=CORES["erro"])
    estilo.configure("Treeview", rowheight=29, background="white", fieldbackground="white")
    estilo.configure("Treeview.Heading", font=fonte(10,"bold"), padding=(4,6))
    estilo.map("Treeview", background=[("selected","#d7eaf4")], foreground=[("selected",CORES["texto"])])
    estilo.configure("TNotebook.Tab", padding=(16,9))
    estilo.configure("TLabelframe.Label", font=fonte(10,"bold"))



def centralizar_janela(janela, mestre=None, largura=None, altura=None):
    """Centraliza uma janela sobre a janela mestre (ou na tela)."""
    janela.update_idletasks()

    largura = largura or janela.winfo_reqwidth()
    altura = altura or janela.winfo_reqheight()

    if mestre is not None and mestre.winfo_exists():
        mestre.update_idletasks()
        x = mestre.winfo_rootx() + (mestre.winfo_width() - largura) // 2
        y = mestre.winfo_rooty() + (mestre.winfo_height() - altura) // 2
    else:
        x = (janela.winfo_screenwidth() - largura) // 2
        y = (janela.winfo_screenheight() - altura) // 2

    # Evita posicionar a janela fora da área visível em telas menores.
    x = max(0, min(x, janela.winfo_screenwidth() - largura))
    y = max(0, min(y, janela.winfo_screenheight() - altura))
    janela.geometry(f"{largura}x{altura}+{x}+{y}")

def habilitar(botao, condicao):
    botao.state(["!disabled"] if condicao else ["disabled"])


class Tabela(ttk.Frame):
    def __init__(self, mestre, colunas, altura=6, multiplos=False):
        super().__init__(mestre)
        ids=[c[0] for c in colunas]
        self.arvore=ttk.Treeview(self, columns=ids, show="headings", height=altura,
                               selectmode="extended" if multiplos else "browse")
        for codigo,titulo,largura in colunas:
            self.arvore.heading(codigo,text=titulo)
            self.arvore.column(codigo,width=largura,minwidth=45,stretch=True)
        vertical=ttk.Scrollbar(self,orient="vertical",command=self.arvore.yview)
        horizontal=ttk.Scrollbar(self,orient="horizontal",command=self.arvore.xview)
        self.arvore.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        self.arvore.grid(row=0,column=0,sticky="nsew")
        vertical.grid(row=0,column=1,sticky="ns")
        horizontal.grid(row=1,column=0,sticky="ew")
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.arvore.tag_configure("grave",foreground=CORES["erro"])
        self.arvore.tag_configure("inconsciente",foreground=CORES["aviso"])

    def preencher(self, linhas):
        selecao=self.arvore.selection()
        self.arvore.delete(*self.arvore.get_children())
        for codigo,valores,tag in linhas:
            self.arvore.insert("","end",iid=codigo,values=valores,tags=(tag,) if tag else ())
        validos=[c for c in selecao if self.arvore.exists(c)]
        if validos:
            self.arvore.selection_set(validos)

    def selecionado(self):
        ids=self.arvore.selection()
        return ids[0] if ids else None


class PainelRolavel(ttk.Frame):
    """Mantém botões acessíveis mesmo em janelas de pouca altura."""

    def __init__(self,mestre,largura=322):
        super().__init__(mestre)
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,width=largura,height=350,bg=CORES['fundo'],highlightthickness=0)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        barra=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        barra.grid(row=0,column=1,sticky='ns')
        self.canvas.configure(yscrollcommand=barra.set)
        self.conteudo=ttk.Frame(self.canvas)
        self.item=self.canvas.create_window(0,0,window=self.conteudo,anchor='nw')
        self.conteudo.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.item,width=e.width))


def escolher_grupo(mestre, pokemons, quantidade, titulo):
    """Escolha explícita do trio/dupla; cancelar não altera a partida."""
    janela=tk.Toplevel(mestre)
    janela.title(titulo)
    janela.transient(mestre)
    janela.resizable(False,False)
    corpo=ttk.Frame(janela,padding=22)
    corpo.pack(fill="both",expand=True)
    ttk.Label(corpo,text=titulo,style="Subtitulo.TLabel").pack(anchor="w",pady=(0,6))
    ttk.Label(corpo,text=f"Marque exatamente {quantidade} Pokémon conscientes.").pack(anchor="w",pady=(0,12))
    variaveis=[]
    for i,p in enumerate(pokemons):
        v=tk.BooleanVar(master=janela,value=i<quantidade)
        variaveis.append((p.codigo,v))
        ttk.Checkbutton(corpo,variable=v,text=f"{p.codigo}  {p.nome}  ·  HP {p.hp:.1f}  ·  {tipos_texto(p.tipos)}").pack(anchor="w",pady=5)
    erro=tk.StringVar(master=janela)
    ttk.Label(corpo,textvariable=erro,style="Erro.TLabel").pack(anchor="w",pady=8)
    resposta=[]
    def confirmar():
        ids=[codigo for codigo,v in variaveis if v.get()]
        if len(ids)!=quantidade:
            erro.set(f"Selecione {quantidade}, não {len(ids)}.")
            return
        resposta.extend(ids)
        janela.destroy()
    botoes=ttk.Frame(corpo)
    botoes.pack(fill="x",pady=(8,0))
    ttk.Button(botoes,text="Cancelar",command=janela.destroy).pack(side="left")
    ttk.Button(botoes,text="Confirmar seleção",style="Principal.TButton",command=confirmar).pack(side="right")
    centralizar_janela(janela, mestre)
    janela.lift()
    janela.focus_force()
    janela.grab_set()
    janela.wait_window()
    return resposta or None
