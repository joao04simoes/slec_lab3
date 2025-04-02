
import T_Display
import math

# Variáveis Globais
tft = T_Display.TFT()  # Instancia um objeto da classe TFT
escala_horizontal = [5, 10, 20, 50]  # escala temporal, em ms
escala_vertical = [1, 2, 5, 10]  # escala da amplitude, em volts
fator = 1/29.3  # Fator do divisor resistivo
width = 240
height = 135
index_vertical = 2  # posição default escala vertical
index_horizontal = 1  # posição default escala horizontal


def read_and_display(index_vertical, index_horizontal, readOnly):

    pontos_adc = tft.read_adc(width, escala_horizontal[index_horizontal]*10)
    tensoes_aux = pontos_adc
    Vmax = 0
    Vmin = 0
    Vmed = 0
    Vrms = 0
    x = []
    y = []
    for n in range(width):
        # Converte valor do ADC em Volt
        # V = 0.00044028 * pontos_adc[n] + 0.091455 (Calibração do professor)
        V = 0.0004313133*pontos_adc[n]+0.10264  # Nossa calibração
        V = V - 1                                 # Tensão entrada de referência de 1V
        V = V / fator                             # Entra com o efeito do div. resistivo
        tensoes_aux[n] = V
        pixel = (height-16)/2 + (
            (height-16)/(6*escala_vertical[index_vertical]))*V
        if pixel > height-16:  # Quando o valor excede o espaço vertical superior simplesmente fica no limite superior do display
            pixel = height-16
        if pixel < 0:   # Quando o valor excede o espaço vertical inferior simplesmente fica no limite inferior do display
            pixel = 0

        x.append(n)
        y.append(round(pixel))

        if n == 0:       # Caso seja o primeiro ponto
            Vmax = Vmin = Vmed = Vrms = V
        else:
            Vmed += V
            if V > Vmax:
                Vmax = V
            if V < Vmin:
                Vmin = V

    # se so quisermos ler (readOnly = 1), nao imprimimos no display
    if readOnly == 0:
        # reiniciar display
        tft.display_set(tft.BLACK, 0, 0, width, height)  # Apaga display
        tft.display_write_grid(0, 0, width, height-16, 10, 6,
                               tft.GREY1, tft.GREY2)  # Desenha grelha
        tft.set_wifi_icon(width-16, height-16)  # Adiciona wifi icon
        # escrever a escala no topo
        tft.display_write_str(tft.Arial16, "%d ms/div" %
                              escala_horizontal[index_horizontal], 0, height-16)
        tft.display_write_str(tft.Arial16, "%d V/div" %
                              escala_vertical[index_vertical], 45+35, height-16)
        # imprimir a forma de onda
        tft.display_nline(tft.YELLOW, x, y)

    Vrms = 0
    for i in range(len(tensoes_aux)):
        Vrms += (tensoes_aux[i]*tensoes_aux[i])

    Vrms = math.sqrt(Vrms / len(tensoes_aux))

    Vmed /= 240  # Divide pelo número de amostras

    return Vmax, Vmin, Vmed, Vrms, tensoes_aux


def get_period(index_vertical, index_horizontal):

    zeros_array = []
    period_array = []
    periodo = 0
    max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
        index_vertical, index_horizontal, 1)

    for i in range(len(tensoes_array)-1):  # percorrer todas as tensões
        isSaved = 0  # flag que nos indica se um valor dentro desse intervalo ja foi guardado ou nao
        if (med_value >= 0):  # se tiver offset DC positivo ou nulo
            while (tensoes_array[i] < 1.1*med_value and tensoes_array[i] > 0.9*med_value):
                if (isSaved == 0):
                    zeros_array.append(i)  # guardar os zeros consecutivos
                    isSaved = 1

                else:
                    isSaved += 1  # guardar os zeros consecutivos
                    if (i < len(tensoes_array)-1):
                        i += 1
                    else:
                        break

        elif (med_value < 0):  # se tiver offset DC negativo
            while (tensoes_array[i] > 1.1*med_value and tensoes_array[i] < 0.9*med_value):
                if (isSaved == 0):
                    zeros_array.append(i)  # guardar os zeros consecutivos
                    isSaved = 1

                else:
                    isSaved += 1
                    if (i < len(tensoes_array)-1):
                        i += 1
                    else:
                        break
        i = i - isSaved

    # percorrer o array dos zeros e calcular meio periodo fazendo a diferenca entre eles
    for i in range(len(zeros_array)):
        meio_periodo = zeros_array[i]-zeros_array[i-1]
        period_array.append(meio_periodo)

    for i in range(1, len(period_array)):
        periodo += period_array[i]

    avg_aux = periodo/(len(period_array)-1)
    periodo = (
        2*(avg_aux*(escala_horizontal[index_horizontal]*(10/width))))*0.001  # periodo em segundos

    return periodo


def auto_scale(escala, x, div):

    aux_array = []
    for i in range(len(escala)):  # percorrer o array da escala
        if (escala[i]*div >= x):  # selecionar as escalas possíveis
            aux_array.append(escala[i])

    # retornar a escala que mais se aproxima de x
    return find_closest_number(aux_array, x, div)


def find_closest_number(array, x, div):

    closest = None
    min_diff = float('inf')  # inicializar com um valor muito grande (infinito)
    for i in range(len(array)):
        product = array[i] * div
        diff = abs(product - x)  # calcular a diferença

        # encontrar a diferença minima de forma a encontrar a escala mais adequada
        if diff < min_diff:
            min_diff = diff
            closest = array[i]

    # encontrar o indice ao qual essa escala corresponde
    if (div == 3):  # trata-se da escala vertical
        for i in range(len(escala_vertical)):
            if (closest == escala_vertical[i]):
                return i
    else:  # trata-se da escala horizontal
        for i in range(len(escala_horizontal)):
            if (closest == escala_horizontal[i]):
                return i


# Programa principal (main)
max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
    index_vertical, index_horizontal, 0)

while tft.working():  # Ciclo principal do programa
    but = tft.readButton()                          # Lê estado dos botões
    if but != tft.NOTHING:
        print("Button pressed:", but)
        if but == 11:  # Button 1 click - Repete função
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 0)

        if but == 12:  # Button 2 click prolongado - Envia mail
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 1)

            corpo_mail = "Lista de %d pontos em %.2f segundos.\n Vmax = %.3fV \t\t Vmin = %.3fV \n Vmed = %.3fV \t\t Vrms = %.3fV\n" % (
                width, (escala_horizontal[index_horizontal]*10)*0.001, max_value, min_value, med_value, rms_value)
            tft.send_mail(((escala_horizontal[index_horizontal]*10)*0.001)/width, tensoes_array, corpo_mail,
                          "verrali380@gmail.com")

        # Button 1 duplo click - Apresenta os valores de medida e o periodo (adicionalmente)
        if but == 13:
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 1)

            T = get_period(index_vertical, index_horizontal)
            tft.display_set(tft.BLACK, 0, 0, width, height)  # apagar display
            # escrever as medidas no display
            tft.display_write_str(
                tft.Arial16, "Medidas", 70, 90, tft.CYAN)
            tft.display_write_str(
                tft.Arial16, "Min: %.2f V" % min_value, 5, 50)
            tft.display_write_str(tft.Arial16, "Max: %.2f V" %
                                  max_value, 130, 50)
            tft.display_write_str(
                tft.Arial16, "Med: %.2f V" % med_value, 5, 70)
            tft.display_write_str(tft.Arial16, "RMS: %.2f V" %
                                  rms_value, 130, 70)
            tft.display_write_str(tft.Arial16, "T = %.2f ms" %
                                  (T*1000), 5, 30)

        if but == 21:            # Button 2 click - Alterar a escala vertical
            index_vertical += 1
            if (index_vertical > 3):  # alterar a escala vertical de forma circular
                index_vertical = 0
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 0)

        if but == 22:            # Button 2 click prolongado - Alterar a escala horizontal
            index_horizontal += 1
            if (index_horizontal > 3):  # alterar a escala horizontal de forma circular
                index_horizontal = 0
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 0)

        if but == 23:  # Button 2 double click - Autoscale
            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 1)
            # se tiver amplitude AC, todos os valores sao diferentes
            if (abs(max_value) != abs(min_value) != abs(rms_value) != abs(med_value)):
                T = get_period(index_vertical, index_horizontal)

                if (med_value >= 0):
                    index_vertical = auto_scale(
                        escala_vertical, 1.1*(max_value), 3)  # dar um pequeno offset de 10% na amplitude maxima para compensar o ruido
                    # 3divs porque a amplitude começa em 0

                if (med_value < 0.1):
                    index_vertical = auto_scale(
                        escala_vertical, abs(1.1*(min_value)), 3)
                # para se ver no minimo 2 periodos quando se faz autoscale (em milisegundos)
                num_periodos = 2*T*1000
                index_horizontal = auto_scale(
                    escala_horizontal, num_periodos, 10)

            max_value, min_value, med_value, rms_value, tensoes_array = read_and_display(
                index_vertical, index_horizontal, 0)
