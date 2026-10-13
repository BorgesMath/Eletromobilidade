"""Normalização de texto para chaves de junção e comparação de rótulos."""

from __future__ import annotations

import re
import unicodedata

_ESPACOS = re.compile(r"\s+")
_ESPACO_BARRA = re.compile(r"\s*/\s*")
_PLUG_IN = re.compile(r"PLUG\s*-?\s*IN")


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: object) -> str:
    """Caixa alta, sem acentos, espaços colapsados. ``None``/NaN viram ``""``."""
    if texto is None or (isinstance(texto, float) and texto != texto):
        return ""
    texto = remover_acentos(str(texto)).upper().strip()
    return _ESPACOS.sub(" ", texto)


def normalizar_combustivel(texto: object) -> str:
    """Forma canônica de um rótulo de combustível do RENAVAM.

    Remove espaços ao redor de ``/`` e unifica as grafias de "plug-in"
    (``PLUGIN``, ``PLUG IN``, ``PLUG-IN``), que variam entre meses.
    """
    texto = _ESPACO_BARRA.sub("/", normalizar(texto))
    return _PLUG_IN.sub("PLUG-IN", texto)


def normalizar_coluna(nome: object) -> str:
    """Nome de coluna em ``snake_case`` ASCII (``"Qtd. Veículos"`` -> ``"qtd_veiculos"``)."""
    texto = normalizar(nome).lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")
