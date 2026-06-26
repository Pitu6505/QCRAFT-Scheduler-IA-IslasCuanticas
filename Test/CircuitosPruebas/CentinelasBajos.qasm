OPENQASM 3.0;
include "stdgates.inc";

// Declaramos 3 qubits: q[0] y q[1] para datos, q[2] como CENTINELA
qubit[3] q;

// Declaramos registros clásicos separados
bit[2] c_data;
bit[1] c_flag;

// 1. Preparamos el centinela en |+> (muy sensible a interferencias magnéticas/fase)
h q[2];

// 2. Circuito de datos: Un estado de Bell simple
h q[0];
cx q[0], q[1];

// 3. Revertimos el centinela y lo medimos
h q[2];
c_flag[0] = measure q[2];

// 4. LÓGICA DINÁMICA: Si el centinela no detectó ruido (0), continuamos
if (c_flag[0] == 0) {
    x q[0];
}

// 5. Medidas finales de datos
c_data[0] = measure q[0];
c_data[1] = measure q[1];