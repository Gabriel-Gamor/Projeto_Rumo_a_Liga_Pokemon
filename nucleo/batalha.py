"""Motor de turnos independente da interface e da movimentação do mapa.

O desafiado começa. O desafiante não pode abandonar duelo entre treinadores.
Capturas podem ser abandonadas; uma interrupção não é contada como empate.
"""

from dataclasses import dataclass, field

from nucleo.erros import AcaoInvalida


class SolicitarDesistencia(Exception):
    """Pedido vindo de uma estratégia; o motor valida se o papel permite sair."""


class _EncerrarEscolha(Exception):
    def __init__(self, lado):
        self.lado = lado


class EstrategiaAutomatica:
    """Escolhe um Pokémon saudável e o ataque de maior dano imediato."""

    def escolher_pokemon(self, opcoes, contexto):
        return max(opcoes, key=lambda p: (p.hp, p.ap + p.dp, p.codigo))

    def escolher_ataque(self, atacante, defensor, tabela):
        return max(atacante.ataques,
                   key=lambda a: tabela.multiplicador(a.tipo, defensor.tipos))

    def desistir(self, turno, captura=False):
        return False


@dataclass
class ResultadoBatalha:
    vencedor: int | None
    motivo: str
    turnos: int
    participantes: list = field(default_factory=list)
    eventos: list = field(default_factory=list)


def probabilidades(xp_atacante, xp_defensor):
    """Detalhe não especificado no PDF: crescimento linear com teto explícito."""
    diferenca = abs(xp_atacante - xp_defensor)
    return min(0.35, diferenca / 1000), min(0.40, diferenca / 1000)


def executar_ataque(atacante, defensor, golpe, xp_treinador_a,
                    xp_treinador_d, tabela, rng, agora):
    if golpe not in atacante.ataques:
        raise AcaoInvalida("Esse Pokémon não conhece o ataque escolhido.")
    esquiva, critico = probabilidades(atacante.xp, defensor.xp)
    base = max(0.0, atacante.ap + xp_treinador_a - defensor.dp - xp_treinador_d)
    fator = tabela.multiplicador(golpe.tipo, defensor.tipos)
    desviou = rng.random() < esquiva
    duplo = not desviou and rng.random() < critico
    dano = 0.0 if desviou else base * fator * (2 if duplo else 1)
    hp_antes = defensor.hp
    defensor.receber_dano(dano, agora, rng)
    return {"atacante": atacante.codigo, "nome_atacante": atacante.nome,
            "defensor": defensor.codigo, "nome_defensor": defensor.nome,
            "golpe": golpe.nome, "tipo": golpe.tipo,
            "dano": round(hp_antes - defensor.hp, 2), "hp": round(defensor.hp, 2),
            "esquiva": desviou, "critico": duplo, "multiplicador": fator}


def batalhar(desafiante, desafiado, equipe_a, equipe_b, tabela, rng, agora,
             estrategia_a=None, estrategia_b=None, captura=False,
             limite_turnos=2000, limite_sem_dano=100, treino=False, observador=None):
    """Mutação das equipes; o chamador avança o relógio UMA unidade ao terminar.

    No limite de segurança, o desafiado automático concede a disputa entre
    treinadores; uma tentativa de captura é abandonada. Não se inventa dano.
    """
    estrategias = [estrategia_a or EstrategiaAutomatica(),
                   estrategia_b or EstrategiaAutomatica()]
    if type(limite_turnos) is not int or limite_turnos < 1 or limite_sem_dano < 1:
        raise AcaoInvalida("Limites de segurança devem ser positivos.")
    equipes = [list(equipe_a), list(equipe_b)]
    treinadores = [desafiante, desafiado]
    if not all(equipes) or any(not p.consciente for equipe in equipes for p in equipe):
        raise AcaoInvalida("Uma batalha deve começar com equipes conscientes.")
    ids = [p.codigo for equipe in equipes for p in equipe]
    if len(ids) != len(set(ids)):
        raise AcaoInvalida("As equipes precisam de Pokémon distintos.")
    if not captura and not treino and (len(equipe_a) != 3 or len(equipe_b) != 3):
        raise AcaoInvalida("Duelos entre treinadores usam exatamente três Pokémon por lado.")
    xp_treinadores = [t.xp if t else 0 for t in treinadores]
    participantes, eventos, ativos = {}, [], []

    def avisar(evento):
        if observador is not None:
            observador(evento)

    def escolher(lado, metodo, *args, **kwargs):
        try:
            return getattr(estrategias[lado], metodo)(*args, **kwargs)
        except SolicitarDesistencia:
            if (captura and lado == 0) or (not captura and lado == 1):
                raise _EncerrarEscolha(lado) from None
            raise AcaoInvalida("O desafiante não pode abandonar uma batalha entre treinadores.") from None

    lado, sem_dano, vencedor, motivo, turno = 1, 0, None, "", 0
    try:
        for lado in (0, 1):
            p = escolher(lado, "escolher_pokemon", equipes[lado], "início")
            if p not in equipes[lado]:
                raise AcaoInvalida("Pokémon escolhido não pertence ao grupo da batalha.")
            ativos.append(p)
            participantes[p.codigo] = p
            avisar({"entrada":p.codigo, "lado":lado, "nome":p.nome})
        lado = 1
        for turno in range(1, limite_turnos + 1):
            if not captura and escolher(1, "desistir", turno, captura=False):
                vencedor, motivo = 0, "desistencia_do_desafiado"
                break
            if captura and escolher(0, "desistir", turno, captura=True):
                motivo = "captura_abandonada"
                break
            atacante, defensor = ativos[lado], ativos[1 - lado]
            xp_a, xp_d = atacante.xp, defensor.xp
            ataque = escolher(lado, "escolher_ataque", atacante, defensor, tabela)
            hp_anterior = defensor.hp
            evento = executar_ataque(atacante, defensor, ataque,
                                     xp_treinadores[lado], xp_treinadores[1 - lado],
                                     tabela, rng, agora)
            evento["turno"] = turno
            eventos.append(evento)
            avisar(evento)
            # O arredondamento do texto de saída não interfere na dinâmica.
            sem_dano = sem_dano + 1 if defensor.hp == hp_anterior else 0
            if not defensor.consciente:
                evolucoes = atacante.vencer_duelo(xp_d, xp_a)
                defensor.ganhar_xp(3)
                evento = {"nocaute":defensor.codigo, "vencedor_duelo":atacante.codigo,
                          "evolucoes":evolucoes}
                eventos.append(evento)
                avisar(evento)
                restantes = [p for p in equipes[1 - lado] if p.consciente]
                if not restantes:
                    vencedor, motivo = lado, "nocaute"
                    break
                novo = escolher(1 - lado, "escolher_pokemon", restantes, "substituição")
                if novo not in restantes:
                    raise AcaoInvalida("Substituto inválido.")
                ativos[1 - lado] = novo
                participantes[novo.codigo] = novo
                avisar({"entrada":novo.codigo, "lado":1-lado, "nome":novo.nome})
            if sem_dano >= limite_sem_dano:
                motivo = "captura_abandonada_sem_progresso" if captura else "desistencia_do_desafiado_sem_progresso"
                vencedor = None if captura else 0
                break
            lado = 1 - lado
        else:
            turno = limite_turnos
            motivo = "captura_abandonada_por_limite" if captura else "desistencia_do_desafiado_por_limite"
            vencedor = None if captura else 0
    except _EncerrarEscolha:
        vencedor = None if captura else 0
        motivo = "captura_abandonada" if captura else "desistencia_do_desafiado"
    if not captura and not treino and vencedor is not None:
        ganhou = treinadores[vencedor]
        ganhou.xp += 3 if xp_treinadores[1 - vencedor] >= xp_treinadores[vencedor] else 1
    if captura and vencedor == 0:
        # Bônus de captura, além do resultado dos duelos individuais.
        desafiante.xp += 3
        for pokemon in participantes.values():
            pokemon.ganhar_xp(3)
    return ResultadoBatalha(vencedor, motivo, turno, list(participantes), eventos)
