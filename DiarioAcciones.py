import os
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from datetime import datetime
from config_utils import config_manager

# Obtener configuración de la base de datos
db_config = config_manager.get_database_config()

# Obtener ruta del archivo de acciones
excel_file_path = config_manager.get_file_path('acciones')
#print("-->")
#print(excel_file_path)
#print("<--")

# Obtener el año actual para la hoja de cálculo
aaaa = datetime.now().strftime("%Y")
#print ("-->")
#print (excel_file_path)
#print ("<--")


# Carga los datos desde la pestaña "2023" del archivo Excel, omitiendo la primera columna (skipcols=[0])
df = pd.read_excel(excel_file_path, sheet_name=aaaa, skiprows=8, usecols=lambda x: x not in [0])


# Conéctate a la base de datos MySQL
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Elimina la tabla si existe
    cursor.execute("DROP TABLE shares_jao")

    # Crea una conexión a la base de datos usando sqlalchemy
    engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}/{database}'.format(**db_config))

    # Crea la tabla en la base de datos
    df[:0].to_sql('shares_jao', con=engine, if_exists='replace', index=False)  # Solo crea la estructura de la tabla

    # Carga los datos en la tabla de MySQL
    df.to_sql('shares_jao', con=engine, if_exists='append', index=False)

    # Confirma los cambios
#    cnx.commit()
    print("Datos cargados exitosamente en la tabla 'shares_jao'.")

    SQL = "insert into shares (`SHA_ISSUER_ID`, `SHA_DATE`, `SHA_ISSUER`, `SHA_TYPE`, `SHA_NOMINAL_VALUE`, `SHA_PRICE`, `SHA_NUMBER`, `SHA_CASH_VALUE`, `SHA_PROVENANCE`) select '1', FECHA, EMISOR, VALOR, `VALOR NOMINAL` , PRECIO, `NUMERO ACCIONES`, `VALOR EFECTIVO`,PROCEDENCIA FROM shares_jao where `NUMERO ACCIONES` <> 0 AND fecha >= (SELECT DATE_ADD(IFNULL(MAX(SHA_DATE), '2100-01-01'), INTERVAL 1 DAY) FROM shares)"    
    print(SQL)
    
    cursor.execute(SQL)
 
    
    SQL = "UPDATE shares A JOIN dictionary D ON A.SHA_ISSUER = D.DIC_VALUE SET A.SHA_ISSUER_ID = D.DIC_ID"

    cursor.execute(SQL)

    print("Actualizada la tabla 'shares'.")


    # cursor.execute(SQL)
    
    cnx.commit()

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    # Cierra la conexión
    if 'cnx' in locals() and cnx.is_connected():
        cursor.close()
        cnx.close()
        print("Conexión cerrada.")
