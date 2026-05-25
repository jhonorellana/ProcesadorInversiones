import os
import time
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine

# Configura las credenciales de la base de datos
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'inversiones',
    'raise_on_warnings': True
}


# Ruta del archivo Excel
aaaa=time.strftime("%Y")
mm=time.strftime("%m")
dd=time.strftime("%d")
dia=time.strftime("%A")
carpeta='007_CotizacionesHistoricas'
nombre = 'acciones'
ext = '.xls'
directorioBase='C:\\Users\\super\\DATOS\\004. DatosBVQ\\'
nombre = 'acciones'
#excel_file_path = directorioBase+aaaa+'_'+mm+'\\'+aaaa+'_'+mm+'_'+dd+'\\'+carpeta+'\\'+nombre+'_'+aaaa+'_'+mm+'_'+dd+ext
#print ("-->")
#print (excel_file_path)
#print ("<--")


#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2018.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2019.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2020.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2021.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2022.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\dividendos_2023.xls'
#excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\Dividendos_2024.xls'
excel_file_path ='C:\\Users\\super\\DATOS\\004. DatosBVQ\\001. Analisis\\Historiadividendos\\Dividendos_2025.xls'

# Carga los datos desde la pestaña "2023" del archivo Excel, omitiendo la primera columna (skipcols=[0])
#df = pd.read_excel(excel_file_path, sheet_name='2018', skiprows=8, usecols=lambda x: x not in [0])
#df = pd.read_excel(excel_file_path, sheet_name='2019', skiprows=8, usecols=lambda x: x not in [0])
#df = pd.read_excel(excel_file_path, sheet_name='2020', skiprows=8, usecols=lambda x: x not in [0])
#df = pd.read_excel(excel_file_path, sheet_name='2021', skiprows=8, usecols=lambda x: x not in [0])
#df = pd.read_excel(excel_file_path, sheet_name='2022', skiprows=8, usecols=lambda x: x not in [0])
#df = pd.read_excel(excel_file_path, sheet_name='2023', skiprows=8, usecols=lambda x: x not in [0])
df = pd.read_excel(excel_file_path, sheet_name='DIVIDENDOS', skiprows=6, usecols=lambda x: x not in [0])




# Conéctate a la base de datos MySQL
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Elimina la tabla si existe
    cursor.execute("DROP TABLE dividendos_his_jao")
    cursor.execute("DROP TABLE dividendos_his")
    
    cursor.execute("CREATE TABLE `dividendos_his` ( `id` int(11) NOT NULL AUTO_INCREMENT, `emisor_id` double DEFAULT NULL COMMENT 'CÓDIGO EMISOR', `emisor` text DEFAULT NULL COMMENT 'EMISOR', `fecha_resolucion` text DEFAULT NULL COMMENT 'FECHA DE RESOLUCION', `fecha_ultimo_derecho` date DEFAULT NULL COMMENT 'FECHA ULTIMO DERECHO', `fecha_pago` text DEFAULT NULL COMMENT 'FECHA DE PAGO', `valor_nominal` double DEFAULT NULL COMMENT 'VALOR NOMINAL', `acciones_antes_dividendos` double DEFAULT NULL COMMENT 'NUMERO DE ACCIONES CIRCULANTES ANTES DE PAGO DE DIVIDENDOS', `ultimo_precio` double DEFAULT NULL COMMENT 'ULTIMO PRECIO', `fecha_ultimo_precio` text DEFAULT NULL COMMENT 'FECHA ULTIMO PRECIO', `dividendo_efectivo` double DEFAULT NULL COMMENT 'DIVIDENDO EFECTIVO', `dividendo_ef_por_accion` double DEFAULT NULL COMMENT 'DIVIDENDO EFECTIVO POR ACCION', `precio_ajus_div_efectivo` double DEFAULT NULL COMMENT 'PRECIO AJUSTADO CON DIVIDENDO EFECTIVO', `aum_dism_capital` double DEFAULT NULL COMMENT 'AUMENTO O DISMINUCIÓN DE CAPITAL', `aumento_suscripcion` double DEFAULT NULL COMMENT 'AUMENTO POR SUSCRIPCION', `capital_anterior` double DEFAULT NULL COMMENT 'CAPITAL ANTERIOR', `acciones_antiguas` double DEFAULT NULL COMMENT 'NUMERO ACCIONES ANTIGUAS', `capital_luego_evento` double DEFAULT NULL COMMENT 'CAPITAL LUEGO DEL EVENTO', `acciones_totales` double DEFAULT NULL COMMENT 'NUMERO ACCIONES TOTALES', `aum_capital_capital_anterior` double DEFAULT NULL COMMENT 'AUMENTO DE CAPITAL / CAPITAL ANTERIOR', `factor_correccion` double DEFAULT NULL COMMENT 'FACTOR DE CORRECCION', `precio_ajustado` double DEFAULT NULL COMMENT 'PRECIO AJUSTADO', `circular` text DEFAULT NULL COMMENT 'CIRCULAR', `utilidad_neta_anio` double DEFAULT NULL COMMENT 'UTILIDAD NETA DEL AÑO', `revision` text DEFAULT NULL COMMENT 'REVISION',  `created_at` timestamp NULL DEFAULT current_timestamp(), `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(), PRIMARY KEY (`id`) ) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;")

    # Crea una conexión a la base de datos usando sqlalchemy
    engine = create_engine('mysql+mysqlconnector://{user}:{password}@{host}/{database}'.format(**db_config))

    # Crea la tabla en la base de datos
    df[:0].to_sql('dividendos_his_jao', con=engine, if_exists='replace', index=False)  # Solo crea la estructura de la tabla

    # Carga los datos en la tabla de MySQL
    df.to_sql('dividendos_his_jao', con=engine, if_exists='append', index=False)

    # Confirma los cambios
#    cnx.commit()
    print("Datos cargados exitosamente en la tabla 'dividendos_his_jao'.")

    SQL = "INSERT INTO `dividendos_his`(`emisor_id`,`emisor`,`fecha_resolucion`,`fecha_ultimo_derecho`,`fecha_pago`,`valor_nominal`,`acciones_antes_dividendos`,`ultimo_precio`,`fecha_ultimo_precio`,`dividendo_efectivo`,`dividendo_ef_por_accion`,`precio_ajus_div_efectivo`,`aum_dism_capital`,`aumento_suscripcion`,`capital_anterior`,`acciones_antiguas`,`capital_luego_evento`,`acciones_totales`,`aum_capital_capital_anterior`,`factor_correccion`,`precio_ajustado`,`circular`,`utilidad_neta_anio`,`revision`)SELECT `CÓDIGO EMISOR`, `EMISOR`, `FECHA DE RESOLUCION`, `FECHA ULTIMO DERECHO`, `FECHA DE PAGO`, `VALOR NOMINAL`, `NUMERO DE ACCIONES CIRCULANTES ANTES DE PAGO DE DIVIDENDOS`, `ULTIMO PRECIO`, `FECHA ULTIMO PRECIO`, `DIVIDENDO EFECTIVO`, `DIVIDENDO EF. POR ACCION`, `PRECIO AJUSTADO CON DIVIDENDO EFECTIVO`, `AUMENTO O DISMINUCIÓN DE CAPITAL`, `AUMENTO POR SUSCRIPCION`, `CAPITAL ANTERIOR`, `NUMERO ACCIONES ANTIGUAS`, `CAPITAL LUEGO DEL EVENTO`, `NUMERO ACCIONES TOTALES`, `AUMENTO DE CAPITAL / CAPITAL ANTERIOR`, `FACTOR DE CORRECCION`, `PRECIO AJUSTADO`, `CIRCULAR`, `UTILIDAD NETA DEL AÑO`, `REVISION` FROM `dividendos_his_jao` where EMISOR is not null"
    # print(SQL)
    
    cursor.execute(SQL)



    SQL = "UPDATE dividendos_his set emisor_id = emisor_id + 2000"
    #print(SQL)
    
    cursor.execute(SQL)
 
    
    SQL = "UPDATE dividendos_his AS A JOIN dictionary AS D ON A.emisor = D.DIC_VALUE SET A.emisor_id = D.dic_id;"
    cursor.execute(SQL)


    SQL = "UPDATE dividendos_his SET emisor_id = 64 where emisor like '%ALIMENT%';"
    cursor.execute(SQL)

    SQL = "UPDATE dividendos_his SET emisor_id = 56 where emisor like '%BANCO AMAZONAS%';"
    cursor.execute(SQL)

    SQL = "UPDATE dividendos_his SET emisor_id = 21 where emisor like '%BANCO DE GUAYAQUIL%';"
    cursor.execute(SQL)
    
    SQL = "UPDATE dividendos_his SET emisor_id = 50 where emisor like '%PRODUBANCO%';"
    cursor.execute(SQL)
    
    SQL = "UPDATE dividendos_his SET emisor_id = 61 where emisor like '%CEPSA%';"
    cursor.execute(SQL)
    
    SQL = "UPDATE dividendos_his SET emisor_id = 41 where emisor like '%CERRO VERDE%';"
    cursor.execute(SQL)    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 15 where emisor like '%CERVE%';"
    cursor.execute(SQL)    
 
    SQL = "UPDATE dividendos_his SET emisor_id = 31 where emisor like '%CONCLINA%';"
    cursor.execute(SQL)    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 66 where emisor like '%MULTI%';"
    cursor.execute(SQL)    

    SQL = "UPDATE dividendos_his SET emisor_id = 35 where emisor like '%CRIDESA%';"
    cursor.execute(SQL)    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 47 where emisor like '%REFUGIO%';"
    cursor.execute(SQL)    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 45 where emisor like '%SENDERO%';"
    cursor.execute(SQL)        

    SQL = "UPDATE dividendos_his SET emisor_id = 46 where emisor like '%TECAL%';"
    cursor.execute(SQL)        
    
    SQL = "UPDATE dividendos_his SET emisor_id = 29 where emisor like '%CONTINENTAL%';"
    cursor.execute(SQL)        

    SQL = "UPDATE dividendos_his SET emisor_id = 22 where emisor like '%HOLCIM%';"
    cursor.execute(SQL)            
    
    SQL = "UPDATE dividendos_his SET emisor_id = 19 where emisor like '%COLON%';"
    cursor.execute(SQL)                

    SQL = "UPDATE dividendos_his SET emisor_id = 26 where emisor like '%INVERSAN%';"
    cursor.execute(SQL)                
    
    SQL = "UPDATE dividendos_his SET emisor_id = 32 where emisor like '%STRONGFOREST%';"
    cursor.execute(SQL)                    

    SQL = "UPDATE dividendos_his SET emisor_id = 51 where emisor like '%UNACEM%';"
    cursor.execute(SQL)                    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 42 where emisor like '%REFOREST%';"
    cursor.execute(SQL)                    

    SQL = "UPDATE dividendos_his SET emisor_id = 37 where emisor like '%MERIZA%';"
    cursor.execute(SQL)                    
    
    SQL = "UPDATE dividendos_his SET emisor_id = 48 where emisor like '%CONGO%';"
    cursor.execute(SQL)                        
    
    SQL = "UPDATE dividendos_his SET emisor_id = 25 where emisor like '%SAN CARLOS%';"
    cursor.execute(SQL)                        

    SQL = "UPDATE dividendos_his SET emisor_id = 44 where emisor like '%FORESTEAD%';"
    cursor.execute(SQL)                        
    
    SQL = "UPDATE dividendos_his SET emisor_id = 38 where emisor like '%HILLFOREST%';"
    cursor.execute(SQL)                        

    SQL = "UPDATE dividendos_his SET emisor_id = 52 where emisor like '%PLAINFOREST%';"
    cursor.execute(SQL)                        

    SQL = "UPDATE dividendos_his SET emisor_id = 40 where emisor like '%HIGHFOREST%';"
    cursor.execute(SQL)                        

    SQL = "UPDATE dividendos_his SET emisor_id = 60 where emisor like '%Hipotecas%';"
    cursor.execute(SQL)                            

    SQL = "UPDATE dividendos_his SET emisor_id = 67 where emisor like '%BEVERAGE%';"
    cursor.execute(SQL)   
    
    SQL = "UPDATE dividendos_his SET emisor_id = 36 where emisor like '%RETRATOREC%';"
    cursor.execute(SQL)   
    
    SQL = "UPDATE dividendos_his SET emisor_id = 55 where emisor like '%SURPAPEL%';"
    cursor.execute(SQL)       
    
    SQL = "UPDATE dividendos_his SET emisor_id = 34 where emisor like '%ALICOSTA%';"
    cursor.execute(SQL)       
    
    SQL = "UPDATE dividendos_his SET emisor_id = 58 where emisor like '%NATLUK%';"
    cursor.execute(SQL)       
    
    SQL = "UPDATE dividendos_his SET emisor_id = 39 where emisor like '%VALLE GRANDE%';"
    cursor.execute(SQL)       

    SQL = "UPDATE dividendos_his SET emisor_id = 17 where emisor like '%RIO GRANDE%';"
    cursor.execute(SQL)       

    SQL = "UPDATE dividendos_his SET emisor_id = 43 where emisor like '%CUMBRE FORESTAL%';"
    cursor.execute(SQL)       

    SQL = "UPDATE dividendos_his SET emisor_id = 53 where emisor like '%VANGUARDIA FORESTAL%';"
    cursor.execute(SQL)       

    SQL = "UPDATE dividendos_his SET emisor_id = 20 where emisor like '%ENSENADA FORESTAL%';"
    cursor.execute(SQL)       

    SQL = "UPDATE dividendos_his SET emisor_id = 68 where emisor like '%SIEMPREVERDE%';"
    cursor.execute(SQL)       




    
    SQL = "update dividendos_his set fecha_resolucion = fecha_ultimo_precio where fecha_resolucion is null;"
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
