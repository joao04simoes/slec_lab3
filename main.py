import T_Display
import math


# Variáveis Globais
tft = T_Display.TFT()  # Instancia um objeto da classe TFT
escala_horizontal = [5, 10, 20, 50]  # escala temporal, em ms
escala_vertical = [1, 2, 5, 10]  # escala da amplitude, em volts
fator = 1/29.3  # Fator do divisor resistivo
width = 240
height = 135
index_vertical = 0  # posição default escala vertical
index_horizontal = 0  # posição default escala horizontal


def readDisplay(index_vertical, index_horizontal):
    pontos_adc = tft.read_adc(width, escala_horizontal[index_horizontal] * 10)

    Vmax = Vmin = Vmed = Vrms = 0
    pontosVolt = [0.0] * 240
    x = []
    y = []

    for n in range(width):
        # Converte valor do ADC em Volt
        V = 0.00044028 * pontos_adc[n] + 0.091455
        V = V - 1  # Ajuste da referência de entrada (1V)
        V = V / fator  # Considera o efeito do divisor resistivo
        pontosVolt[n] = V

        # Calcula a posição base do pixel ao centro
        pixel_centro = (height - 16) / 2

        # Calcula o deslocamento do pixel baseado em V e na escala vertical
        escala = (height - 16) / (6 * escala_vertical[index_vertical])
        deslocamento = escala * V

        # Define a posição final do pixel
        pixel = pixel_centro + deslocamento

        # Garante que o pixel permanece dentro dos limites do display
        pixel = max(0, min(pixel, height - 16))

        x.append(n)
        y.append(round(pixel))

        # Atualiza os valores de Vmax, Vmin, Vmed e Vrms
        if n == 0:
            Vmax = Vmin = Vmed = Vrms = V
        else:
            Vmed += V
            Vmax = max(Vmax, V)
            Vmin = min(Vmin, V)

    # reiniciar display
    tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
    tft.display_write_grid(0, 0, width, height-16, 10, 6,
                           tft.GREY2, tft.GREY1)  # Desenha grelha
    tft.set_wifi_icon(width-16, height-16)  # Adiciona wifi icon
    # escrever a escala no topo
    tft.display_write_str(tft.Arial16, "%d ms/div" %
                          escala_horizontal[index_horizontal], 0, height-16)
    tft.display_write_str(tft.Arial16, "%d V/div" %
                          escala_vertical[index_vertical], 45+35, height-16)
    # imprimir a forma de onda
    tft.display_nline(tft.YELLOW, x, y)
    # Cálculo do valor eficaz (Vrms)
    for i in range(len(pontosVolt)):
        Vrms += pontosVolt[i] ** 2

    Vrms = math.sqrt(Vrms / len(pontosVolt))

    # Média dos valores medidos
    Vmed /= len(pontosVolt)

    return Vmax, Vmin, Vmed, Vrms, pontosVolt


def compute_dft(signal):
    N = len(signal)
    X = [0] * (N // 2 + 1)  # Apenas metade dos pontos são necessários
    for k in range(N // 2 + 1):
        real = sum(signal[n] * math.cos(-2 * math.pi * k * n / N)
                   for n in range(N))
        imag = sum(signal[n] * math.sin(-2 * math.pi * k * n / N)
                   for n in range(N))
        X[k] = (2 if 0 < k < N // 2 else 1) * \
            math.sqrt(real**2 + imag**2) / N
    return X


def display_dft(spectrum):

    N = 240  # Número de amostras
    T = escala_horizontal[index_horizontal] * \
        10 / 1000  # Tempo total em segundos
    fs = N / T
    pixel_centro = (height - 16) / 2
    max_magnitude = max(spectrum) if max(
        spectrum) > 0 else 1  # Evita divisão por zero
    # Ajusta escala com base no valor máximo
    escala_vertical = (height - 16) / 6
    x = []
    y = []

    # Definição da escala de frequência conforme o enunciado
    escala_frequencias = [240, 120, 60, 24]  # Hz/div
    f_max = fs / 2  # Frequência máxima (Nyquist)
    f_div = next((f for f in escala_frequencias if f <=
                  f_max / 10), escala_frequencias[-1])

    for i in range(len(spectrum) - 1):  # Ignorar o último ponto
        deslocamento = escala_vertical * spectrum[i]
        pixel = max(0, min(0 + deslocamento, height - 16))
        x.extend([2 * i, 2 * i + 1])  # Duplicação dos pontos
        y.extend([round(pixel), round(pixel)])

    tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
    tft.display_write_grid(0, 0, width, height - 16,
                           10, 6, tft.GREY1, tft.GREY2)

    tft.set_wifi_icon(width - 16, height - 16)
    tft.display_write_str(tft.Arial16, "%d Hz/div" % f_div, 0, height - 16)
    tft.display_write_str(tft.Arial16, "1 V/div", 45+35, height-16)
    tft.display_nline(tft.YELLOW, x, y)


def apply_bandpass_filter(signal):
    # Parâmetros do filtro Chebyshev de 1ª ordem
    f0 = 100  # Hz (frequência central)
    LB = 50  # Hz (largura de banda)
    fs = 4800  # Hz (frequência de amostragem)
    w0 = 2 * math.pi * f0 / fs
    bw = 2 * math.pi * LB / fs

    # Coeficientes do filtro bilinear
    alpha = math.tan(bw / 2)
    a0 = 1 + alpha
    a1 = -2 * math.cos(w0) / a0
    a2 = (1 - alpha) / a0
    b0 = alpha / a0
    b1 = 0
    b2 = -alpha / a0

    # Aplicação do filtro IIR
    filtered_signal = [0] * len(signal)
    for n in range(2, len(signal)):
        filtered_signal[n] = b0 * signal[n] + b1 * signal[n-1] + b2 * \
            signal[n-2] - a1 * filtered_signal[n-1] - a2 * filtered_signal[n-2]
    return filtered_signal


while tft.working():
    Button = tft.readButton()
    if Button != tft.NOTHING:
        print("Button pressed:", Button)
        if Button == 11:  # butão 1 click
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)

        if Button == 12:
            Vmax, Vmin, Vmed, Vmed, pontosVolt = readDisplay(
                index_vertical, index_horizontal)

            corpo_mail = "Lista de %d pontos em %.2f segundos.\n Vmax = %.3fV \t\t Vmin = %.3fV \n Vmed = %.3fV \t\t Vrms = %.3fV\n" % (
                width, (escala_horizontal[index_horizontal]*10)*0.001, Vmax, Vmin, Vmed, Vmed)
            tft.send_mail(((escala_horizontal[index_horizontal]*10)*0.001)/width, pontosVolt, corpo_mail,
                          "joaosimoesxc@gmail.com")

        if Button == 13:
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)
            filtered_signal = apply_bandpass_filter(pontosVolt)
            tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
            tft.display_write_grid(0, 0, width, height-16,
                                   10, 6, tft.GREY1, tft.GREY2)
            tft.set_wifi_icon(width-16, height-16)
            tft.display_write_str(tft.Arial16, "5ms/div", 0, height-16)
            tft.display_nline(tft.YELLOW, list(range(width)), [
                round((height-16)/2 + s) for s in filtered_signal])

        if Button == 21:
            index_vertical += 1
            if index_vertical > 3:
                index_vertical = 0
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)

        if Button == 22:
            index_horizontal += 1
            if index_horizontal > 3:
                index_horizontal = 0
            Vmax, Vmin, Vmed, Vrms, pontosVolt = readDisplay(
                index_vertical, index_horizontal)
        if Button == 23:
            spectrum = compute_dft(pontosVolt)
            display_dft(spectrum)
