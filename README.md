# Rumo à Liga Pokémon

Projeto desenvolvido para a disciplina de **Algoritmos em Grafos**.

A ideia do trabalho é representar uma região como um grafo ponderado e usar os
algoritmos estudados na disciplina para controlar viagens, rotas e planejamento
da jornada.

O tema Pokémon foi usado apenas como contexto para o projeto. Este trabalho tem
finalidade acadêmica e não comercial e não possui vínculo com Nintendo,
The Pokémon Company ou Game Freak.

## Objetivo

O jogador começa no laboratório e precisa viajar pela região, enfrentar líderes
de ginásio, conseguir **8 insígnias** e chegar ao estádio para se inscrever na
Liga antes do prazo.

Durante a jornada também é possível encontrar Pokémon selvagens, treinadores,
ovos, ervas e a Equipe Rocket.

## Requisitos

- Python 3.10 ou superior
- Tkinter
- Ambiente gráfico para abrir a interface

O jogo usa somente módulos da biblioteca padrão do Python.

## Como executar

Entre na pasta do projeto e execute:

```bash
python main.py
```

No Linux, dependendo da instalação:

```bash
python3 main.py
```

Para conferir se o Tkinter está funcionando:

```bash
python -m tkinter
```

No Ubuntu/Debian, caso seja necessário:

```bash
sudo apt install python3-tk
```

No Arch Linux:

```bash
sudo pacman -S tk
```

## Como jogar

Ao iniciar a partida, informe o nome do treinador, escolha o arquivo da região e
uma semente aleatória. O arquivo `dados/regiao.json` já vem selecionado por
padrão.

A semente serve para repetir a mesma sequência de sorteios. A semente `3` é a
padrão atual do projeto, mas pode ser alterada ou sorteada pela própria
interface.

### Mapa e viagens

Clique em um local do mapa para selecionar um destino. O caminho calculado
aparece destacado.

- **Uma estrada** percorre apenas a próxima aresta da rota.
- **Seguir rota** percorre o caminho calculado até o destino, enquanto a jornada
  puder continuar.
- Os números mostrados nas estradas representam os pesos das arestas.

### Batalhas

Nos locais do mapa podem aparecer Pokémon selvagens, treinadores, líderes e a
Equipe Rocket.

- Pokémon selvagens podem ser capturados.
- Treinadores comuns podem aceitar ou recusar um desafio.
- Líderes de ginásio entregam uma insígnia quando são derrotados.
- Alguns líderes são móveis e podem não estar no ginásio naquele momento.
- Laboratórios e Centros Médicos são locais protegidos e não permitem batalhas.

Nas batalhas é possível escolher os Pokémon, ataques e substituições manualmente
ou usar as escolhas automáticas.

### Equipe

A aba **Minha equipe** mostra os Pokémon ativos, HP, XP, AP, DP, fase, tipos e
ataques.

O treinador pode carregar no máximo 6 Pokémon ativos. Quando surge uma sétima
posição, é necessário escolher qual Pokémon será enviado ao professor.

Pokémon enviados ao depósito podem ser retirados novamente no laboratório,
desde que exista espaço na equipe.

### Inventário

A aba **Inventário** mostra informações da jornada, como:

- quantidade de ervas coletadas;
- ovos;
- Pokémon ativos;
- Pokémon no depósito;
- insígnias conquistadas.

As ervas são usadas imediatamente quando são coletadas e recuperam HP dos
Pokémon conscientes.

### Centros Médicos

Nos Centros Médicos é possível tratar a equipe. Os tratamentos são realizados
em paralelo e consomem tempo da jornada.

### Inscrição na Liga

Depois de conseguir 8 insígnias, vá até o estádio e clique em
**Inscrever na Liga**.

Se a inscrição for feita dentro do prazo, a jornada é concluída e uma tela final
mostra os dados da partida.

Se o prazo terminar antes da inscrição, o treinador fica inapto para aquela
edição da Liga.

## Algoritmos usados

Os principais algoritmos de grafos utilizados no projeto são:

- **BFS**, para buscas no grafo;
- **Dijkstra**, para calcular caminhos mínimos;
- **Programação dinâmica**, usada no planejamento dos ginásios restantes.

O grafo é armazenado com listas de adjacência e as estradas podem ser percorridas
nos dois sentidos.

## Mapa padrão

O mapa padrão possui:

- 20 vértices;
- 25 arestas;
- 8 ginásios;
- 3 Centros Médicos;
- 1 laboratório;
- 1 estádio;
- 42 Pokémon selvagens;
- 7 treinadores comuns;
- 7 ovos;
- 20 ervas;
- 1 Equipe Rocket.

A soma dos pesos das arestas é `247` e o prazo da região é `2964`, equivalente
a `12 × 247`.

Os líderes dos ginásios G03 e G06 são móveis.

## Organização do projeto

```text
rumo_liga_pokemon/
├── dados/
│   └── regiao.json
├── interface/
│   ├── combate.py
│   ├── componentes.py
│   ├── equipe.py
│   ├── inventario.py
│   ├── janela.py
│   ├── mapa.py
│   └── tipos.py
├── nucleo/
│   ├── algoritmos.py
│   ├── batalha.py
│   ├── erros.py
│   ├── grafo.py
│   ├── jogo.py
│   ├── mundo.py
│   ├── pokemon.py
│   ├── regiao.py
│   ├── salvamento.py
│   ├── tipos.py
│   └── treinador.py
├── Saves/
├── testes/
├── main.py
└── README.md
```

### Principais arquivos

| Arquivo | Função |
| --- | --- |
| `main.py` | Inicia o programa. |
| `nucleo/grafo.py` | Estrutura do grafo e suas arestas. |
| `nucleo/algoritmos.py` | BFS, Dijkstra e planejamento. |
| `nucleo/mundo.py` | Estado da região, eventos e movimentação dos NPCs. |
| `nucleo/batalha.py` | Regras das batalhas. |
| `nucleo/jogo.py` | Ações principais da jornada. |
| `nucleo/salvamento.py` | Salvamento e carregamento das partidas. |
| `interface/janela.py` | Janela principal e controle das abas. |
| `interface/mapa.py` | Mapa, rotas e ações de cada local. |
| `interface/equipe.py` | Equipe, ovos e depósito. |
| `interface/inventario.py` | Inventário e insígnias. |
| `interface/tipos.py` | Tabela de tipos. |
| `interface/combate.py` | Interface das batalhas. |
| `dados/regiao.json` | Dados do mapa, espécies, ginásios e regras. |

## Arquivo da região

O mapa é carregado a partir de `dados/regiao.json`.

Nesse arquivo ficam informações como:

- vértices;
- arestas e seus pesos;
- ginásios;
- quantidade de personagens e itens;
- espécies e evoluções;
- ataques;
- tabela de tipos;
- regras da região;
- prazo da jornada;
- posições usadas para desenhar o mapa.

As arestas são declaradas apenas uma vez no JSON. O programa cria a ligação nos
dois sentidos.

Exemplo:

```json
["LAB", "PRA", 8]
```

Também é possível criar outro arquivo de região e escolhê-lo pela tela inicial.

## Salvamento

Os saves são arquivos JSON.

Ao salvar ou carregar uma partida, a janela começa na pasta:

```text
Saves/
```

mas é possível escolher outro local normalmente.

O save mantém os dados necessários para continuar a jornada, incluindo equipe,
tempo, eventos e estado dos personagens.

## Testes

Os testes podem ser executados de duas formas.

### unittest

Não precisa instalar nada além do Python:

```bash
python -m unittest discover -s testes -v
```

No Linux:

```bash
python3 -m unittest discover -s testes -v
```

### pytest

O `pytest` é opcional.

Para instalar:

```bash
python -m pip install pytest
```

Depois:

```bash
python -m pytest testes -v
```

No Linux:

```bash
python3 -m pytest testes -v
```

Os testes verificam partes como algoritmos, batalhas, evolução, arquivos,
salvamento, simulações da jornada e ações da interface.

Os testes da interface precisam de Tkinter e de uma sessão gráfica disponível.

## Observação

BFS, Dijkstra e a programação dinâmica usados no trabalho foram implementados
no próprio projeto. Foram utilizadas estruturas da biblioteca padrão, como
`deque` e `heapq`, mas não bibliotecas prontas de grafos como NetworkX.
