"""
Línea de comandos del agente (Fase 18).

    python -m src.agente "¿Qué modelo de volatilidad recomiendan los resultados?"

Requiere credenciales de la API de Anthropic en el entorno (por ejemplo la
variable ANTHROPIC_API_KEY). Nunca se guardan en el código.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(argv=None):
    import anthropic

    from src.agente.agente import Agente

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Agente de investigación del proyecto (Fase 18).")
    parser.add_argument("tarea", help="Pregunta o tarea en lenguaje natural.")
    parser.add_argument("--esfuerzo", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    try:
        resultado = Agente(esfuerzo=args.esfuerzo).ejecutar(args.tarea)
    except anthropic.AuthenticationError:
        print("Error: no hay credenciales válidas. Defina ANTHROPIC_API_KEY (ver README).", file=sys.stderr)
        return 2
    except anthropic.RateLimitError:
        print("Error: límite de uso de la API alcanzado; intente más tarde.", file=sys.stderr)
        return 3
    except anthropic.APIStatusError as exc:
        print(f"Error de la API ({exc.status_code}): {exc.message}", file=sys.stderr)
        return 4
    except anthropic.APIConnectionError:
        print("Error: no se pudo conectar con la API (revise la red).", file=sys.stderr)
        return 5
    print(resultado.texto)
    print(f"\n[{len(resultado.llamadas)} llamadas a herramientas | tokens: {resultado.uso} | "
          f"bitácora: {resultado.ruta_bitacora}]")
    return 0 if resultado.completado else 1


if __name__ == "__main__":
    sys.exit(main())
