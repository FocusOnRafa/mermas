import mysql.connector
import openai #recuerden cambiar motor aca al importar
from datetime import datetime
from collections import deque
import sys

# Configuración de la conexión a MariaDB
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345',
    'database': 'mermas'
}

# Configurar el cliente de OpenAI con tu API Key
client = openai.OpenAI(api_key="AQUI PRUEBN SUS KEYS/ O SI NO CMABIEN DE MOTOR DE IA")

# Estructura de la tabla principal
ESTRUCTURA_TABLA  = """
TABLA mermasdb
codigo_producto int(11),
descripcion varchar(100),
negocio varchar(50),
seccion varchar(50),
linea varchar(50),
categoria varchar(50),
abastecimiento varchar(30),
comuna varchar(50),
region varchar(20),
tienda varchar(50),
zonal varchar(50),
mes varchar(20),
año int(11),
semestre varchar(20),
fecha date,
motivo varchar(50),
ubicacion_motivo varchar(50),
merma_unidad float,
merma_monto float,
merma_unidad_p float,
merma_monto_p float,
tamano_producto varchar(20),
es_a_granel tinyint(1),
nivel_merma varchar(10),
dia_semana int(11),
estacion varchar(15),
tipo_producto_estacional tinyint(1),
riesgo_perecibilidad varchar(10),
valor_perdida varchar(10),
riesgo_categoria varchar(10)
"""

EJEMPLOS_PREGUNTAS = [
    "¿Cuáles son las mermas más altas por región?",
    "¿Qué productos tuvieron mayor merma en el mes de enero?",
    "¿Cuánto fue el monto total de mermas en 2023?",
    "¿En qué tienda se registró la mayor merma de unidades?",
    "¿Cuáles son las categorías con mayor riesgo de perecibilidad?"
]

# Historial de las últimas 5 preguntas y respuestas
historial = deque(maxlen=5)

def obtener_consulta_sql(pregunta):
    prompt = f""" Dada la siguiente estructura de tabla :
    {ESTRUCTURA_TABLA}
    Y la siguiente consulta en lenguaje natural:
    \"{pregunta}\"

    Genera una consulta SQL para el motor mariadb que responda la pregunta del usuario. Sigue estas pautas:
    0. La tabla se llama mermasdb.
    1. Utiliza LIKE para búsquedas de texto, permitiendo coincidencias parciales.
    2. Para hacer búsqueda insensible a mayúsculas y minúsculas utiliza LOWER() para tratar todos los datos en minúsculas.
    3. Al buscar descripciones o nombres utiliza LIKE con comodines %.
    4. Si la consulta puede devolver múltiples resultados, usa GROUP BY para agrupar resultados similares.
    5. Incluye COUNT(*) o COUNT(DISTINCT...) cuando sea apropiado para contar resultados.
    6. Usa IFNULL cuando sea necesario para manejar valores null.
    7. Limita los resultados a 100 filas como máximo. Usa limit 100.
    8. Incluye order by para ordenar los resultados de manera lógica.
    9. Si la consulta utiliza cálculos numéricos, usa funciones como MIN, MAX, AVG, SUM, u otras que se requieran y que sean válidas en SQL.
    10. Si la consulta es sobre fechas, usa funciones apropiadas en Mysql para esto.
    11. En la respuesta puedes incorporar datos de la tabla que sean útiles para que el usuario final tenga una respuesta clara.
    12. No generes bajo ningún caso instrucciones de tipo DDL (Create, drop) o DML diferentes de Select.

    Responde solo con la consulta SQL, sin agregar nada más."""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0
    )
    return response.choices[0].message.content.strip()

def ejecutar_sql(sql):
    try:
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary = True)
        cur.execute(sql)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results 
    except mysql.connector.Error as err:
        raise Exception(f"Error de base de datos: {err}")

def generar_respuesta_final(resultado_sql,pregunta):
    prompt = f"""Dada la siguiente pregunta:
    \"{pregunta}\"
    Y los siguientes resultados de la consulta SQL:
    {resultado_sql}
    Genera una respuesta en lenguage natural, entendible para un usuario de negocio en el ámbito universitario y de RRHH con las siguientes reglas:
    1. Responde directamente sin hacer mención a SQL u otros términos técnicos.
    2. Usa un lenguaje claro, profesional, como si estuvieses conversando con el usuario que efectúa la pregunta.
    3. Presenta la información de manera organizada y fácil de entender. Trata de estructurar los datos y ordenarlos al momento de responder.
    4. Si los datos son limitados o incompletos, proporciona una respuesta con la información disponible y no pidas disculpas.
    5. Utiliza términos propios del ámbito universitario cuando sea posible.
    6. Si los datos incluyen cifras monetarias, utiliza el símbolo $ e incorpora separadores de miles. Los datos monetarios son siempre en pesos chilenos.
    7. No agregues información que no esté explicitamente en los datos obtenidos.
    8. Si la respuesta no puede ser respondida, indica amablemente que no hay datos disponibles e invita a una nueva pregunta.
    9. No agregues a menos que se solicite un análisis de resultados. Sólo entrégalos de manera entendible sin emitir opinión a menos que se solicite.
    10. No hagas supuestos ni hagas sugerencias con los datos. Esto es muy importante.
    11. Envía el resultado de manera precisa y estructurada sin un análisis salvo que se solicite.
    12. Los resultados son utilizados en una conversión tipo chat, por tanto no saludes ni te despidas. Limita a entregar los resultados de manera clara.
    13. IMPORTANTE: Nunca menciones datos técnicos ni pidas disculpas.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0
    )
    return response.choices[0].message.content.strip()

def mostrar_tabla(resultados):
    if not resultados:
        print("No hay datos para mostrar.")
        return
    columnas = resultados[0].keys()
    ancho_col = {col: max(len(str(col)), max(len(str(fila[col])) for fila in resultados)) for col in columnas}
    encabezado = " | ".join(f"{col:<{ancho_col[col]}}" for col in columnas)
    print(encabezado)
    print("-" * len(encabezado))
    for fila in resultados:
        print(" | ".join(f"{str(fila[col]):<{ancho_col[col]}}" for col in columnas))

def mostrar_ejemplos():
    print("Ejemplos de preguntas que puedes hacer:")
    for ej in EJEMPLOS_PREGUNTAS:
        print(f"- {ej}")

def mostrar_historial():
    if not historial:
        print("No hay historial disponible.")
        return
    print("Últimas preguntas y respuestas:")
    for i, (preg, resp) in enumerate(historial, 1):
        print(f"{i}. Pregunta: {preg}\n   Respuesta: {resp}\n")

def main():
    while True:
        pregunta = input("Ingrese una pregunta (o 'salir', 'ejemplos', 'historial'): ").strip()
        if pregunta.lower() == 'salir':
            print("Chat finalizado")
            break
        if pregunta.lower() == 'ejemplos':
            mostrar_ejemplos()
            continue
        if pregunta.lower() == 'historial':
            mostrar_historial()
            continue
        if not pregunta or len(pregunta) < 5:
            print("Por favor, ingresa una pregunta más específica. Escribe 'ejemplos' para ver ejemplos de preguntas.")
            continue
        try:
            sql_query = obtener_consulta_sql(pregunta)
            print(f"SQL GENERADO : {sql_query}")
            sql_resultados = ejecutar_sql(sql_query)
            if isinstance(sql_resultados, list) and sql_resultados and isinstance(sql_resultados[0], dict):
                mostrar_tabla(sql_resultados)
            respuesta_final = generar_respuesta_final(sql_resultados, pregunta)
            print(f"RESPUESTA : {respuesta_final}")
            historial.append((pregunta, respuesta_final))
        except Exception as e:
            print(f"Ocurrió un error: {e}")
            print("Si el problema persiste, revisa la conexión a la base de datos o la pregunta realizada.")

if __name__ == "__main__":
    main()