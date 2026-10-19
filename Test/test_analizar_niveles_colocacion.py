import io
import unittest
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import networkx as nx

from analizar_niveles_colocacion import estimate_swaps, extract_circuit
from analizar_niveles_colocacion import (
    analyze_circuits,
    load_url_entries,
    placement_strategy_name,
    selected_level_scenarios,
    summarize_swaps,
)
from placement_algorithm_logical import place_circuits_logical


class AnalyzePlacementLevelsTests(unittest.TestCase):
    def test_extract_circuit_reads_registers_and_multi_qubit_gates(self):
        source = """
from qiskit import QuantumRegister
qreg_q = QuantumRegister(3, 'q')
circuit = QuantumCircuit(qreg_q)
circuit.cx(qreg_q[0], qreg_q[2])
circuit.ccx(qreg_q[0], qreg_q[1], qreg_q[2])
circuit.h(qreg_q[1])
"""
        self.assertEqual(extract_circuit(source), (3, [(0, 1), (0, 2), (1, 2)]))

    def test_enabled_levels_report_the_strategy_that_placed_the_circuit(self):
        graph = nx.path_graph(5)
        nx.set_node_attributes(graph, 0.0, "noise")
        circuit = {"id": "c1", "size": 3, "edges": [(0, 1)]}
        actual_levels = {}

        placements, errors = place_circuits_logical(
            graph,
            [circuit],
            enabled_levels={3},
            placement_levels=actual_levels,
        )

        self.assertEqual(len(placements), 1)
        self.assertEqual(errors, [])
        self.assertEqual(actual_levels["c1"], 3)

    def test_quiet_mode_suppresses_algorithm_debug_output(self):
        graph = nx.path_graph(5)
        nx.set_node_attributes(graph, 0.0, "noise")
        output = io.StringIO()

        with redirect_stdout(output):
            place_circuits_logical(
                graph,
                [{"id": "c1", "size": 3, "edges": [(0, 1)]}],
                enabled_levels={3},
                verbose=False,
            )

        self.assertEqual(output.getvalue(), "")

    def test_strategy_names_explain_the_three_levels(self):
        self.assertEqual(placement_strategy_name(1), "VF2: isomorfismo exacto")
        self.assertEqual(placement_strategy_name(2), "Componentes conexas")
        self.assertEqual(placement_strategy_name(3), "Búsqueda normal")

    def test_can_select_only_level_three(self):
        self.assertEqual(selected_level_scenarios([3]), (("Solo nivel 3", {3}),))

    def test_swap_summary_sums_all_iterations_and_reports_missing_estimates(self):
        scenarios = [("Solo nivel 3", {3})]
        rows = [
            {"scenario": "Solo nivel 3", "estimated_swaps": 4},
            {"scenario": "Solo nivel 3", "estimated_swaps": 7},
            {"scenario": "Solo nivel 3", "estimated_swaps": ""},
        ]

        self.assertEqual(
            summarize_swaps(rows, scenarios),
            [{
                "scenario": "Solo nivel 3",
                "total_estimated_swaps": 11,
                "estimated_circuits": 2,
                "total_circuits": 3,
            }],
        )

    def test_distance_constraint_applies_between_circuits_in_same_batch(self):
        graph = nx.path_graph(3)
        nx.set_node_attributes(graph, 0.0, "noise")
        circuits = [
            {"id": "first", "size": 1, "edges": []},
            {"id": "second", "size": 1, "edges": []},
        ]

        placements, _ = place_circuits_logical(
            graph,
            circuits,
            enabled_levels={3},
            min_circuit_distance=2,
            verbose=False,
        )

        self.assertEqual(len(placements), 1)

    def test_unplaced_circuits_are_retried_in_a_fresh_iteration(self):
        graph = nx.path_graph(3)
        nx.set_node_attributes(graph, 0.0, "noise")
        circuits = [
            {
                "id": f"circuit_{index}",
                "name": f"circuit_{index}",
                "url": f"https://raw.githubusercontent.com/user/repo/main/{index}.py",
                "qubits": 1,
                "edges": [],
            }
            for index in range(5)
        ]

        rows = analyze_circuits(circuits, graph, [("Solo nivel 3", {3})])

        self.assertEqual(len(rows), 5)
        self.assertEqual([row["iteration"] for row in rows], [1, 1, 1, 2, 2])
        self.assertTrue(all(row["status"] == "OK" for row in rows))

    def test_component_strategy_is_reported_as_level_two(self):
        graph = nx.path_graph(5)
        nx.set_node_attributes(graph, 0.0, "noise")
        circuit = {"id": "c1", "size": 3, "edges": [(0, 1)]}
        actual_levels = {}

        placements, errors = place_circuits_logical(
            graph,
            [circuit],
            enabled_levels={2, 3},
            placement_levels=actual_levels,
        )

        self.assertEqual(len(placements), 1)
        self.assertEqual(errors, [])
        self.assertEqual(actual_levels["c1"], 2)

    def test_isomorphic_placement_keeps_logical_qubit_order(self):
        graph = nx.Graph()
        graph.add_nodes_from([1, 0, 2, 3])
        graph.add_edges_from([(0, 1), (0, 2), (0, 3)])
        nx.set_node_attributes(graph, 0.0, "noise")
        circuit = {"id": "c1", "size": 3, "edges": [(0, 1), (0, 2)]}

        placements, errors = place_circuits_logical(
            graph,
            [circuit],
            enabled_levels={1},
        )

        self.assertEqual(errors, [])
        physical_qubits = placements[0][1]
        self.assertTrue(graph.has_edge(physical_qubits[0], physical_qubits[1]))
        self.assertTrue(graph.has_edge(physical_qubits[0], physical_qubits[2]))

    def test_swap_estimate_uses_shortest_path_distance(self):
        graph = nx.path_graph(4)
        self.assertEqual(estimate_swaps(graph, [0, 3], [(0, 1)]), (2, []))

    def test_invalid_level_is_rejected(self):
        with self.assertRaises(ValueError):
            place_circuits_logical(nx.path_graph(2), [], enabled_levels={4})

    def test_loads_url_dictionary_from_scheduler_script_without_importing_it(self):
        source = '''urls = {
    "Popular-pe-1": "https://raw.githubusercontent.com/user/repo/main/pe.py",
    "Popular-pe-2": "https://raw.githubusercontent.com/user/repo/main/pe2.py",
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scheduler_urls.py"
            path.write_text(source, encoding="utf-8")

            self.assertEqual(
                load_url_entries(path),
                [
                    ("Popular-pe-1", "https://raw.githubusercontent.com/user/repo/main/pe.py"),
                    ("Popular-pe-2", "https://raw.githubusercontent.com/user/repo/main/pe2.py"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
