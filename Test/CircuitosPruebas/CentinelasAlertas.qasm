OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
bit[2] c_data;
bit[1] c_flag;

// 1. Preparamos el centinela en alta sensibilidad
h q[2];

// 2. Circuito de datos: Inyección masiva de pulsos de microondas
h q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
cx q[0], q[1];
cx q[1], q[0];
// En un simulador local no pasará nada, pero en hardware real esto genera mucho crosstalk

// 3. Revertimos el centinela y lo medimos
h q[2];
c_flag[0] = measure q[2];

// 4. LÓGICA DINÁMICA: La instrucción de abajo será ABORTADA por el hardware 
// en una gran cantidad de shots porque c_flag[0] será 1 debido al ruido térmico.
if (c_flag[0] == 0) {
    x q[0];
}

// 5. Medidas finales de datos
c_data[0] = measure q[0];
c_data[1] = measure q[1];