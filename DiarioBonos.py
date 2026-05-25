import os
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from config_utils import config_manager
from datetime import datetime

# Obtener configuración de la base de datos
db_config = config_manager.get_database_config()

# Obtener ruta del archivo de bonos
excel_file_path = config_manager.get_file_path('bonos')
#print("-->")
#print(excel_file_path)
#print("<--")

# Obtener el año actual para la hoja de cálculo
aaaa = datetime.now().strftime("%Y")

# Leer el archivo Excel
df = pd.read_excel(excel_file_path, sheet_name=aaaa, skiprows=11, usecols=lambda x: x not in [0])




# Conéctate a la base de datos MySQL
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Elimina la tabla si existe
    cursor.execute("DROP TABLE bonds_his_jao")

    # Crea una conexión a la base de datos usando sqlalchemy
    engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}/{database}'.format(**db_config))

    # Crea la tabla en la base de datos
    df[:0].to_sql('bonds_his_jao', con=engine, if_exists='replace', index=False)  # Solo crea la estructura de la tabla

    # Carga los datos en la tabla de MySQL
    df.to_sql('bonds_his_jao', con=engine, if_exists='append', index=False)

    # Confirma los cambios
#    cnx.commit()
    print("Datos cargados exitosamente en la tabla 'bonds_his_jao'.")

    SQL = "insert into bond_his (FECHA, DECRETO, PRECIO_PORC, RENDIMIENTO_PORC, PLAZO_POR_VENCER, TASA_INTERES, VALOR_NOMINAL, VALOR_EFECTIVO, FECHA_EMISION, FECHA_VENCIMIENTO, PROCEDENCIA, TIPO, TIPO_MERCADO_1) SELECT `FECHA`, `DECRETO`, `PRECIO %%`, `RENDIMIENTO %%`, `PLAZO POR VENCER(DÍAS)`, `INTERÉS %%`, `VALOR NOMINAL (USD)`, `VALOR EFECTIVO (USD)`, `FECHA EMISION`, `FECHA VENCIMIENTO`, `PROCEDENCIA`, `TIPO`, `TIPO DE MERCADO` FROM `bonds_his_jao` where fecha > (SELECT IFNULL(MAX(fecha), '2100-01-01') FROM bond_his)"    

    print(SQL)
    
    cursor.execute(SQL)

    print("Actualizada la tabla 'Bond_his'.")
   

    
    cnx.commit()

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    # Cierra la conexión
    if 'cnx' in locals() and cnx.is_connected():
        cursor.close()
        cnx.close()
        print("Conexión cerrada.")
