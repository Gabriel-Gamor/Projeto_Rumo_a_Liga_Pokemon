"""Erros esperados, apresentados ao usuário sem traceback."""


class ErroProjeto(ValueError):
    """Classe base para uma entrada inválida ou ação não permitida."""


class ErroFormato(ErroProjeto):
    """Arquivo de região inconsistente."""


class AcaoInvalida(ErroProjeto):
    """A regra da jornada impede a ação solicitada."""
