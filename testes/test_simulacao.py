from copy import deepcopy
from random import Random
import unittest

from nucleo.erros import AcaoInvalida
from nucleo.regiao import validar_regiao
from testes.apoio import jornada_de_teste
from nucleo.jogo import Jogo
from testes.apoio import DADOS, jogo, posicionar
from testes.test_batalha import Desistir


class TestMundo(unittest.TestCase):
    def test_mesma_semente_mesmos_estados_e_eventos(self):
        a,b = jogo(91),jogo(91)
        a.esperar(103)
        b.esperar(103)
        self.assertEqual(a.status(),b.status())
        self.assertEqual(a.mundo.fila_eventos,b.mundo.fila_eventos)
        self.assertEqual(list(a.mundo.historico),list(b.mundo.historico))

    def test_iniciais_trio_e_alternativa_um_aleatorio(self):
        j = jogo()
        self.assertEqual(len(j.jogador.equipe),3)
        self.assertEqual(j.jogador.pokebolas,7)
        self.assertTrue(j.jogador.incubadora)
        self.assertEqual(len({p.especie.codigo for p in j.jogador.equipe}),3)
        self.assertTrue(all(p.fase==0 and p.xp==0 for p in j.jogador.equipe))
        outro = Jogo(j.mundo.regiao,3,iniciais='aleatorio')
        self.assertEqual(len(outro.jogador.equipe),1)
        self.assertEqual(outro.jogador.equipe[0].fase,0)

    def test_espera_nao_da_xp_distancia_e_movimento_adjacente_da(self):
        j = jogo()
        j.esperar(100)
        self.assertTrue(all(p.xp==0 for p in j.jogador.equipe))
        with self.assertRaises(AcaoInvalida):
            j.mover('EST')
        for _ in range(7):
            j.mover('PRA')
            j.mover('LAB')
        self.assertEqual(j.mundo.distancia_percorrida,112)
        self.assertTrue(all(p.xp==1 and p.resto_distancia==12 for p in j.jogador.equipe))

    def test_npcs_percorrem_arestas_com_pesos_e_nao_aparecem_em_transito(self):
        j = jogo()
        j.esperar(300)
        eventos = [e for e in j.mundo.historico if e['tipo']=='movimento_npc']
        self.assertTrue(eventos)
        for e in eventos:
            self.assertEqual(e['chegada']-e['partida'],j.mundo.regiao.grafo.peso(e['origem'],e['destino']))
        for a in j.mundo.atores.values():
            if a.movimento:
                self.assertIsNone(a.posicao)
                self.assertNotIn(a,j.mundo.presentes())

    def test_lider_movel_retorna_periodicamente(self):
        dados = deepcopy(DADOS)
        dados['ginasios'][2].update(movel=True,periodo=100,permanencia=30)
        j = Jogo(validar_regiao(dados),3)
        a = j.mundo.atores['L-G03']
        for t in (20,100,120,200,220,300):
            j.mundo.avancar(t-j.mundo.agora)
            self.assertEqual(a.posicao,'G03')

    def test_graves_de_npc_sao_levados_ao_pmc(self):
        j = jogo()
        a = posicionar(j,'T01')
        a.treinador.equipe[0].hp=1
        j.mundo.retomar(a)
        j.esperar(100)
        curas = [e for e in j.mundo.historico if e['tipo']=='tratamento_npc' and e['ator']=='T01']
        self.assertTrue(curas)
        self.assertIn(curas[0]['local'],j.mundo.regiao.grafo.locais('pmc'))
        self.assertEqual(a.treinador.equipe[0].hp,100)

    def test_ovo_oculta_tipo_e_choca_apos_cem_unidades(self):
        j = jogo()
        ovo = j.mundo.itens['E01']
        ovo.posicao='LAB'
        mostrado = next(i for i in j.olhar()['itens'] if i['codigo']=='E01')
        self.assertEqual(set(mostrado),{'codigo','tipo'})
        j.coletar('E01')
        self.assertNotIn('filhote',j.status()['ovos'][0])
        j.esperar(99)
        self.assertEqual(len(j.jogador.equipe),3)
        j.esperar(1)
        self.assertEqual(len(j.jogador.equipe),4)
        self.assertEqual(j.jogador.equipe[-1].xp,0)
        self.assertEqual(j.jogador.equipe[-1].fase,0)

    def test_filhote_em_transito_nao_recebe_distancia_antes_de_nascer(self):
        j = jogo()
        ovo = j.mundo.itens['E01']
        ovo.posicao='LAB'
        j.coletar('E01')
        j.esperar(95)
        j.mover('PRA')  # oito unidades: nasce após cinco, percorre apenas três
        filhote = j.jogador.equipe[-1]
        self.assertEqual(filhote.resto_distancia,3)
        self.assertEqual(filhote.xp,0)

    def test_pmc_exige_local_e_cura_em_paralelo(self):
        j = jogo()
        for p in j.jogador.equipe:
            p.hp=1
        with self.assertRaises(AcaoInvalida):
            j.tratar()
        j.viajar('PMC1')
        antes = j.mundo.agora
        resultado = j.tratar()
        self.assertEqual(j.mundo.agora-antes,max(resultado['tempos_individuais'].values()))
        self.assertTrue(all(10<=t<=50 for t in resultado['tempos_individuais'].values()))
        self.assertTrue(all(p.hp==100 and p.consciente for p in j.jogador.equipe))

    def test_ervas_nao_curam_inconscientes(self):
        j = jogo()
        j.mundo.itens['H01'].posicao='LAB'
        j.jogador.equipe[0].hp=92
        j.jogador.equipe[1].hp=15
        j.jogador.equipe[1].inconsciente_ate=40
        j.jogador.equipe[2].hp=1
        j.coletar('H01')
        self.assertEqual([p.hp for p in j.jogador.equipe],[100,15,1])
        with self.assertRaises(AcaoInvalida):
            j.coletar('H01')


class TestJornada(unittest.TestCase):
    def test_mapa_entregue_permite_jornadas_completas(self):
        from nucleo.regiao import carregar_regiao
        from testes.apoio import RAIZ
        regiao = carregar_regiao(RAIZ / 'dados' / 'regiao.json')
        for semente in (1,3,7,50,90):
            with self.subTest(semente=semente):
                j = Jogo(regiao, semente)
                resultado = jornada_de_teste(j)
                self.assertTrue(resultado['sucesso'], resultado.get('erro'))
                self.assertTrue(j.inscrito)
                self.assertEqual(len(j.jogador.insignias), 8)
                self.assertLessEqual(j.mundo.agora, regiao.prazo)

    def test_sequencias_aleatorias_preservam_invariantes_e_salvamento(self):
        import json
        from nucleo.salvamento import estado,restaurar
        for seed in range(8):
            j=jogo(seed)
            escolhas=Random(seed+987)
            for passo in range(80):
                if j.expirado or j.inscrito:
                    break
                if j.jogador.pendente:
                    j.guardar(j.jogador.pendente.codigo)
                acao=escolhas.randrange(5)
                try:
                    if acao==0:
                        vizinhos=j.mundo.regiao.grafo.adj[j.jogador.posicao]
                        j.mover(escolhas.choice(vizinhos)[0])
                    elif acao==1:
                        j.esperar(escolhas.randint(1,25))
                    elif acao==2:
                        itens=j.olhar()['itens']
                        if itens:
                            j.coletar(itens[0]['codigo'])
                    elif acao==3:
                        presentes=j.mundo.presentes()
                        if presentes:
                            ator=escolhas.choice(presentes)
                            if ator.tipo=='selvagem':
                                j.capturar(ator.codigo)
                            else:
                                j.desafiar(ator.codigo)
                    elif acao==4:
                        j.tratar()
                except AcaoInvalida:
                    pass  # Uma ação recusada não deve corromper o mundo.
                j.jogador.conferir_limites()
                for p in j.mundo._pokemons_existentes():
                    self.assertTrue(1<=p.hp<=100,(seed,passo,p.resumo()))
                    self.assertEqual(p.consciente,p.hp>=20)
                    self.assertEqual(p.fase,min(p.xp//1000,len(p.especie.fases)-1))
                if passo%10==0:
                    status=j.status()
                    j=restaurar(json.loads(json.dumps(estado(j))))
                    self.assertEqual(j.status(),status)

    def test_proibicao_batalhas_nos_locais_protegidos(self):
        j = jogo()
        for local in ('LAB','PMC1'):
            posicionar(j,'T01',local)
            with self.assertRaises(AcaoInvalida):
                j.desafiar('T01')
            posicionar(j,'S01',local)
            with self.assertRaises(AcaoInvalida):
                j.capturar('S01')
            with self.assertRaises(AcaoInvalida):
                j.treinar('P0001','P0002')

    def test_captura_bonus_e_duracao(self):
        j = jogo(vantagens_tipos=False)
        a = posicionar(j,'S01')
        a.pokemon.ap_inicial=0
        a.pokemon.dp_inicial=0
        a.pokemon.hp=20
        antes_p = a.pokemon.xp
        antes_j = {p.codigo:p.xp for p in j.jogador.equipe}
        resultado = j.capturar('S01')
        self.assertTrue(resultado['capturado'])
        self.assertEqual(j.mundo.agora,1)
        self.assertEqual(j.jogador.xp,3)
        self.assertEqual(a.pokemon.xp-antes_p,6)
        self.assertEqual(sum(p.xp-antes_j[p.codigo] for p in j.jogador.equipe if p.codigo in antes_j),13)
        self.assertFalse(a.ativo)
        self.assertIn(a.pokemon,j.jogador.equipe)

    def test_abandono_esconde_selvagem_permanentemente(self):
        j = jogo()
        a = posicionar(j,'S01')
        hp = a.pokemon.hp
        r = j.capturar('S01',abandonar=True)
        self.assertFalse(r['capturado'])
        self.assertIsNone(r['vencedor'])
        self.assertIn(j.jogador.codigo,a.escondido_para)
        self.assertEqual(a.pokemon.hp,hp)
        posicionar(j,'S01')
        self.assertNotIn(a,j.mundo.presentes())

    def test_batalha_dura_uma_unidade_e_badge_nao_some_ao_perder(self):
        j = jogo(vantagens_tipos=False)
        a = posicionar(j,'L-G01','G01')
        j.jogador.xp=1000
        antes = j.mundo.agora
        r = j.desafiar('G01')
        self.assertTrue(r['venceu'])
        self.assertEqual(j.mundo.agora-antes,1)
        badge = set(j.jogador.insignias)
        posicionar(j,'T01')
        r = j.desafiar('T01',como_desafiado=True,estrategia=Desistir())
        self.assertFalse(r['venceu'])
        self.assertEqual(j.jogador.insignias,badge)

    def test_treinador_pode_recusar(self):
        j = jogo(chance_aceitar=0)
        posicionar(j,'T01')
        r = j.desafiar('T01')
        self.assertFalse(r['aceitou'])
        self.assertEqual(j.mundo.agora,0)

    def test_selecao_pendente_bloqueia_viagem_ate_escolha(self):
        j = jogo()
        for _ in range(4):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        with self.assertRaises(AcaoInvalida):
            j.mover('PRA')
        escolhido = j.jogador.equipe[1].codigo
        j.guardar(escolhido)
        j.mover('PRA')
        self.assertEqual(len(j.jogador.equipe),6)

    def test_captura_com_seis_ativos_reserva_setima_posicao(self):
        j=jogo()
        for _ in range(3):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        a=posicionar(j,'S01')
        a.pokemon.hp=1
        r=j.capturar('S01')
        self.assertTrue(r['capturado'])
        self.assertEqual(r['destino'],'selecao_pendente')
        self.assertIs(j.jogador.pendente,a.pokemon)
        self.assertEqual((len(j.jogador.equipe),j.jogador.ocupacao),(6,7))

    def test_captura_com_sete_posicoes_ocupadas_nao_muda_ator(self):
        j=jogo()
        for _ in range(3):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        j.mundo.itens['E01'].posicao='LAB'
        j.coletar('E01')
        a=posicionar(j,'S01')
        with self.assertRaises(AcaoInvalida):
            j.capturar('S01')
        self.assertTrue(a.ativo)
        self.assertFalse(a.suspenso)
        self.assertEqual(j.mundo.agora,0)

    def test_inscricao_exige_insignias_estadio_e_prazo_inclusivo(self):
        j = jogo()
        with self.assertRaises(AcaoInvalida):
            j.inscrever()
        j.jogador.posicao='EST'
        with self.assertRaises(AcaoInvalida):
            j.inscrever()
        j.jogador.insignias = {g.insignia for g in j.mundo.regiao.ginasios}
        j.mundo.agora=j.mundo.regiao.prazo
        self.assertTrue(j.inscrever()['inscrito'])
        j2=jogo()
        j2.jogador.posicao='EST'
        j2.jogador.insignias=set(j.jogador.insignias)
        j2.mundo.agora=j2.mundo.regiao.prazo+1
        with self.assertRaises(AcaoInvalida):
            j2.inscrever()
        self.assertTrue(j2.expirado)

    def test_rocket_so_rouba_apos_vitoria_e_reaparece(self):
        j = jogo()
        j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        a = posicionar(j,'R01')
        r = j.desafiar('R01',como_desafiado=True,estrategia=Desistir())
        roubado = r['pokemon_roubado']
        self.assertIn(roubado,a.roubados)
        self.assertEqual(len(j.jogador.equipe),3)
        self.assertIsNone(a.posicao)
        self.assertTrue(j.mundo.agora < a.invisivel_ate <= j.mundo.agora+80)
        j.mundo.avancar(a.invisivel_ate-j.mundo.agora)
        self.assertIsNotNone(a.posicao)
        self.assertIsNone(a.invisivel_ate)
        posicionar(j,'R01')
        j.jogador.xp=1000
        r = j.desafiar('R01')
        self.assertTrue(r['venceu'])
        self.assertIn(roubado,r['recuperados_no_laboratorio'])
        self.assertIn(roubado,[p.codigo for p in j.jogador.deposito])
        d,_ = j.mundo.caminhos('PRA')
        self.assertGreaterEqual(d[a.posicao],.75*max(d.values()))

    def test_jornada_conclui_sem_atribuir_badges_diretamente(self):
        for seed in (1,3,7,50,90):
            with self.subTest(semente=seed):
                j=jogo(seed)
                r=jornada_de_teste(j)
                self.assertTrue(r['sucesso'],r.get('erro'))
                vitorias = [e for e in j.mundo.historico if e['tipo']=='batalha_treinador' and e['venceu']]
                self.assertEqual(len(vitorias),8)
                self.assertTrue(j.inscrito)
                self.assertLessEqual(j.mundo.agora,j.mundo.regiao.prazo)
