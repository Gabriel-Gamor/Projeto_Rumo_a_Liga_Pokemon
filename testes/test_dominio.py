from copy import deepcopy
from random import Random
import unittest

from nucleo.treinador import Treinador
from nucleo.erros import AcaoInvalida
from testes.apoio import pokemon


class TestPokemon(unittest.TestCase):
    def test_distancia_acumula_resto(self):
        p = pokemon()
        p.percorrer(99)
        self.assertEqual(p.xp,0)
        p.percorrer(202)
        self.assertEqual((p.xp,p.resto_distancia),(3,1))

    def test_evolucao_exata_e_preserva_ataques(self):
        p = pokemon(ap=40,dp=20)
        p.ganhar_xp(999)
        self.assertEqual(p.fase,0)
        p.ganhar_xp(1)
        self.assertEqual(p.fase,1)
        self.assertAlmostEqual(p.ap,140*1.3)
        self.assertAlmostEqual(p.dp,120*1.3)
        self.assertEqual(len(p.ataques),2)
        p.ganhar_xp(1000)
        self.assertAlmostEqual(p.ap,(182+100)*1.3)
        self.assertEqual(len(p.ataques),3)
        p.ganhar_xp(5000)
        self.assertEqual(p.fase,2)
        self.assertAlmostEqual(p.ap,366.6+500)

    def test_xp_em_lote_equivale_a_incrementos(self):
        a,b = pokemon(),pokemon()
        a.ganhar_xp(2345)
        for _ in range(2345):
            b.ganhar_xp(1)
        self.assertEqual(a,b)

    def test_bonus_so_se_adversario_tinha_xp_suficiente(self):
        p = pokemon(xp=100)
        p.vencer_duelo(100,100)
        self.assertEqual((p.xp,p.bonus_batalhas),(110,1))
        p.vencer_duelo(50,110)
        self.assertEqual((p.xp,p.bonus_batalhas),(120,1))
        self.assertAlmostEqual(p.ap,40+12+1)

    def test_hp_minimo_e_ferimento_grave_nao_regenera(self):
        p = pokemon()
        p.receber_dano(10000,0,Random(8))
        self.assertEqual(p.hp,1)
        self.assertFalse(p.consciente)
        self.assertTrue(10 <= p.inconsciente_ate <= 50)
        p.passar_tempo(500,500)
        self.assertEqual(p.hp,1)
        self.assertFalse(p.tomar_erva())
        p.tratar_pmc()
        self.assertTrue(p.consciente)
        self.assertEqual(p.hp,100)

    def test_repouso_preserva_limiar_e_independe_dos_saltos(self):
        a = pokemon(hp=19)
        a.inconsciente_ate = 43
        b = deepcopy(a)
        a.passar_tempo(100,100)
        for t in range(1,101):
            b.passar_tempo(1,t)
            self.assertEqual(b.consciente,b.hp>=20)
        self.assertEqual(a,b)
        self.assertEqual(a.hp,26)

    def test_cura_passiva_e_ervas_com_teto(self):
        p = pokemon(hp=85)
        p.passar_tempo(19,19)
        self.assertEqual(p.hp,86)
        p.passar_tempo(1,20)
        self.assertEqual(p.hp,87)
        self.assertTrue(p.tomar_erva())
        self.assertEqual(p.hp,97)
        p.tomar_erva()
        self.assertEqual(p.hp,100)

    def test_repouso_nao_diminui_hp_fracionario(self):
        p=pokemon(hp=19.8)
        p.inconsciente_ate=40
        p.passar_tempo(10,10)
        self.assertEqual(p.hp,19.8)
        self.assertFalse(p.consciente)

    def test_xp_e_distancia_nao_negativos(self):
        p = pokemon()
        for valor in (-1,1.5,True):
            with self.assertRaises(ValueError):
                p.ganhar_xp(valor)
            with self.assertRaises(ValueError):
                p.percorrer(valor)


class TestInventario(unittest.TestCase):
    def setUp(self):
        self.t = Treinador('j','Jogador','LAB')
        for i in range(6):
            self.t.receber(pokemon(str(i)))

    def test_setimo_fica_pendente_sem_sete_ativos(self):
        novo = pokemon('novo')
        self.assertEqual(self.t.receber(novo),'selecao_pendente')
        self.assertEqual((len(self.t.equipe),self.t.ocupacao),(6,7))
        self.t.enviar_ao_professor('2')
        self.assertIn(novo,self.t.equipe)
        self.assertIsNone(self.t.pendente)
        self.assertEqual(self.t.deposito[0].codigo,'2')

    def test_pode_enviar_o_recem_capturado(self):
        self.t.receber(pokemon('novo'))
        self.t.enviar_ao_professor('novo')
        self.assertEqual(len(self.t.equipe),6)
        self.assertEqual(self.t.deposito[0].codigo,'novo')

    def test_ovo_na_setima_posicao_nasce_no_tempo_certo(self):
        self.t.pegar_ovo('ovo',pokemon('filhote'),20)
        self.assertEqual(self.t.chocar(119),[])
        self.assertEqual(self.t.chocar(120)[0].codigo,'filhote')
        self.assertEqual(len(self.t.equipe),6)
        self.assertEqual(self.t.pendente.codigo,'filhote')

    def test_ovos_multiplos_ocupacao_e_nao_abandono(self):
        for i in range(3):
            self.t.enviar_ao_professor(str(i))
        for i in range(4):
            self.t.pegar_ovo(f'E{i}',pokemon(f'F{i}'),0)
        with self.assertRaises(AcaoInvalida):
            self.t.pegar_ovo('E5',pokemon('F5'),0)
        with self.assertRaises(AcaoInvalida):
            self.t.enviar_ao_professor('E0')
        self.t.chocar(100)
        self.assertEqual((len(self.t.equipe),self.t.ocupacao),(6,7))

    def test_rejeicao_de_duplicata_nao_muda_inventario(self):
        antes = list(self.t.equipe)
        with self.assertRaises(AcaoInvalida):
            self.t.receber(self.t.equipe[0])
        self.assertEqual(self.t.equipe,antes)
        self.assertIsNone(self.t.pendente)

    def test_escolha_trio_exige_tres_distintos_conscientes(self):
        with self.assertRaises(AcaoInvalida):
            self.t.escolher_trio(['0','0','1'])
        self.t.equipe[0].hp = 1
        with self.assertRaises(AcaoInvalida):
            self.t.escolher_trio(['0','1','2'])
        self.assertEqual(len(self.t.escolher_trio()),3)
