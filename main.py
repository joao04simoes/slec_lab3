import T_Display
import math
import gc

# Variáveis Globais
tft = T_Display.TFT()
escala_horizontal = [5, 10, 20, 50]  # Escalas horizontais disponíveis (ms/div)
escala_vertical = [1, 2, 5, 10]      # Escalas verticais disponíveis (V/div)
fator = 1/29.3                       # Fator de calibração para conversão de tensão
width = 240                         # Largura do ecrã em pixels
height = 135                        # Altura do ecrã em pixels
index_vertical = 0                  # Índice atual da escala vertical
index_horizontal = 0                # Índice atual da escala horizontal


# Função que lê os dados do ADC, converte para tensão e desenha o sinal
def readDisplay(index_vertical, index_horizontal):

    # Leitura dos pontos do ADC
    pontos_adc = tft.read_adc(width, escala_horizontal[index_horizontal] * 10)

    Vmax = Vmin = Vmed = Vrms = 0
    pontosVolt = [0.0] * 240
    x = []
    y = []
    pixel_centro = ((height + 16) / 2)
    escala = (height - 16) / (6 * escala_vertical[index_vertical])
    for n in range(width):
        # Conversão do valor ADC para tensão com calibração
        V = 0.000391527 * pontos_adc[n] + 0.161379742
        # V = 0.00044028 * pontos_adc[n] + 0.091455  # equação dada
        V = V - 1
        V = V / fator
        pontosVolt[n] = V

        # Conversão da tensão para posição no ecrã (pixel)
        deslocamento = escala * V
        pixel = pixel_centro + deslocamento
        pixel = max(16, min(pixel, height))

        x.append(n)
        y.append(round(pixel))

        # Cálculo dos valores estatísticos
        if n == 0:
            Vmax = Vmin = Vmed = Vrms = V
        else:
            Vmed += V
            Vmax = max(Vmax, V)
            Vmin = min(Vmin, V)

    del pontos_adc
    gc.collect()
    # Apresentação do sinal no ecrã
    tft.display_set(tft.BLACK, 0, 0, width, height)
    tft.display_write_grid(0, 16, width, height-16,
                           10, 6, tft.GREY2, tft.GREY1)
    tft.set_wifi_icon(width - 16, 0)
    tft.display_write_str(tft.Arial16, "%d ms/div" %
                          escala_horizontal[index_horizontal], 90, 0)
    tft.display_write_str(tft.Arial16, "%d V/div" %
                          escala_vertical[index_vertical], 0, 0)
    tft.display_nline(tft.YELLOW, x, y)

    # Cálculo de Vrms e Vmed
    for i in range(len(pontosVolt)):
        Vrms += pontosVolt[i] ** 2
    Vrms = math.sqrt(Vrms / len(pontosVolt))
    Vmed /= len(pontosVolt)
    del x, y, V, pixel_centro, deslocamento, escala
    return Vmax, Vmin, Vmed, Vrms, pontosVolt


# Cálculo da Transformada rápida de Fourier (FFT)
def compute_fft(pontos_volt):
    NPoints = 240
    spectrum = [0.0] * NPoints

    for k in range(NPoints):
        auxcos = 0.0
        auxsen = 0.0

        for n in range(NPoints):
            angle = (2 * math.pi * k * n) / NPoints
            auxcos += pontos_volt[n] * math.cos(angle)
            auxsen -= pontos_volt[n] * math.sin(angle)

        V = complex(auxcos, auxsen)
        if k == 0 or k == NPoints // 2:
            spectrum[k] = abs(V) / NPoints
        else:
            spectrum[k] = (2 * abs(V)) / NPoints
    del V, auxcos, auxsen, angle, pontos_volt
    gc.collect()
    return spectrum


# Mostra o espectro de frequências no ecrã
def display_fft(spectrum):
    N = 240
    T = escala_horizontal[index_horizontal] * \
        10 / 1000  # Tempo total em segundos
    fs = N / T   # Frequência de amostragem
    escalaVertical = ((height - 16) / 6) / (escala_vertical[index_vertical]/2)
    x = []
    y = []

    # Escala de frequências para apresentação
    escala_frequencias = [240, 120, 60, 24]
    f_max = fs / 2
    f_div = escala_frequencias[-1]
    for f in escala_frequencias:
        if f <= f_max / 10:
            f_div = f
            break

    for i in range(len(spectrum) - 1):
        deslocamento = escalaVertical * spectrum[i]
        pixel = max(16, min(16 + deslocamento, height))
        x.extend([2 * i, 2 * i + 1])
        y.extend([round(pixel), round(pixel)])

    del spectrum, N, T, fs, escalaVertical, f_max
    gc.collect()

    # Desenho do gráfico do espectro
    tft.display_set(tft.BLACK, 0, 0, width, height)
    tft.display_write_grid(0, 16, width, height - 16,
                           10, 6, tft.BLACK, tft.GREY1)
    tft.set_wifi_icon(width - 16, 0)
    tft.display_write_str(tft.Arial16, "%d Hz/div" % f_div, 90, 0)
    tft.display_write_str(tft.Arial16, "%.1f V/div" %
                          (escala_vertical[index_vertical]/2), 0, 0)
    tft.display_nline(tft.MAGENTA, x, y)

    del x, y, deslocamento, pixel, f_div
    gc.collect()


# Determina automaticamente a melhor escala vertical para o sinal
def autoescala(signal):
    max_value = max(abs(min(signal)), abs(max(signal)))
    for i, escala in enumerate(escala_vertical):
        if max_value <= 3 * escala:
            return i
    return len(escala_vertical) - 1


# Aplica um filtro passa-banda ao sinal
def apply_bandpass_filter(signal, fs=4800):

    # Coeficientes do filtro IIR
    b0 = 0.03162969
    b1 = 0.0
    b2 = -0.03162969
    a0 = 1.0
    a1 = -1.92021863
    a2 = 0.93674062

    y = [0.0] * len(signal)
    x1 = x2 = y1 = y2 = signal[0]

    for i in range(len(signal)):
        x0 = signal[i]
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        y[i] = y0
        x2 = x1
        x1 = x0
        y2 = y1
        y1 = y0

    # Desenha o sinal filtrado no ecrã
    escalaV = escala_vertical[autoescala(y)]
    meio_tela = (height + 16) / 2
    escala_pixel = ((height - 16) / 2) / (3 * escalaV)
    pontosY = [round(meio_tela - s * escala_pixel) for s in y]

    tft.display_set(tft.BLACK, 0, 0, width, height)
    tft.display_write_grid(0, 16, width, height - 16,
                           10, 6, tft.GREY2, tft.GREY1)
    tft.set_wifi_icon(width - 16, 0)
    tft.display_write_str(tft.Arial16, "5 ms/div", 90, 0)
    tft.display_write_str(tft.Arial16, "%d V/div" % escalaV, 0, 0)
    tft.display_nline(tft.YELLOW, list(range(width)), pontosY)
    del y0, x0, x1, x2, y1, y2
    del signal, b0, b1, b2, a0, a1, a2
    del y
    gc.collect()
    return y


# Loop principal do programa
Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
    index_vertical, index_horizontal)
while tft.working():
    Button = tft.readButton()
    if Button != tft.NOTHING:
        print("Button pressed:", Button)

        if Button == 11:  # Botão 1 (1 clique)
            # Ler e apresentar o sinal
            gc.collect()
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)
            gc.collect()

        if Button == 12:  # Botão 1 (1 prolongado)
            # Enviar os dados por email
            gc.collect()
            corpo_mail = "Lista de %d pontos em %.2f segundos.\n Vmax = %.3fV \t\t Vmin = %.3fV \n Vmed = %.3fV \t\t Vrms = %.3fV\n" % (
                width, (escala_horizontal[index_horizontal]*10)*0.001, Vmax, Vmin, Vmed, Vrms)
            tft.send_mail(((escala_horizontal[index_horizontal]*10)*0.001)/width, pontosVolt, corpo_mail,
                          "joaosimoesxc@gmail.com")
            gc.collect()

        if Button == 13:  # Botão 1 (2 cliques)
            # Ler e aplicar filtro ao sinal
            gc.collect()
            Vmax, Vmin, Vmed, Vrms, PontosFiltro = readDisplay(
                index_vertical, index_horizontal)
            PontosFiltro = apply_bandpass_filter(PontosFiltro)
            gc.collect()

        if Button == 21:  # Botão 2 (1 clique)
            # Alterar escala vertical
            gc.collect()
            index_vertical = (index_vertical + 1) % len(escala_vertical)
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)
            gc.collect()

        if Button == 22:  # Botão 2 (1 prolongado)
            # Alterar escala horizontal
            gc.collect()
            index_horizontal = (index_horizontal + 1) % len(escala_horizontal)
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)
            gc.collect()

        if Button == 23:  # Botão 2 (2 cliques)
            # Calcular e mostrar o espectro de frequências
            gc.collect()
            spectrum = compute_fft(pontosVolt)
            display_fft(spectrum)
            gc.collect()
