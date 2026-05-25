import os
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from datetime import datetime
from config_utils import config_manager
import time

# Obtener configuración de la base de datos
db_config = config_manager.get_database_config()

# Obtener ruta del archivo de dividendos
# excel_file_path = config_manager.get_file_path('dividendos')
#print("-->")
#print(excel_file_path)
#print("<--")

# Ruta del archivo Excel
aaaa=time.strftime("%Y")
mm=time.strftime("%m")
dd=time.strftime("%d")
dia=time.strftime("%A")
carpeta='008_RentaVariable'
# nombre = 'dividendos'
ext = '.xls'
directorioBase='C:\\Users\\super\\DATOS\\004. DatosBVQ\\'
nombre = 'dividendos'
excel_file_path = directorioBase+aaaa+'_'+mm+'\\'+aaaa+'_'+mm+'_'+dd+'\\'+carpeta+'\\'+nombre+'_'+aaaa+'_'+mm+'_'+dd+ext
print ("-->")
print (excel_file_path)
print ("<--")



# Obtener el año actual para la hoja de cálculo
# aaaa = datetime.now().strftime("%Y")
# print ("<--")

aaaa = "DIVIDENDOS"

df = pd.read_excel(excel_file_path, sheet_name=aaaa, skiprows=6, usecols=lambda x: x not in [0])




# Conéctate a la base de datos MySQL
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Elimina la tabla si existe
    cursor.execute("DROP TABLE dividendos_his_jao")
    cursor.execute("DROP TABLE dividendos_his")

    # Crea una conexión a la base de datos usando sqlalchemy
    engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}/{database}'.format(**db_config))

    # Crea la tabla en la base de datos
    df[:0].to_sql('dividendos_his_jao', con=engine, if_exists='replace', index=False)  # Solo crea la estructura de la tabla

    # Carga los datos en la tabla de MySQL
    df.to_sql('dividendos_his_jao', con=engine, if_exists='append', index=False)

    # Confirma los cambios
#    cnx.commit()
    print("Datos cargados exitosamente en la tabla 'dividendos_his_jao'.")

#    SQL = "delete from dividendos_his where fecha > '2026-01-01'; ALTER TABLE dividendos_his AUTO_INCREMENT = 1;"    
#    SQL = SQL + "insert into dividendos_his (FECHA, EMISOR, PRECIO_PORC, VALOR_NOMINAL, VALOR_EFECTIVO, EMISION, VENCIMIENTO, RENDIMIENTO, PROCEDENCIA, OBSERVACIONES) SELECT `FECHA`, `EMISOR`, `PRECIO %%`, `VALOR NOMINAL (USD)`, `VALOR EFECTIVO (USD)`, `F. EMISION`, `F. VENCIMIENTO`, `RENDIMIENTO %%`, `PROCEDENCIA`, `OBSERVACIONES` FROM `dividendos_his_jao` where emisor is not null and fecha > (SELECT IFNULL(MAX(fecha), '2100-01-01') FROM dividendos_his)"    


    cursor.execute("CREATE TABLE `dividendos_his` ( `id` int(11) NOT NULL AUTO_INCREMENT, `emisor_id` double DEFAULT NULL COMMENT 'CÓDIGO EMISOR', `emisor` text DEFAULT NULL COMMENT 'EMISOR', `fecha_resolucion` text DEFAULT NULL COMMENT 'FECHA DE RESOLUCION', `fecha_ultimo_derecho` date DEFAULT NULL COMMENT 'FECHA ULTIMO DERECHO', `fecha_pago` text DEFAULT NULL COMMENT 'FECHA DE PAGO', `valor_nominal` double DEFAULT NULL COMMENT 'VALOR NOMINAL', `acciones_antes_dividendos` double DEFAULT NULL COMMENT 'NUMERO DE ACCIONES CIRCULANTES ANTES DE PAGO DE DIVIDENDOS', `ultimo_precio` double DEFAULT NULL COMMENT 'ULTIMO PRECIO', `fecha_ultimo_precio` text DEFAULT NULL COMMENT 'FECHA ULTIMO PRECIO', `dividendo_efectivo` double DEFAULT NULL COMMENT 'DIVIDENDO EFECTIVO', `dividendo_ef_por_accion` double DEFAULT NULL COMMENT 'DIVIDENDO EFECTIVO POR ACCION', `precio_ajus_div_efectivo` double DEFAULT NULL COMMENT 'PRECIO AJUSTADO CON DIVIDENDO EFECTIVO', `aum_dism_capital` double DEFAULT NULL COMMENT 'AUMENTO O DISMINUCIÓN DE CAPITAL', `aumento_suscripcion` double DEFAULT NULL COMMENT 'AUMENTO POR SUSCRIPCION', `capital_anterior` double DEFAULT NULL COMMENT 'CAPITAL ANTERIOR', `acciones_antiguas` double DEFAULT NULL COMMENT 'NUMERO ACCIONES ANTIGUAS', `capital_luego_evento` double DEFAULT NULL COMMENT 'CAPITAL LUEGO DEL EVENTO', `acciones_totales` double DEFAULT NULL COMMENT 'NUMERO ACCIONES TOTALES', `aum_capital_capital_anterior` double DEFAULT NULL COMMENT 'AUMENTO DE CAPITAL / CAPITAL ANTERIOR', `factor_correccion` double DEFAULT NULL COMMENT 'FACTOR DE CORRECCION', `precio_ajustado` double DEFAULT NULL COMMENT 'PRECIO AJUSTADO', `circular` text DEFAULT NULL COMMENT 'CIRCULAR', `utilidad_neta_anio` double DEFAULT NULL COMMENT 'UTILIDAD NETA DEL AÑO', `revision` text DEFAULT NULL COMMENT 'REVISION',  `created_at` timestamp NULL DEFAULT current_timestamp(), `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(), PRIMARY KEY (`id`) ) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;")

    SQL = "INSERT INTO `dividendos_his`(`emisor_id`,`emisor`,`fecha_resolucion`,`fecha_ultimo_derecho`,`fecha_pago`,`valor_nominal`,`acciones_antes_dividendos`,`ultimo_precio`,`fecha_ultimo_precio`,`dividendo_efectivo`,`dividendo_ef_por_accion`,`precio_ajus_div_efectivo`,`aum_dism_capital`,`aumento_suscripcion`,`capital_anterior`,`acciones_antiguas`,`capital_luego_evento`,`acciones_totales`,`aum_capital_capital_anterior`,`factor_correccion`,`precio_ajustado`,`circular`,`utilidad_neta_anio`,`revision`)SELECT `CÓDIGO EMISOR`, `EMISOR`, `FECHA DE RESOLUCION`, `FECHA ULTIMO DERECHO`, `FECHA DE PAGO`, `VALOR NOMINAL`, `NUMERO DE ACCIONES CIRCULANTES ANTES DE PAGO DE DIVIDENDOS`, `ULTIMO PRECIO`, `FECHA ULTIMO PRECIO`, `DIVIDENDO EFECTIVO`, `DIVIDENDO EF. POR ACCION`, `PRECIO AJUSTADO CON DIVIDENDO EFECTIVO`, `AUMENTO O DISMINUCIÓN DE CAPITAL`, `AUMENTO POR SUSCRIPCION`, `CAPITAL ANTERIOR`, `NUMERO ACCIONES ANTIGUAS`, `CAPITAL LUEGO DEL EVENTO`, `NUMERO ACCIONES TOTALES`, `AUMENTO DE CAPITAL / CAPITAL ANTERIOR`, `FACTOR DE CORRECCION`, `PRECIO AJUSTADO`, `CIRCULAR`, `UTILIDAD NETA DEL AÑO`, `REVISION` FROM `dividendos_his_jao` where EMISOR is not null"

    print(SQL)
    
    cursor.execute(SQL)

 
    print("Actualizada la tabla 'dividendos_his'.")

    
    cnx.commit()

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    # Cierra la conexión
    if 'cnx' in locals() and cnx.is_connected():
        cursor.close()
        cnx.close()
        print("Conexión cerrada.")
