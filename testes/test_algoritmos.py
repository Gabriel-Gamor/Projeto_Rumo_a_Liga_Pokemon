from itertools import permutations
from math import inf
from random import Random
import unittest

from nucleo.grafo import Grafo, Vertice
from nucleo.algoritmos import bfs, dijkstra, reconstruir, menor_rota
from nucleo.algoritmos import planejar_insignias
from nucleo.treinador import Ginasio
from nucleo.erros import ErroProjeto


def grafo(n, arestas):
    return Grafo([Vertice(str(i), f'Local {i}') for i in range(n)],
                 [(str(u), str(v), w) for u, v, w in arestas])


def enumerar_caminhos(g, origem):
    """Oráculo independente: enumera caminhos simples, exponencial só no teste."""
    melhor = {v: inf for v in g.adj}
    def visitar(u, custo, vistos):
        melhor[u] = min(melhor[u], custo)
        for v, w in g.adj[u]:
            if v not in vistos:
                visitar(v, custo+w, vistos | {v})
    visitar(origem, 0, {origem})
    return melhor


class TestGrafos(unittest.TestCase):
    def test_representacao_bidirecional_e_soma_uma_vez(self):
        g = grafo(3, [(0,1,9), (0,1,3), (1,2,5), (2,2,4)])
        self.assertEqual(g.soma_pesos, 21)
        self.assertEqual(g.tamanho, 4)
        self.assertEqual(g.peso('0','1'), 3)
        self.assertEqual(g.peso('1','0'), 3)
        self.assertEqual(sum(map(len,g.adj.values())), 8)

    def test_pesos_e_extremidades_invalidos(self):
        for w in (-1,0,True,1.5):
            with self.subTest(w=w), self.assertRaises(ErroProjeto):
                grafo(2, [(0,1,w)])
        with self.assertRaises(ErroProjeto):
            grafo(2, [(0,3,2)])

    def test_bfs_mede_saltos_nao_pesos(self):
        g = grafo(4, [(0,1,50),(0,2,1),(2,1,1)])
        dist, pai = bfs(g,'0')
        self.assertEqual(dist['1'], 1)
        self.assertEqual(dist['3'], inf)
        self.assertEqual(reconstruir(pai,'0','3'), [])
        self.assertEqual(menor_rota(g,'0','1'), (2,['0','2','1']))

    def test_dijkstra_contra_enumeracao_em_grafos_aleatorios(self):
        rng = Random(543)
        for caso in range(30):
            n = rng.randint(2,6)
            arestas = [(i,j,rng.randint(1,30)) for i in range(n) for j in range(i+1,n)
                       if rng.random() < .6]
            g = grafo(n,arestas)
            esperado = enumerar_caminhos(g,'0')
            for metodo in ('heap','quadratico','auto'):
                with self.subTest(caso=caso,metodo=metodo):
                    d,pai = dijkstra(g,'0',metodo)
                    self.assertEqual(d,esperado)
                    for v in g.adj:
                        caminho = reconstruir(pai,'0',v)
                        if d[v] != inf:
                            self.assertEqual(sum(g.peso(u,z) for u,z in zip(caminho,caminho[1:])),d[v])
                        else:
                            self.assertEqual(caminho,[])

    def test_ciclo_de_pais_rejeitado(self):
        with self.assertRaises(ErroProjeto):
            reconstruir({'s':None,'a':'b','b':'a'},'s','a')

    def test_dp_escolhe_subconjunto_e_ordem_contra_forca_bruta(self):
        rng = Random(900)
        for caso in range(10):
            g = grafo(7, [(i,j,rng.randint(1,20)) for i in range(7) for j in range(i+1,7)])
            gyms = [Ginasio(f'G{i}',str(i),str(i),'L') for i in range(1,6)]
            dist = {str(i):enumerar_caminhos(g,str(i)) for i in range(7)}
            for k in (1,3,5):
                esperado = min(sum(dist[u][v] for u,v in zip(('0',)+p,p+('6',)))+k
                               for p in permutations(tuple(str(i) for i in range(1,6)),k))
                plano = planejar_insignias(g,'0','6',gyms,k)
                with self.subTest(caso=caso,k=k):
                    self.assertEqual(plano.tempo_minimo,esperado)
                    self.assertEqual(len(set(plano.ginasios)),k)
                    custo = sum(g.peso(u,v) for u,v in zip(plano.vertices,plano.vertices[1:]))+k
                    self.assertEqual(custo,esperado)

    def test_dp_sem_visitas_e_impossibilidade(self):
        g = grafo(3,[(0,1,5)])
        self.assertEqual(planejar_insignias(g,'0','1',[],0).tempo_minimo,5)
        with self.assertRaises(ErroProjeto):
            planejar_insignias(g,'0','2',[],0)
        with self.assertRaises(ErroProjeto):
            planejar_insignias(g,'0','1',[],1)

    def test_origem_e_metodo_invalidos(self):
        g = grafo(2,[(0,1,1)])
        with self.assertRaises(ErroProjeto):
            dijkstra(g,'inexistente')
        with self.assertRaises(ErroProjeto):
            dijkstra(g,'0','biblioteca')
