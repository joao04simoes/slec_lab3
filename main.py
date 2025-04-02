import T_Display

# Variáveis Globais
tft = T_Display.TFT()  # Instancia um objeto da classe TFT
escala_horizontal = [5, 10, 20, 50]  # escala temporal, em ms
escala_vertical = [1, 2, 5, 10]  # escala da amplitude, em volts
fator = 1/29.3  # Fator do divisor resistivo
width = 240
height = 135
index_vertical = 1  # posição default escala vertical
index_horizontal = 2  # posição default escala horizontal


def normaliza_angulo(x):
    while x > 3.1416:
        x -= 2 * 3.1416
    while x < -3.1416:
        x += 2 * 3.1416
    return x


def fatorial(n):
    resultado = 1
    for i in range(1, n + 1):
        resultado *= i
    return resultado


def seno(x, termos=10):
    if x < 0:
        return -seno(-x, termos)  # Usa a propriedade de função ímpar

    resultado = 0
    for n in range(termos):
        termo = ((-1) ** n) * (x ** (2 * n + 1)) / fatorial(2 * n + 1)
        resultado += termo
    return resultado


def cosseno(x, termos=10):
    x = abs(x)  # Usa a propriedade de função par

    resultado = 0
    for n in range(termos):
        termo = ((-1) ** n) * (x ** (2 * n)) / fatorial(2 * n)
        resultado += termo
    return resultado


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
        pixel_centro = ((height + 16) / 2)

        # Calcula o deslocamento do pixel baseado em V e na escala vertical
        escala = (height - 16) / (6 * escala_vertical[index_vertical])
        deslocamento = escala * V

        # Define a posição final do pixel
        pixel = pixel_centro + deslocamento

        # Garante que o pixel permanece dentro dos limites do display
        pixel = max(16, min(pixel, height))

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
    tft.display_write_grid(0, 16, width, height-16, 10, 6,
                           tft.GREY2, tft.GREY1)  # Desenha grelha
    tft.set_wifi_icon(width - 16, 0)  # Adiciona wifi icon
    # escrever a escala no topo
    tft.display_write_str(tft.Arial16, "%d ms/div" %
                          escala_horizontal[index_horizontal], 90, 0)
    tft.display_write_str(tft.Arial16, "%d V/div" %
                          escala_vertical[index_vertical], 0, 0)
    # imprimir a forma de onda
    tft.display_nline(tft.YELLOW, x, y)
    # Cálculo do valor eficaz (Vrms)
    for i in range(len(pontosVolt)):
        Vrms += pontosVolt[i] ** 2

    Vrms = (Vrms / len(pontosVolt))**0.5

    # Média dos valores medidos
    Vmed /= len(pontosVolt)

    return Vmax, Vmin, Vmed, Vrms, pontosVolt


def compute_dft(signal):
    N = len(signal)
    X = [0] * (N // 2 + 1)  # Apenas metade dos pontos são necessários
    for k in range(N // 2 + 1):
        real = sum(signal[n] * cosseno(normaliza_angulo(-2 * 3.1416 * k * n / N))
                   for n in range(N))
        imag = sum(signal[n] * seno(normaliza_angulo(-2 * 3.1416 * k * n / N))
                   for n in range(N))
        X[k] = (2 if 0 < k < N // 2 else 1) * \
            ((real**2 + imag**2)**0.5) / N
    return X


def display_dft(spectrum):

    N = 240  # Número de amostras
    T = escala_horizontal[index_horizontal] * \
        10 / 1000  # Tempo total em segundos
    fs = N / T
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
        pixel = max(16, min(16 + deslocamento, height - 16))
        x.extend([2 * i, 2 * i + 1])  # Duplicação dos pontos
        y.extend([round(pixel), round(pixel)])

    tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
    tft.display_write_grid(0, 16, width, height - 16,
                           10, 6, tft.BLACK, tft.GREY1)
    tft.set_wifi_icon(width - 16, 0)
    tft.display_write_str(tft.Arial16, "%d Hz/div" % f_div, 0, 0)
    tft.display_write_str(tft.Arial16, "1 V/div", 90, 0)
    tft.display_nline(tft.MAGENTA, x, y)


def apply_bandpass_filter(signal, fs=4800, f0=100, bw=50):

    dt = 1 / fs
    w0 = 2 * 3.141592653589793 * f0  # Frequência angular central
    wb = 2 * 3.141592653589793 * bw   # Largura de banda angular

    # Fator de transformação bilinear
    T = 2 / dt
    w0_d = (2 / dt) * (w0 / (T + w0))  # Conversão bilinear

    # Coeficientes do filtro IIR (passa-banda)
    alpha = w0_d / (wb + w0_d)

    y = [0] * len(signal)  # Inicializa o sinal filtrado

    for i in range(1, len(signal)):
        y[i] = alpha * (signal[i] - signal[i - 1]) + (1 - alpha) * y[i - 1]

    escalaV = escala_vertical[autoescala(y)]

    meio_tela = (height + 16) / 2  # Centro da tela
    escala_pixel = ((height - 16)/2) / (3 * escalaV)  # Pixels por V/div

    pontosY = [round(meio_tela + (s * escala_pixel))
               for s in y]

    # Atualiza o display
    tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
    tft.display_write_grid(
        0, 16, width, height-16, 10, 6, tft.GREY2, tft.GREY1)  # Desenha grelha
    tft.set_wifi_icon(width - 16, 0)  # Adiciona ícone Wi-Fi
    # Escreve escala horizontal
    tft.display_write_str(tft.Arial16, "%d ms/div" %
                          escala_horizontal[index_horizontal], 90, 0)
    tft.display_write_str(tft.Arial16, "%d V/div" %
                          escalaV, 0, 0)  # Escreve escala vertical

    # Plota o sinal no display
    tft.display_nline(tft.YELLOW, list(range(width)), pontosY)

    return y


def autoescala(signal):
    max_value = max(abs(min(signal)), abs(max(signal)))

    for i, escala in enumerate(escala_vertical):
        if max_value <= 3 * escala:
            return i

    return len(escala_vertical) - 1   # Retorna a escala máxima se necessário


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
