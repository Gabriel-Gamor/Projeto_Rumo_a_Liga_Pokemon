"""Arquivos de região, persistência e restrição de dependências."""

import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from nucleo.erros import ErroFormato
from nucleo.regiao import validar_regiao, carregar_regiao
from nucleo.salvamento import salvar, carregar, estado, restaurar
from testes.apoio import RAIZ, DADOS, jogo, posicionar


class TestArquivoRegiao(unittest.TestCase):
    def rejeitar(self,alterar):
        d=deepcopy(DADOS)
        alterar(d)
        with self.assertRaises(ErroFormato):
            validar_regiao(d)

    def test_arquivo_entregue_contem_requisitos_adicionais(self):
        r=carregar_regiao(RAIZ/'dados/regiao.json')
        self.assertEqual((r.grafo.ordem,r.grafo.tamanho,r.grafo.soma_pesos,r.prazo),(20,25,247,2964))
        self.assertEqual(set(r.quantidades),{'selvagens','treinadores','ovos','ervas','rockets'})
        self.assertGreater(r.quantidades['rockets'],0)
        self.assertTrue(r.regras['vantagens_tipos'])
        self.assertEqual(len(r.vantagens),18)
        self.assertTrue(any(g.movel for g in r.ginasios))
        self.assertTrue(any(not g.movel for g in r.ginasios))

    def test_limites_do_prazo_inclusivos(self):
        for multiplicador in (10,15):
            d=deepcopy(DADOS)
            d['prazo']=multiplicador*sum(a[2] for a in d['arestas'])
            self.assertEqual(validar_regiao(d).prazo,d['prazo'])
        self.rejeitar(lambda d:d.update(prazo=1))

    def test_rejeita_regiao_desconexa(self):
        d=deepcopy(DADOS)
        d.pop('ordem_mapa',None)
        d.pop('desenho',None)
        d['vertices'].append({'id':'ISOLADO','nome':'Ilha','tipo':'comum'})
        with self.assertRaises(ErroFormato):
            validar_regiao(d)

    def test_rejeita_ginasios_iniciais_e_especies_invalidos(self):
        self.rejeitar(lambda d:d.update(iniciais=['bulbasaur']))
        self.rejeitar(lambda d:d['ginasios'].pop())
        self.rejeitar(lambda d:d['ginasios'][1].update(insignia=d['ginasios'][0]['insignia']))
        self.rejeitar(lambda d:d['especies'][0]['fases'][1].update(nome='Bulbasaur'))
        self.rejeitar(lambda d:d['especies'][0]['fases'].append(deepcopy(d['especies'][0]['fases'][0])))

    def test_rejeita_tabela_incompleta_e_intervalos_invalidos(self):
        self.rejeitar(lambda d:d['vantagens'].pop('fada'))
        self.rejeitar(lambda d:d['regras'].update(ap_inicial=[50,10]))
        self.rejeitar(lambda d:d['quantidades'].update(selvagens=-1))
        self.rejeitar(lambda d:d['vantagens']['fogo'].update(planta=3))

    def test_posicoes_visuais_opcionais_e_validadas(self):
        d=deepcopy(DADOS)
        d.pop('desenho')
        validar_regiao(d)
        self.rejeitar(lambda d:d['desenho']['posicoes'].pop('LAB'))
        self.rejeitar(lambda d:d['desenho']['posicoes'].update(LAB=[-1,12]))
        self.rejeitar(lambda d:d['desenho']['desvios'].update(inexistente=[[10,10]]))

    def test_json_malformado(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'invalido.json'
            p.write_text('{incorreto',encoding='utf-8')
            with self.assertRaises(ErroFormato):
                carregar_regiao(p)


class TestSalvamento(unittest.TestCase):
    def test_retoma_mesmos_eventos_e_aleatoriedade(self):
        j=jogo(83)
        j.viajar('G03')
        j.esperar(17)
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'partida.json'
            salvar(j,p)
            novo=carregar(p)
            self.assertEqual(j.status(),novo.status())
            for copia in (j,novo):
                copia.esperar(100)
                copia.viajar('PMC2')
            self.assertEqual(j.status(),novo.status())
            self.assertEqual(j.mundo.fila_eventos,novo.mundo.fila_eventos)
            self.assertEqual(j.mundo.rng.getstate(),novo.mundo.rng.getstate())
            self.assertEqual(list(j.mundo.historico),list(novo.mundo.historico))

    def test_pokemon_capturado_preserva_identidade_unica(self):
        j=jogo()
        a=posicionar(j,'S01')
        a.pokemon.hp=1
        j.capturar('S01')
        novo=restaurar(json.loads(json.dumps(estado(j))))
        p=novo.jogador.equipe[-1]
        self.assertIs(p,novo.mundo.atores['S01'].pokemon)
        p.tratar_pmc()
        p.hp=80
        novo.esperar(10)
        self.assertEqual(p.hp,81)

    def test_ovos_e_escolha_pendente_sao_preservados(self):
        j=jogo()
        for _ in range(3):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        j.mundo.itens['E01'].posicao='LAB'
        j.coletar('E01')
        novo=restaurar(json.loads(json.dumps(estado(j))))
        novo.esperar(100)
        self.assertIsNotNone(novo.jogador.pendente)
        terceiro=restaurar(json.loads(json.dumps(estado(novo))))
        self.assertEqual(novo.status(),terceiro.status())

    def test_salvamento_adulterado_e_rejeitado(self):
        base=estado(jogo())
        for alterar in (lambda d:d.update(versao=999),lambda d:d.update(agora=-1),
                        lambda d:d['jogador'].update(posicao='INEXISTENTE'),
                        lambda d:d['pokemons']['P0001'].update(hp=0),
                        lambda d:d['jogador']['equipe'].append('P0001'),
                        lambda d:d.update(inscrito=True)):
            d=deepcopy(base)
            alterar(d)
            with self.assertRaises(ErroFormato):
                restaurar(d)

    def test_projeto_nao_importa_solucoes_externas(self):
        permitidos=sys.stdlib_module_names|{'nucleo','interface'}
        for pasta in ('nucleo','interface'):
            for arquivo in (RAIZ/pasta).glob('*.py'):
                for no in ast.walk(ast.parse(arquivo.read_text(encoding='utf-8'))):
                    nomes=[]
                    if isinstance(no,ast.Import):
                        nomes=[alias.name for alias in no.names]
                    elif isinstance(no,ast.ImportFrom) and no.module:
                        nomes=[no.module]
                    for nome in nomes:
                        self.assertIn(nome.split('.')[0],permitidos,str(arquivo))
                        if pasta=='nucleo':
                            self.assertNotEqual(nome.split('.')[0],'tkinter')
