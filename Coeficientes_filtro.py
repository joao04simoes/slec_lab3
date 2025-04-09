import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# Requisitos do filtro
f0 = 100        # Frequência central [Hz]
LB = 50         # Largura de banda [Hz]
fs = 4800       # Frequência de amostragem [Hz]

# Conversões
w0 = 2 * np.pi * f0              # Frequência angular central
BW = 2 * np.pi * LB              # Largura de banda angular

# Filtro analógico Chebyshev passa-baixo (1ª ordem, Ap = 3dB)
Ap = 3  # dB
rp = Ap
N = 1
b_lp, a_lp = signal.cheby1(N, rp, Wn=1, btype='low', analog=True, output='ba')

# Transformação para passa-banda analógica
b_bp, a_bp = signal.lp2bp(b_lp, a_lp, wo=w0, bw=BW)

# Transformação bilinear
b_z, a_z = signal.bilinear(b_bp, a_bp, fs=fs)

# Mostrar os coeficientes
print("Coeficientes do filtro digital (IIR):")
print("b =", b_z)
print("a =", a_z)
