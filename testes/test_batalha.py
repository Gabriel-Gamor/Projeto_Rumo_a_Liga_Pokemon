from random import Random
import unittest

from nucleo.tipos import TabelaTipos
from nucleo.erros import AcaoInvalida
from nucleo.batalha import (
    EstrategiaAutomatica, batalhar, executar_ataque, probabilidades,
)
from testes.apoio import pokemon, treinador, regiao


class Desistir(EstrategiaAutomatica):
    def desistir(self, turno, captura=False):
        return True


class TestBatalha(unittest.TestCase):
    def setUp(self):
        self.tabela = TabelaTipos()
        self.rng = Random(3)

    def test_defensor_ataca_primeiro_e_treinador_ganha_xp(self):
        a,b = treinador('A',ap=200,dp=100),treinador('B',ap=1,dp=0)
        r = batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0)
        self.assertEqual(r.eventos[0]['atacante'][0],'B')
        self.assertEqual(r.vencedor,0)
        self.assertEqual(a.xp,3)
        self.assertEqual(b.xp,0)
        self.assertEqual(sum(p.xp for p in a.equipe),30)
        self.assertEqual(sum(p.xp for p in b.equipe),9)
        self.assertTrue(all(p.hp==1 for p in b.equipe))

    def test_vitoria_contra_treinador_menos_experiente_da_um_xp(self):
        a,b = treinador('A',ap=200,dp=100,xp=10),treinador('B',ap=1,dp=0,xp=2)
        batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0)
        self.assertEqual(a.xp,11)

    def test_desafiante_nao_pode_desistir_de_batalha_treinador(self):
        a,b = treinador('A',ap=200,dp=100),treinador('B',ap=1,dp=0)
        r = batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0,estrategia_a=Desistir())
        self.assertEqual(r.motivo,'nocaute')
        self.assertTrue(r.eventos)

    def test_desafiado_pode_desistir_sem_dano_inventado(self):
        a,b = treinador('A'),treinador('B')
        r = batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0,estrategia_b=Desistir())
        self.assertEqual(r.vencedor,0)
        self.assertEqual(r.eventos,[])
        self.assertTrue(all(p.hp==100 and p.xp==0 for p in a.equipe+b.equipe))

    def test_sem_dano_nao_gera_loop_ou_empate(self):
        a,b = treinador('A',ap=0,dp=100),treinador('B',ap=0,dp=100)
        r = batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0,limite_sem_dano=10)
        self.assertEqual(r.turnos,10)
        self.assertEqual(r.vencedor,0)
        self.assertEqual(r.motivo,'desistencia_do_desafiado_sem_progresso')
        self.assertTrue(all(p.hp==100 for p in a.equipe+b.equipe))

    def test_limite_de_turnos_explicito(self):
        a,b = treinador('A'),treinador('B')
        r = batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0,limite_turnos=1)
        self.assertEqual(r.turnos,1)
        self.assertEqual(r.motivo,'desistencia_do_desafiado_por_limite')

    def test_captura_pode_abandonar_sem_conceder_vitoria(self):
        a = treinador('A')
        r = batalhar(a,None,a.equipe,[pokemon('selvagem')],self.tabela,self.rng,0,
                     captura=True,estrategia_a=Desistir())
        self.assertIsNone(r.vencedor)
        self.assertEqual(r.motivo,'captura_abandonada')
        self.assertEqual(a.xp,0)

    def test_equipes_invalidas(self):
        a,b = treinador('A'),treinador('B')
        with self.assertRaises(AcaoInvalida):
            batalhar(a,b,a.equipe[:2],b.equipe,self.tabela,self.rng,0)
        a.equipe[0].hp=1
        with self.assertRaises(AcaoInvalida):
            batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0)

    def test_dano_base_considera_xp_dos_treinadores(self):
        a,b = pokemon('A',ap=50),pokemon('B',dp=20)
        r = executar_ataque(a,b,a.ataques[0],10,3,self.tabela,self.rng,0)
        self.assertEqual(r['dano'],37)

    def test_probabilidades_simetricas_proporcionais_com_teto(self):
        self.assertEqual(probabilidades(10,10),(0,0))
        self.assertEqual(probabilidades(100,0),(.1,.1))
        self.assertEqual(probabilidades(0,100),(.1,.1))
        self.assertEqual(probabilidades(10000,0),(.35,.4))

    def test_tipos_duplos_e_imunidade(self):
        r = regiao()
        tabela = TabelaTipos(r.vantagens,True)
        self.assertEqual(tabela.multiplicador('agua',('pedra','terra')),4)
        self.assertEqual(tabela.multiplicador('planta',('fogo','voador')),.25)
        self.assertEqual(tabela.multiplicador('eletrico',('agua','terra')),0)
        self.assertEqual(tabela.multiplicador('fada',('dragao',)),2)
        self.assertEqual(tabela.multiplicador('venenoso',('aco',)),0)
        a,b = pokemon('A',ap=100,tipo='normal'),pokemon('B',tipo='fantasma')
        dano = executar_ataque(a,b,a.ataques[0],0,0,tabela,self.rng,0)
        self.assertEqual(dano['dano'],0)
        self.assertEqual(TabelaTipos(r.vantagens,False).multiplicador('normal',('fantasma',)),1)

    def test_treino_nao_concede_xp_ao_treinador(self):
        t = treinador('T',ap=100,dp=0,xp=15)
        r = batalhar(t,t,[t.equipe[0]],[t.equipe[1]],self.tabela,self.rng,0,treino=True)
        self.assertEqual(t.xp,15)
        self.assertEqual(sum(p.xp for p in t.equipe),13)
        self.assertIn(r.vencedor,(0,1))

    def test_sorteios_de_esquiva_e_critico(self):
        class Sorteios:
            def __init__(self,valores):
                self.valores=iter(valores)
            def random(self):
                return next(self.valores)
            def randint(self,a,b):
                return a
        atacante=pokemon('A',ap=20,xp=100)
        defensor=pokemon('D',dp=10)
        r=executar_ataque(atacante,defensor,atacante.ataques[0],0,0,self.tabela,Sorteios([0]),0)
        self.assertTrue(r['esquiva'])
        self.assertEqual(defensor.hp,100)
        r=executar_ataque(atacante,defensor,atacante.ataques[0],0,0,self.tabela,Sorteios([.9,0]),0)
        self.assertTrue(r['critico'])
        self.assertEqual(r['dano'],40)

    def test_dano_pequeno_nao_e_confundido_com_zero_pelo_log(self):
        a,b=treinador('A',ap=0,dp=0),treinador('B',ap=0,dp=0)
        for p in a.equipe+b.equipe:
            p.bonus_evolucao_ap=.001
        r=batalhar(a,b,a.equipe,b.equipe,self.tabela,self.rng,0,
                   limite_turnos=12,limite_sem_dano=3)
        self.assertEqual(r.turnos,12)
        self.assertEqual(r.motivo,'desistencia_do_desafiado_por_limite')
