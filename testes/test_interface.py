"""Integração real dos widgets Tk com o núcleo, sem bibliotecas de automação.

Execute em uma sessão gráfica. Sem Tk/display, somente esta classe é ignorada;
os testes do núcleo continuam disponíveis em terminais sem interface gráfica.
"""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
except ImportError:
    tk = None

from testes.apoio import jogo, pokemon, posicionar


class TestInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:
            raise unittest.SkipTest('Tkinter não está instalado.')
        try:
            raiz = tk.Tk()
            raiz.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest('Interface requer uma sessão gráfica: ' + str(exc))
        from interface.janela import Aplicacao
        cls.Aplicacao = Aplicacao

    def setUp(self):
        self.raiz = tk.Tk()
        self.app = None
        self.erros_callbacks = []
        self.raiz.report_callback_exception = lambda tipo, valor, tb: self.erros_callbacks.append(valor)

    def tearDown(self):
        for codigo in self.raiz.tk.call('after', 'info'):
            self.raiz.after_cancel(codigo)
        self.raiz.destroy()
        self.assertEqual(self.erros_callbacks, [], 'Erros em callbacks dos widgets')

    def abrir(self, partida=None):
        self.app = self.Aplicacao(self.raiz, partida or jogo())
        self.raiz.update()
        return self.app

    def clicar_local(self, codigo):
        self.app.abas.select(self.app.mapa)
        self.raiz.update()
        x, y = self.app.mapa.centros[codigo]
        self.app.mapa.canvas.event_generate('<Motion>', x=round(x), y=round(y))
        self.app.mapa.canvas.event_generate('<Button-1>', x=round(x), y=round(y))
        self.raiz.update()

    def escolher_linha(self, tabela, codigo):
        tabela.arvore.selection_set(codigo)
        tabela.arvore.event_generate('<<TreeviewSelect>>')
        self.raiz.update()

    def combate_manual(self, codigo, escolher=None, **opcoes):
        """Clica nas opções reais durante o wait_variable da janela modal."""
        contagem = {'cliques': 0, 'expirou': False}

        def clicar():
            janela = self.app.combate
            if janela and janela.em_andamento:
                if janela.esperando:
                    if escolher:
                        escolher(janela, contagem)
                    else:
                        janela.botoes_escolha[0].invoke()
                    contagem['cliques'] += 1
                self.raiz.after(5, clicar)

        def destravar():
            janela = self.app.combate
            if janela and janela.em_andamento:
                contagem['expirou'] = True
                janela.automatico.set(True)
                janela.alternar_automatico()

        self.raiz.after(5, clicar)
        guarda = self.raiz.after(5000, destravar)
        resultado = self.app.iniciar_combate(codigo, **opcoes)
        self.raiz.after_cancel(guarda)
        self.assertFalse(contagem['expirou'], 'Os botões não conseguiram concluir a batalha.')
        self.assertGreater(contagem['cliques'], 0)
        return resultado

    def test_inicio_arquivo_padrao_e_mapa_com_todas_as_estradas(self):
        self.app = self.Aplicacao(self.raiz)
        self.app.nome.set('Ana')
        self.app.btn_iniciar.invoke()
        self.raiz.update()
        a = self.app
        self.assertEqual(a.jogo.jogador.nome, 'Ana')
        self.assertEqual(len(a.jogo.jogador.equipe), 3)
        self.assertEqual(set(a.mapa.centros), set(a.jogo.mundo.regiao.grafo.vertices))
        self.assertEqual(len(a.mapa.arestas_desenhadas), a.jogo.mundo.regiao.grafo.tamanho)
        esperados = Counter(str(p) for _, _, p in a.jogo.mundo.regiao.grafo.arestas)
        exibidos = Counter(a.mapa.canvas.itemcget(i, 'text') for i in a.mapa.rotulos_pesos)
        self.assertEqual(exibidos, esperados)
        for codigo in a.mapa.centros:
            ids = a.mapa.canvas.find_withtag('local:' + codigo)
            self.assertTrue(any(a.mapa.canvas.type(i) == 'rectangle' for i in ids))

    def test_clique_seleciona_sem_tempo_e_botao_percorre_aresta(self):
        a = self.abrir()
        self.clicar_local('PRA')
        self.assertEqual(a.mapa.selecionado, 'PRA')
        self.assertEqual(a.jogo.mundo.agora, 0)
        self.assertEqual(a.jogo.jogador.posicao, 'LAB')
        a.mapa.btn_passo.invoke()
        self.assertEqual(a.jogo.jogador.posicao, 'PRA')
        self.assertEqual(a.jogo.mundo.agora, 8)
        self.clicar_local('LAB')
        a.mapa.btn_passo.invoke()
        self.assertEqual(a.jogo.mundo.distancia_percorrida, 16)

    def test_rota_nao_adjacente_e_percorrida_aresta_por_aresta(self):
        a=self.abrir()
        self.clicar_local('EST')
        rota=a.jogo.rota('EST')['vertices']
        self.assertGreater(len(rota),2)
        self.assertFalse(a.mapa.btn_passo.instate(['disabled']))
        origem=a.jogo.jogador.posicao
        proximo=rota[1]
        a.mapa.btn_passo.invoke()
        self.assertEqual(a.jogo.jogador.posicao,proximo)
        self.assertEqual(a.mapa.selecionado,'EST')
        self.assertIsNotNone(a.jogo.mundo.regiao.grafo.peso(origem,proximo))

    def test_ovo_oculto_coletado_e_chocado_pelo_botao(self):
        j = jogo()
        j.mundo.itens['E01'].posicao = 'LAB'
        a = self.abrir(j)
        indice = next(i for i, item in enumerate(a.mapa._itens) if item.codigo == 'E01')
        a.mapa.itens.current(indice)
        a.mapa.btn_coletar.invoke()
        valores = a.equipe.ovos.arvore.item('E01', 'values')
        self.assertEqual(valores[1], 'Desconhecido')
        a.mapa.tempo.set('100')
        a.mapa.btn_esperar.invoke()
        self.assertEqual(len(j.jogador.equipe), 4)
        self.assertEqual(j.jogador.equipe[-1].xp, 0)
        self.assertEqual(a.equipe.ovos.arvore.get_children(), ())

    def test_excedente_exige_escolha_e_deposito_so_retira_no_laboratorio(self):
        j = jogo()
        for _ in range(4):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        a = self.abrir(j)
        pendente = j.jogador.pendente
        self.assertEqual(a.abas.select(), str(a.equipe))
        self.assertTrue(a.mapa.btn_esperar.instate(['disabled']))
        antigo = j.jogador.equipe[0]
        self.escolher_linha(a.equipe.ativos, antigo.codigo)
        a.equipe.btn_guardar.invoke()
        self.assertIsNone(j.jogador.pendente)
        self.assertEqual(len(j.jogador.equipe), 6)
        self.assertIn(pendente, j.jogador.equipe)
        self.assertIn(antigo, j.jogador.deposito)
        outro = j.jogador.equipe[0]
        self.escolher_linha(a.equipe.ativos, outro.codigo)
        a.equipe.btn_guardar.invoke()
        self.escolher_linha(a.equipe.deposito, antigo.codigo)
        a.equipe.btn_retirar.invoke()
        self.assertIn(antigo, j.jogador.equipe)
        self.assertEqual(len(j.jogador.equipe), 6)
        j.mover('PRA')
        a.atualizar()
        self.escolher_linha(a.equipe.deposito, outro.codigo)
        self.assertTrue(a.equipe.btn_retirar.instate(['disabled']))

    def test_pode_enviar_so_o_pokemon_recem_chegado(self):
        j = jogo()
        for _ in range(4):
            j.jogador.receber(j.mundo.criar_pokemon(ovo=True))
        equipe_anterior = list(j.jogador.equipe)
        novo = j.jogador.pendente
        a = self.abrir(j)
        a.equipe.btn_pendente.invoke()
        self.assertEqual(j.jogador.equipe, equipe_anterior)
        self.assertIn(novo, j.jogador.deposito)
        self.assertIsNone(j.jogador.pendente)

    def test_tabela_duplo_tipo_imunidade_e_clique_na_celula(self):
        a = self.abrir()
        a.abas.select(a.tipos)
        self.raiz.update()
        self.assertIn('= 4×', a.tipos.resultado.get())
        a.tipos.ataque.set('Elétrico')
        a.tipos.defesa1.set('Água')
        a.tipos.defesa2.set('Terra')
        a.tipos.calcular()
        self.assertIn('= 0×', a.tipos.resultado.get())
        from nucleo.tipos import TIPOS
        i, k = TIPOS.index('fogo'), TIPOS.index('planta')
        x, y = 110 + k * 47 + 23, 32 + i * 25 + 12
        a.tipos.canvas.event_generate('<Motion>', x=x, y=y)
        a.tipos.canvas.event_generate('<Button-1>', x=x, y=y)
        self.raiz.update()
        self.assertEqual(a.tipos.defesa2.get(), 'Nenhum')
        self.assertIn('= 2×', a.tipos.resultado.get())

    def test_batalha_automatica_informa_badge_e_retorna_ao_jogo(self):
        j = jogo(vantagens_tipos=False)
        posicionar(j, 'L-G01', 'G01')
        j.jogador.xp = 1000
        a = self.abrir(j)
        resultado = a.iniciar_combate('L-G01', automatico=True)
        self.assertTrue(resultado['venceu'])
        self.assertEqual(j.mundo.agora, 1)
        self.assertEqual(len(j.jogador.insignias), 1)
        self.assertIn('Insígnia recebida', a.combate.instrucao.get())
        self.assertTrue(a.ocupado)
        a.combate.btn_voltar.invoke()
        self.assertFalse(a.ocupado)
        self.assertIsNone(a.combate)

    def test_batalha_manual_aceita_escolha_de_pokemon_e_ataque(self):
        j = jogo(vantagens_tipos=False)
        posicionar(j, 'L-G01', 'G01')
        j.jogador.xp = 1000
        self.abrir(j)
        resultado = self.combate_manual('L-G01')
        self.assertTrue(resultado['venceu'])
        self.assertTrue(any(e.get('atacante') == j.jogador.equipe[0].codigo
                            for e in resultado['eventos']))
        self.assertEqual(j.mundo.agora, 1)

    def test_abandonar_captura_apos_um_ataque_preserva_dano_e_oculta_selvagem(self):
        j = jogo(vantagens_tipos=False)
        ator = posicionar(j, 'S01')
        ator.pokemon = pokemon('selvagem_controlado', ap=1, dp=1)
        self.abrir(j)

        def escolha(janela, contagem):
            if ator.pokemon.hp < 100:
                janela.btn_sair.invoke()
            else:
                janela.botoes_escolha[0].invoke()

        resultado = self.combate_manual('S01', escolha)
        self.assertFalse(resultado['capturado'])
        self.assertEqual(resultado['motivo'], 'captura_abandonada')
        self.assertLess(ator.pokemon.hp, 100)
        self.assertNotIn(ator, j.mundo.presentes())
        self.assertIn(j.jogador.codigo, ator.escondido_para)
        self.assertEqual(len(j.jogador.equipe), 3)
        self.assertEqual(j.mundo.agora, 1)

    def test_desafiado_pode_desistir_e_rocket_so_rouba_apos_vencer(self):
        j = jogo()
        ator = posicionar(j, 'R01')
        self.abrir(j)
        badges = set(j.jogador.insignias)
        self.assertEqual(ator.roubados, [])

        def escolha(janela, contagem):
            janela.btn_sair.invoke()

        resultado = self.combate_manual('R01', escolha, como_desafiado=True)
        self.assertFalse(resultado['venceu'])
        self.assertEqual(resultado['motivo'], 'desistencia_do_desafiado')
        self.assertIn('pokemon_roubado', resultado)
        self.assertEqual(len(j.jogador.equipe), 2)
        self.assertEqual(j.jogador.insignias, badges)
        self.assertEqual(len(ator.roubados), 1)
        self.assertIsNotNone(ator.invisivel_ate)
        self.assertNotIn(ator, j.mundo.presentes())
        self.app.combate.btn_voltar.invoke()
        self.app.mapa.tempo.set(str(ator.invisivel_ate - j.mundo.agora))
        self.app.mapa.btn_esperar.invoke()
        self.assertIsNone(ator.invisivel_ate)
        self.assertIsNotNone(ator.posicao)

    def test_protecao_do_laboratorio_e_pmc_aparece_nos_botoes(self):
        j = jogo()
        posicionar(j, 'T01', 'LAB')
        a = self.abrir(j)
        self.assertTrue(a.mapa.btn_batalha.instate(['disabled']))
        self.assertTrue(a.mapa.btn_defender.instate(['disabled']))
        posicionar(j, 'T01', 'PMC1')
        j.jogador.equipe[0].hp = 1
        a.atualizar()
        self.assertTrue(a.mapa.btn_batalha.instate(['disabled']))
        a.mapa.btn_curar.invoke()
        self.assertEqual(j.jogador.equipe[0].hp, 100)
        self.assertTrue(10 <= j.mundo.agora <= 50)

    def test_salvar_e_carregar_pelos_botoes_restaura_partida(self):
        a = self.abrir()
        with TemporaryDirectory() as tmp:
            caminho = str(Path(tmp) / 'partida.json')
            with patch('interface.janela.filedialog.asksaveasfilename', return_value=caminho):
                a.btn_salvar.invoke()
            self.assertTrue(Path(caminho).is_file())
            self.clicar_local('PRA')
            a.mapa.btn_passo.invoke()
            self.assertEqual(a.jogo.mundo.agora, 8)
            with patch('interface.janela.filedialog.askopenfilename', return_value=caminho):
                a.btn_carregar.invoke()
            self.raiz.update()
            self.assertEqual(a.jogo.mundo.agora, 0)
            self.assertEqual(a.jogo.jogador.posicao, 'LAB')

    def test_janela_menor_mantem_mapa_e_acesso_aos_botoes_por_rolagem(self):
        a = self.abrir()
        self.raiz.geometry('1000x680')
        self.raiz.update()
        c = a.mapa.canvas
        for x, y in a.mapa.centros.values():
            self.assertTrue(0 < x < c.winfo_width())
            self.assertTrue(0 < y < c.winfo_height())
        painel = a.mapa.painel_rolavel.canvas
        painel.yview_moveto(1)
        self.raiz.update()
        posicao = a.mapa.btn_planejar.winfo_rooty() - painel.winfo_rooty()
        self.assertTrue(0 <= posicao < painel.winfo_height())
        self.assertLessEqual(posicao + a.mapa.btn_planejar.winfo_height(), painel.winfo_height())

    def test_tempo_invalido_na_interface_nao_altera_partida(self):
        a = self.abrir()
        for valor in ('abc', '-1', '0'):
            a.mapa.tempo.set(valor)
            a.mapa.btn_esperar.invoke()
            self.assertEqual(a.jogo.mundo.agora, 0)
        self.assertTrue(a.mensagem.get())
