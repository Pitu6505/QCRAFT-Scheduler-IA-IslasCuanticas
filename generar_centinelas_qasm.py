"""Genera plantillas OpenQASM para los modos centinela del scheduler.

Los modos estaticos se expresan en OpenQASM 2.0 porque solo necesitan
preparacion, ejecucion y medida al final.

Los modos dinamicos se expresan en OpenQASM 3.0 porque requieren delay,
medicion intermedia y, en algunos casos, control condicional.
"""

from __future__ import annotations

import argparse


STATIC_HEADER = """OPENQASM 2.0;
include "qelib1.inc";
"""


DYNAMIC_HEADER = """OPENQASM 3.0;
include "stdgates.inc";
"""


def static_template(mode: str, sentinel_prep: str, closing: str) -> str:
    return f"""{STATIC_HEADER}
qreg q[2];
creg c[2];

// Modo: {mode}
// q[0] = qubit de datos
// q[1] = centinela

// Preparacion del centinela
{sentinel_prep}

// Circuito logico de datos
h q[0];
cx q[0], q[1];

// Cierre del centinela
{closing}

measure q[1] -> c[1];
measure q[0] -> c[0];
"""


def dynamic_global_template(mode: str, sentinel_prep: str) -> str:
    return f"""{DYNAMIC_HEADER}
qubit[2] q;
bit[1] c_flag;
bit[1] data_out;

// Modo: {mode}
// q[0] = datos, q[1] = centinela

{sentinel_prep}
delay[1000ns] q[1];
barrier q;

c_flag[0] = measure q[1];

if (c_flag[0] == 0) {{
    h q[0];
    cx q[0], q[1];
    data_out[0] = measure q[0];
}}
"""


def dynamic_local_template(mode: str, sentinel_prep: str) -> str:
    return f"""{DYNAMIC_HEADER}
qubit[2] q;
bit[1] c_flag;
bit[1] data_out;

// Modo: {mode}
// q[0] = datos, q[1] = centinela

{sentinel_prep}

// Primera mitad del circuito
h q[0];
barrier q;

// Medicion intermedia del centinela
c_flag[0] = measure q[1];

if (c_flag[0] == 0) {{
    // Segunda mitad condicionada
    cx q[0], q[1];
    data_out[0] = measure q[0];
}}
"""


def build_catalog() -> dict[str, str]:
    catalog: dict[str, str] = {}

    catalog["standard"] = static_template(
        "standard",
        "h q[1];",
        "h q[1];",
    )
    catalog["robust"] = static_template(
        "robust",
        "h q[1];",
        "x q[1];\nh q[1];",
    )
    catalog["t1_decay"] = static_template(
        "t1_decay",
        "x q[1];",
        "x q[1];",
    )
    catalog["dd"] = static_template(
        "dd",
        "h q[1];",
        "x q[1];\ny q[1];\nx q[1];\ny q[1];\nh q[1];",
    )
    catalog["completo"] = static_template(
        "completo",
        "h q[1];",
        "x q[1];\nh q[1];",
    )

    catalog["standard_local"] = static_template(
        "standard_local",
        "h q[1];",
        "h q[1];",
    )
    catalog["robust_local"] = static_template(
        "robust_local",
        "h q[1];",
        "x q[1];\nh q[1];",
    )
    catalog["t1_decay_local"] = static_template(
        "t1_decay_local",
        "x q[1];",
        "x q[1];",
    )
    catalog["dd_local"] = static_template(
        "dd_local",
        "h q[1];",
        "x q[1];\ny q[1];\nx q[1];\ny q[1];\nh q[1];",
    )
    catalog["completo_local"] = static_template(
        "completo_local",
        "h q[1];",
        "x q[1];\nh q[1];",
    )

    catalog["dynamic_t1"] = dynamic_global_template(
        "dynamic_t1",
        "x q[1];",
    )
    catalog["dynamic_ramsey"] = dynamic_global_template(
        "dynamic_ramsey",
        "h q[1];",
    )
    catalog["dynamic_local_t1"] = dynamic_local_template(
        "dynamic_local_t1",
        "x q[1];",
    )
    catalog["dynamic_local_ramsey"] = dynamic_local_template(
        "dynamic_local_ramsey",
        "h q[1];",
    )

    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Imprime plantillas OpenQASM para los modos centinela del scheduler."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        help="Nombre del modo o 'all' para imprimirlos todos.",
    )
    args = parser.parse_args()

    catalog = build_catalog()

    if args.mode != "all" and args.mode not in catalog:
        valid = ", ".join(sorted(catalog))
        raise SystemExit(f"Modo desconocido: {args.mode}\nModos validos: {valid}")

    modes = sorted(catalog) if args.mode == "all" else [args.mode]
    for mode in modes:
        print("=" * 80)
        print(f"{mode.upper()}")
        print("=" * 80)
        print(catalog[mode].strip())
        print()


if __name__ == "__main__":
    main()