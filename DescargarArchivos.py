import pyperclip
import time
import os
from shutil import rmtree





MyDelay1 = 4
MyDelay2 = 4
MyDelay3 = 4

aaaa=time.strftime("%Y")

mm=time.strftime("%m")
dd=time.strftime("%d")
dia=time.strftime("%A")

#directorioBase='C:\\Users\\super\\DATOS\\JHON\\004. DatosBVQ\\'


#directorioBase='D:\\004. DatosBVQ\\'


directorioBase='C:\\Users\\super\\DATOS\\004. DatosBVQ\\'

# rmtree(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd)




if not os.path.exists(directorioBase+aaaa+"_"+mm):
    
    
    os.mkdir(directorioBase+aaaa+"_"+mm)
    
    
if not os.path.exists(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd):
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd)
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\001_InformacionContinua")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\002_BoletinesAlCierre")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\003_BoletinesSemanales")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\004_BoletinesMensuales")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\005_BoletinesValores")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\006_Emisiones")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\007_CotizacionesHistoricas")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\008_RentaVariable")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\009_CalificacionesDeRiesgo")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\010_SectorPublico")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\011_VectorDePreciosDiario")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\012_VectorDePreciosMensual")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\013_PrecioNacionalRentaVariableDiario")
    os.mkdir(directorioBase+aaaa+"_"+mm+"\\"+aaaa+"_"+mm+"_"+dd+"\\014_PrecioNacionalRentaVariableMensual")
    
    
    urls = [




                'https://www.bolsadequito.com/uploads/estadisticas/boletines/informacion-continua/boletin-diario.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/informacion-continua/ofertas-y-demandas.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/informacion-continua/maximos-y-minimos.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/informacion-continua/lista-valores-reporto.xls',
              
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-al-cierre/ecuindex.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-semanales/pulso-semanal.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-semanales/montos-colocados.xls',
              
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-mensuales/pulso-mensual.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-mensuales/informe-bursatil-mensual.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-mensuales/total-negociado-tipo-papel.xls',
            
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-valores/deuda-publica.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-valores/obligaciones.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-valores/facturas-comerciales.xls',      
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-valores/valores-genericos.xls',

                'https://www.bolsadequito.com/uploads/estadisticas/boletines/emisiones/renta-fija.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/emisiones/renta-variable.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/emisiones/bonos.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/emisiones/facturas-comerciales.xls', 
                

                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/facturas-comerciales.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/notas-credito.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/cetes.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/bonos.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/cupones.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/papel-comercial.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/tbc.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/ocas.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/vtp.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/acciones.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/valores-genericos.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/obligaciones.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/cotizaciones-historicas/titularizaciones.xls',                

                'https://www.bolsadequito.com/uploads/estadisticas/boletines/renta-variable/dividendos.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/renta-variable/indicadores-renta-variable.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/renta-variable/montos-negociados-acciones.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/renta-variable/evolucion-precios-acciones.xls',

                'https://www.bolsadequito.com/uploads/estadisticas/boletines/sector-publico/montos-negociados-mensuales.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/sector-publico/montos-negociados-acumulados.xls',

                'https://www.bolsadequito.com/uploads/estadisticas/valoracion/vector-precios-diario/vector-precios-diario.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/valoracion/vector-precios-mensual/vector-precios-mensual.xls',

                'https://www.bolsadequito.com/uploads/estadisticas/valoracion/pnrv-diario/precio-nacional-renta-variable-diario.xls',
                'https://www.bolsadequito.com/uploads/estadisticas/valoracion/pnrv-mensual/precio-nacional-renta-variable-mensual.xls',            
                'https://www.bolsadequito.com/uploads/estadisticas/boletines/boletines-mensuales/analisis-sensibilidad.pdf'
            ]
            
    for url in urls:
        
        print('Cargando...')
        
        partes=url.split('/')
        archivo=partes[len(partes)-1]
        carpeta=partes[len(partes)-2]
        nombre=archivo[:len(archivo)-4]
        ext=archivo[len(archivo)-4:len(archivo)]
        print(nombre)
        print(ext)
       
        if carpeta=="informacion-continua":
            carpeta='001_InformacionContinua'
        elif carpeta=="boletines-al-cierre":
            carpeta='002_BoletinesAlCierre'
        elif carpeta=="boletines-semanales":
            carpeta='003_BoletinesSemanales'
        elif carpeta=="boletines-mensuales":
            carpeta='004_BoletinesMensuales'
        elif carpeta=="boletines-valores":
            carpeta='005_BoletinesValores'
        elif carpeta=="emisiones":
            carpeta='006_Emisiones'
        elif carpeta=="cotizaciones-historicas":
            carpeta='007_CotizacionesHistoricas'
        elif carpeta=="renta-variable":
            carpeta='008_RentaVariable'
        elif carpeta=="sector-publico":
            carpeta='010_SectorPublico'
        elif carpeta=="vector-precios-diario":
            carpeta='011_VectorDePreciosDiario'           
        elif carpeta=="vector-precios-mensual":
            carpeta='012_VectorDePreciosMensual'
        elif carpeta=="pnrv-diario":
            carpeta='013_PrecioNacionalRentaVariableDiario'
        elif carpeta=="pnrv-mensual":
            carpeta='014_PrecioNacionalRentaVariableMensual'
        
        directorio=directorioBase+aaaa+'_'+mm+'\\'+aaaa+'_'+mm+'_'+dd+'\\'+carpeta+'\\'+nombre+'_'+aaaa+'_'+mm+'_'+dd+ext
        
        pyperclip.copy(directorio)
        os.system("start chrome /incognito "+url)
        time.sleep(MyDelay1)
        if(ext=='.xls'):
            print('Pegando...')
            os.system("pegar.bat")
        elif(ext=='.pdf'):
            directorio_auxiliar=directorio
            continue
        time.sleep(MyDelay2)
        print('Enviando...')
        os.system("enviar.bat")
        time.sleep(MyDelay3)
    pyperclip.copy(directorio_auxiliar)
