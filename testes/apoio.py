from copy import deepcopy
import json
from pathlib import Path

from nucleo.tipos import Ataque, Especie, Fase
from nucleo.pokemon import Pokemon
from nucleo.treinador import Treinador
from nucleo.regiao import validar_regiao
from nucleo.jogo import Jogo
from nucleo.erros import AcaoInvalida

RAIZ = Path(__file__).resolve().parents[1]
DADOS = json.loads((RAIZ / 'dados' / 'regiao.json').read_text(encoding='utf-8'))
# Cenário controlado só para testes, sem alterar o arquivo de jogo.
DADOS['quantidades'].update(selvagens=6,treinadores=2,ovos=3,ervas=6,rockets=1)
DADOS['regras'].update(xp_selvagem_max=80,xp_lider_max=30,xp_treinador_max=3,
                       ap_regiao=[12,20],dp_regiao=[3,8],hp_regiao_min=40,
                       ap_inicial=[35,45],dp_inicial=[15,25])
for ginasio in DADOS['ginasios']:
    ginasio['movel']=False



def regiao(**regras):
    dados = deepcopy(DADOS)
    dados['regras'].update(regras)
    return validar_regiao(dados)


def jogo(semente=3, **regras):
    return Jogo(regiao(**regras), semente)


def pokemon(codigo='P', ap=40, dp=10, tipo='normal', hp=100, xp=0):
    fases = tuple(Fase(f'Forma {i}', (tipo,), (Ataque(f'Ataque {i}', tipo),)) for i in range(3))
    p = Pokemon(codigo, Especie('teste', fases), ap, dp, hp=hp)
    p.ganhar_xp(xp)
    return p


def treinador(codigo, ap=40, dp=10, xp=0):
    return Treinador(codigo, codigo, 'PRA',
                     [pokemon(f'{codigo}{i}', ap, dp) for i in range(3)], xp=xp)


def posicionar(j, codigo, local='PRA'):
    """Prepara encontro controlado; não faz parte das ações disponíveis ao jogador."""
    a = j.mundo.atores[codigo]
    a.versao += 1
    a.movimento = None
    a.suspenso = False
    a.invisivel_ate = None
    j.mundo._mudar_posicao(a, local)
    j.jogador.posicao = local
    return a


def jornada_de_teste(jogo):
    passos = []
    tentativas = {}
    try:
        while len(jogo.jogador.insignias) < 8:
            if jogo.jogador.pendente:
                # Escolha explícita desta política: mantém a equipe anterior.
                jogo.guardar(jogo.jogador.pendente.codigo)
            if len(jogo.jogador.equipe) < 3:
                raise AcaoInvalida("A jornada de teste exige o trio inicial.")
            if any(p.hp < 100 or not p.consciente for p in jogo.jogador.equipe):
                pmcs = jogo.mundo.regiao.grafo.locais("pmc")
                pmc = min(pmcs, key=lambda v: jogo.rota(v)["tempo"])
                viagem = jogo.viajar(pmc)
                if not viagem["chegou"]:
                    raise AcaoInvalida("A viagem ao PMC foi interrompida.")
                cura = jogo.tratar()
                passos.append({"acao":"pmc", "local":pmc, "tempo":jogo.mundo.agora, **cura})
            plano = jogo.plano()
            codigo = plano["ginasios"][0]
            g = jogo.mundo.ginasios[codigo]
            jogo.viajar(g.vertice)
            ator = jogo.mundo.atores["L-" + codigo]
            while ator not in jogo.mundo.presentes() or len(ator.treinador.conscientes) < 3:
                jogo.esperar(5)
            resultado = jogo.desafiar(codigo)
            passos.append({"acao":"batalha", "ginasio":codigo, "venceu":resultado["venceu"],
                           "motivo":resultado["motivo"], "turnos":resultado["turnos"],
                           "tempo":jogo.mundo.agora, "insignias":len(jogo.jogador.insignias)})
            tentativas[codigo] = tentativas.get(codigo, 0) + 1
            if not resultado["venceu"] and tentativas[codigo] >= 5:
                raise AcaoInvalida(f"Jornada de teste interrompida após cinco derrotas em {codigo}.")
        jogo.viajar(jogo.mundo.regiao.estadio)
        passos.append({"acao":"inscricao", **jogo.inscrever()})
        return {"sucesso":True, "semente":jogo.mundo.semente, "passos":passos, "status":jogo.status()}
    except AcaoInvalida as exc:
        return {"sucesso":False, "erro":str(exc), "semente":jogo.mundo.semente,
                "passos":passos, "status":jogo.status()}
