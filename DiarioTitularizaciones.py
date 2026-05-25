import os
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from datetime import datetime
from config_utils import config_manager

# Obtener configuración de la base de datos
db_config = config_manager.get_database_config()

# Obtener ruta del archivo de titularizaciones
excel_file_path = config_manager.get_file_path('titularizaciones')
#print("-->")
#print(excel_file_path)
#print("<--")

# Obtener el año actual para la hoja de cálculo
aaaa = datetime.now().strftime("%Y")
#print ("<--")

df = pd.read_excel(excel_file_path, sheet_name=aaaa, skiprows=9, usecols=lambda x: x not in [0])




# Conéctate a la base de datos MySQL
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Elimina la tabla si existe
    cursor.execute("DROP TABLE titularizaciones_his_jao")

    # Crea una conexión a la base de datos usando sqlalchemy
    engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}/{database}'.format(**db_config))

    # Crea la tabla en la base de datos
    df[:0].to_sql('titularizaciones_his_jao', con=engine, if_exists='replace', index=False)  # Solo crea la estructura de la tabla

    # Carga los datos en la tabla de MySQL
    df.to_sql('titularizaciones_his_jao', con=engine, if_exists='append', index=False)

    # Confirma los cambios
#    cnx.commit()
    print("Datos cargados exitosamente en la tabla 'titularizaciones_his_jao'.")

    SQL = "delete from titularizaciones_his where fecha > '2026-01-01'; ALTER TABLE titularizaciones_his AUTO_INCREMENT = 1;"    
    SQL = SQL + "insert into titularizaciones_his (FECHA, EMISOR, PRECIO_PORC, RENDIMIENTO, PLAZO_DIAS, INTERES, VALOR_NOMINAL, EMISION, VALOR_EFECTIVO, VENCIMIENTO, PROCEDENCIA, MERCADO) SELECT `FECHA`, `EMISOR`, `PRECIO %%`, `RENDIMIENTO %%`, `PLAZO POR VENCER (DÍAS)`, `INTERÉS %%`, `VALOR NOMINAL (USD)`, `FECHA DE EMISIóN`, `VALOR EFECTIVO (USD)`, `FECHA VENCIMIENTO`, `PROCEDENCIA`, `TIPO DE MERCADO` FROM `titularizaciones_his_jao` where emisor is not null and fecha > (SELECT IFNULL(MAX(fecha), '2100-01-01') FROM titularizaciones_his)"    

    #print(SQL)
    
    cursor.execute(SQL)

    print("Actualizada la tabla 'titularizaciones_his'.")
   

    
    cnx.commit()

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    # Cierra la conexión
    if 'cnx' in locals() and cnx.is_connected():
        cursor.close()
        cnx.close()
        print("Conexión cerrada.")
