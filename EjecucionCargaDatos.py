import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import threading
import time
import mysql.connector
import os
import json
from datetime import datetime
import zipfile

# ---------------------------------------
# Carga de configuración
# ---------------------------------------
def cargar_configuracion():
    """Carga la configuración desde el archivo config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró el archivo de configuración 'config.json'")
        raise
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Error al analizar el archivo de configuración: {e}")
        raise
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado al cargar la configuración: {e}")
        raise

# Cargar configuración
try:
    config = cargar_configuracion()
    db_config = config['database']
except Exception as e:
    # Configuración por defecto en caso de error
    db_config = {
        "user": "root",
        "password": "",
        "host": "localhost",
        "database": "inversiones_tempa",
        "raise_on_warnings": True,
    }
    messagebox.showwarning("Advertencia", 
        f"Usando configuración por defecto. Error al cargar config.json: {e}")

# Constantes de la aplicación
STATUS_NORMAL_COLOR = "black"
STATUS_ERROR_COLOR = "red"

# Lista global para controlar el estado de todos los botones
all_buttons = []

# Estas variables se inicializan más abajo, después de crear la GUI
root = None
status_label = None
output_text = None


# ---------------------------------------
# Utilidades generales
# ---------------------------------------
def escribir_log(mensaje: str) -> None:
    """Escribe una línea en el archivo de log con timestamp."""
    with open("log_ejecucion.txt", "a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {mensaje}\n")


def es_error_conexion(err: mysql.connector.Error) -> bool:
    """
    Determina si el error de MySQL es de conexión/servidor caído.
    """
    errno = getattr(err, "errno", None)
    return errno in (
        2003,  # No se puede conectar al servidor MySQL
        2006,  # Servidor se ha ido
        2013,  # Conexión perdida
        1045,  # Usuario/clave inválidos
        1049,  # Base de datos desconocida
    )


def imprimir_linea(texto: str, tipo: str = "normal") -> None:
    """
    Inserta una línea en el Text con el estilo indicado:
    - tipo="normal" -> texto negro
    - tipo="error"  -> texto rojo + icono [WARN] al inicio
    """
    if output_text is None:
        return  # seguridad por si algo se ejecuta antes de crear la GUI

    tag = "normal"
    if tipo == "error":
        texto = "[WARN] " + texto
        tag = "error"

    output_text.insert("end", texto + "\n", tag)
    output_text.see("end")  # hacer scroll automático al final


def limpiar_salida() -> None:
    """Limpia el contenido del panel de salida."""
    if output_text is not None:
        output_text.delete("1.0", "end")


def marcar_error_en_pantalla(mensaje_estado: str) -> None:
    """Actualiza solo el estado general a rojo cuando hay error."""
    if status_label is not None:
        status_label.config(text=mensaje_estado, fg=STATUS_ERROR_COLOR)


def resetear_color_pantalla(mensaje_estado: str) -> None:
    """Vuelve el estado general a color normal (negro)."""
    if status_label is not None:
        status_label.config(text=mensaje_estado, fg=STATUS_NORMAL_COLOR)


def verificar_conexion_bd() -> bool:
    """Verifica que la base de datos esté accesible antes de ejecutar SPs."""
    try:
        conn = mysql.connector.connect(**db_config)
        conn.close()
        return True
    except mysql.connector.Error as err:
        mensaje = f"Error de CONEXIÓN con la base de datos: {err}"
        marcar_error_en_pantalla("Error de conexión a la base de datos.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        return False


# ---------------------------------------
# Stored Procedures
# ---------------------------------------
def ejecutar_sp(nombre_sp: str, args: tuple = None) -> bool:
    """
    Ejecuta un stored procedure y devuelve True si todo OK, False si hubo error.
    Distingue error de conexión vs error de lógica.
    """
    if args is None:
        args = ()

    current_db_config = db_config.copy()
    if nombre_sp.startswith("sipro_desa."):
        current_db_config["database"] = "sipro_desa"
        sp_name_to_call = nombre_sp.replace("sipro_desa.", "")
    else:
        sp_name_to_call = nombre_sp

    try:
        mensaje_inicio = f"Iniciando ejecución: {nombre_sp}..." if not args else f"Iniciando ejecución: {nombre_sp}{args}..."
        imprimir_linea(mensaje_inicio, "normal")
        escribir_log(mensaje_inicio)

        conn = mysql.connector.connect(**current_db_config)
        cursor = conn.cursor(buffered=True)
        
        if args:
            placeholders = ", ".join(["%s"] * len(args))
            sql = f"CALL {sp_name_to_call}({placeholders})"
            cursor.execute(sql, args)
        else:
            cursor.execute(f"CALL {sp_name_to_call}()")

        # Consumir y vaciar completamente todos los resultsets emitidos por el SP
        try:
            cursor.fetchall()
        except Exception:
            pass

        try:
            while cursor.nextset():
                try:
                    cursor.fetchall()
                except Exception:
                    pass
        except Exception:
            pass

        conn.commit()
        cursor.close()
        conn.close()

        mensaje = f"Stored procedure completado: {nombre_sp}" if not args else f"Stored procedure completado: {nombre_sp}{args}"
        imprimir_linea(mensaje, "normal")
        escribir_log(mensaje)
        return True

    except mysql.connector.Error as err:
        if es_error_conexion(err):
            mensaje = (
                f"[CONEXIÓN] Error al ejecutar {nombre_sp}: {err} "
                "(posible motor de BD abajo)"
            )
            marcar_error_en_pantalla("Error de CONEXIÓN durante la ejecución de SPs.")
        else:
            mensaje = f"[SP] Error de lógica al ejecutar {nombre_sp}: {err}"
            marcar_error_en_pantalla("Error de LÓGICA en uno de los SPs.")

        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        return False

    except Exception as ex:
        mensaje = f"[SP] Error inesperado al ejecutar {nombre_sp}: {ex}"
        marcar_error_en_pantalla("Error inesperado durante la ejecución de SPs.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        return False


def run_sps() -> bool:
    """
    Ejecuta la lista de SPs.
    Devuelve True si todo salió bien, False si hubo algún error.
    """
    imprimir_linea("Ejecutando procedimientos almacenados...", "normal")
    escribir_log("Inicio de ejecución de SPs")

    # 1) Verificar conexión previa
    if not verificar_conexion_bd():
        messagebox.showerror(
            "Error de conexión",
            "No se pudo conectar a la base de datos.\n"
            "Verifica que el servidor MySQL esté arriba y que la "
            "configuración sea correcta.",
        )
        escribir_log("Ejecución de SPs cancelada por error de conexión inicial.")
        return False

    lista_sps = [
        "SP_ACTUALIZAR_SHARES_LAST_DATE",
        "SP_ACTUALIZAR_RESUMEN_QUINCENAL",
        "SP_ACTUALIZAR_CONSOLIDADO_INVERSIONES",
        "SP_LIMPIAR_TEMPORALES",
        "SP_ACTUALIZAR_AMORTIZACION_INVESTMENT",
        ("sipro_desa.SP_ACTUALIZAR_AMORTIZACION_INVERSION", (None, None)),
        "sipro_desa.SP_ACCION_ULTIMO_PRECIO_REFRESH",
        "sipro_desa.sp_actualizar_snapshot_cartera",
    ]

    for item in lista_sps:
        if isinstance(item, tuple):
            nombre_sp, args = item
        else:
            nombre_sp, args = item, ()

        if not ejecutar_sp(nombre_sp, args):
            mensaje = "Se detuvo la ejecución de SPs por un error."
            imprimir_linea(mensaje, "error")
            escribir_log(mensaje)

            messagebox.showerror(
                "Error en SPs",
                f"Ocurrió un error al ejecutar el procedimiento: {nombre_sp}.\n"
                "Revisa el archivo log_ejecucion.txt para más detalles.",
            )
            return False

        time.sleep(5)  # pausa entre SPs

    escribir_log("Fin de ejecución de SPs")
    return True


# ---------------------------------------
# Backup de base de datos
# ---------------------------------------
def hacer_backup_base_datos() -> None:
    """Genera un backup comprimido (ZIP) de la base de datos."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = "backups"
        os.makedirs(backup_folder, exist_ok=True)

        sql_filename = f"backup_inversion_{timestamp}.sql"
        sql_path = os.path.join(backup_folder, sql_filename)

        comando = [
            "mysqldump",
            "-u",
            db_config["user"],
            f"--password={db_config['password']}",
            db_config["database"],
        ]

        # Crear el archivo SQL
        with open(sql_path, "w", encoding="utf-8") as f:
            subprocess.run(comando, stdout=f, check=True)

        # Comprimir a ZIP
        zip_filename = f"backup_inversion_{timestamp}.zip"
        zip_path = os.path.join(backup_folder, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_path, arcname=sql_filename)

        # Eliminar el SQL temporal
        os.remove(sql_path)

        mensaje = f"Backup comprimido en: {zip_path}"
        imprimir_linea(mensaje, "normal")
        escribir_log(mensaje)
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar mysqldump: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
    except Exception as e:
        mensaje = f"Error al crear el backup comprimido: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
    
    # ---------------------------------------

    """Genera un backup comprimido (ZIP) de la base de datos."""
    try:
        sql_filename = f"backup_sipro_desa_{timestamp}.sql"
        sql_path = os.path.join(backup_folder, sql_filename)

        comando = [
            "mysqldump",
            "-u",
            db_config["user"],
            f"--password={db_config['password']}",
            "sipro_desa",
        ]

        # Crear el archivo SQL
        with open(sql_path, "w", encoding="utf-8") as f:
            subprocess.run(comando, stdout=f, check=True)

        # Comprimir a ZIP
        zip_filename = f"backup_sipro_desa_{timestamp}.zip"
        zip_path = os.path.join(backup_folder, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_path, arcname=sql_filename)

        # Eliminar el SQL temporal
        os.remove(sql_path)

        mensaje = f"Backup comprimido en: {zip_path}"
        imprimir_linea(mensaje, "normal")
        escribir_log(mensaje)
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar mysqldump: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
    except Exception as e:
        mensaje = f"Error al crear el backup comprimido: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)



# ---------------------------------------

    """Genera un backup comprimido (ZIP) de la base de datos."""
    try:
        sql_filename = f"backup_release_control_db_{timestamp}.sql"
        sql_path = os.path.join(backup_folder, sql_filename)

        comando = [
            "mysqldump",
            "-u",
            db_config["user"],
            f"--password={db_config['password']}",
            "release_control_db",
        ]

        # Crear el archivo SQL
        with open(sql_path, "w", encoding="utf-8") as f:
            subprocess.run(comando, stdout=f, check=True)

        # Comprimir a ZIP
        zip_filename = f"backup_release_control_db_{timestamp}.zip"
        zip_path = os.path.join(backup_folder, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_path, arcname=sql_filename)

        # Eliminar el SQL temporal
        os.remove(sql_path)

        mensaje = f"Backup comprimido en: {zip_path}"
        imprimir_linea(mensaje, "normal")
        escribir_log(mensaje)
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar mysqldump: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
    except Exception as e:
        mensaje = f"Error al crear el backup comprimido: {e}"
        marcar_error_en_pantalla("Error al generar el backup.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)







# ---------------------------------------
# Ejecución de scripts externos
# ---------------------------------------
def ejecutar_script(nombre_script: str) -> None:
    """Ejecuta un script Python externo, mostrando y registrando errores."""
    imprimir_linea(f"Iniciando: {nombre_script}", "normal")
    escribir_log(f"Iniciando: {nombre_script}")
    try:
        result = subprocess.run(
            ["python", nombre_script],
            check=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            salida = f"Salida de {nombre_script}:\n{result.stdout}"
            escribir_log(salida)
            # Mostrar en pantalla solo si hay un error en la salida
            if 'error' in result.stdout.lower() or 'warning' in result.stdout.lower():
                imprimir_linea(salida, "error")

        mensaje = f"Finalizado: {nombre_script}"
        imprimir_linea(mensaje, "normal")
        escribir_log(mensaje)
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar {nombre_script}: código {e.returncode}"
        marcar_error_en_pantalla("Error en la ejecución de un script.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)

        # Mostrar la salida estándar en la interfaz
        if e.stdout:
            salida_stdout = f"Salida estándar de {nombre_script}:\n{e.stdout}"
            imprimir_linea(salida_stdout, "normal")
            escribir_log(salida_stdout)
        
        # Mostrar el error en la interfaz
        if e.stderr:
            error_msg = f"Error de {nombre_script}:\n{e.stderr}"
            imprimir_linea(error_msg, "error")
            escribir_log(f"STDERR {nombre_script}:\n{e.stderr}")
    except Exception as e:
        mensaje = f"Error inesperado al ejecutar {nombre_script}: {str(e)}"
        marcar_error_en_pantalla("Error inesperado en la ejecución de un script.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)


# ---------------------------------------
# Flujos de ejecución de negocio
# ---------------------------------------
def run_scripts_and_sps(include_backup: bool = True) -> None:
    """Ejecuta todos los scripts, luego los SPs, y opcionalmente el backup."""
    scripts = [
        "DiarioAcciones.py",
        "DiarioBonos.py",
        "DiarioDividendos.py",
        "DiarioFacturas.py",
        "DiarioGenericos.py",
        "DiarioObligaciones.py",
        "DiarioPapeles.py",
        "DiarioTitularizaciones.py",
    ]

    # Ejecutar scripts
    for script in scripts:
        ejecutar_script(script)
        time.sleep(5)

    # Pausa antes de los SPs
    imprimir_linea("Esperando 5 segundos para ejecutar SPs...", "normal")
    escribir_log("Esperando 5 segundos para ejecutar SPs...")
    time.sleep(5)

    # Ejecutar SPs. Si falla, no continuamos.
    if not run_sps():
        return

    if include_backup:
        # Hacer backup
        hacer_backup_base_datos()
        imprimir_linea(
            "Proceso de scripts, SPs y backup completado.", "normal"
        )
        escribir_log("Proceso completo (scripts, SPs y backup) finalizado.")
        resetear_color_pantalla("Ejecución completada (Todo).")
        messagebox.showinfo(
            "Ejecución completada", "Scripts, SPs y backup finalizados correctamente."
        )
    else:
        imprimir_linea(
            "Proceso de scripts y SPs (sin backup) completado.", "normal"
        )
        escribir_log("Proceso de scripts y SPs (sin backup) finalizado.")
        resetear_color_pantalla("Ejecución completada (sin backup).")
        messagebox.showinfo(
            "Ejecución completada",
            "Scripts y SPs finalizados correctamente (sin backup).",
        )


def execute_all() -> None:
    """Scripts + SPs + backup."""
    run_scripts_and_sps(include_backup=True)


def execute_carga_datos() -> None:
    """Scripts + SPs sin backup."""
    run_scripts_and_sps(include_backup=False)


def execute_only_backup() -> None:
    """Solo backup."""
    escribir_log("Iniciando generación de backup (solo backup).")
    imprimir_linea("Iniciando generación de backup (solo backup)...", "normal")
    hacer_backup_base_datos()
    imprimir_linea("Proceso de backup finalizado.", "normal")
    escribir_log("Proceso de backup finalizado (solo backup).")
    resetear_color_pantalla("Backup completado.")
    messagebox.showinfo("Backup", "Proceso de backup finalizado.")


def execute_only_sps() -> None:
    """Solo SPs."""
    escribir_log("Iniciando ejecución solo de SPs.")
    imprimir_linea("Iniciando ejecución de procedimientos (SPs)...", "normal")

    if not run_sps():
        return

    imprimir_linea("Ejecución de procedimientos finalizada.", "normal")
    escribir_log("Ejecución de SPs finalizada.")
    resetear_color_pantalla("Procedimientos completados.")
    messagebox.showinfo(
        "Procedimientos", "Procedimientos almacenados ejecutados correctamente."
    )


def execute_main_procesador() -> None:
    """Ejecuta MainProcesador.py para procesar PDFs y generar CSV."""
    escribir_log("Iniciando procesador principal de PDFs.")
    imprimir_linea("Iniciando procesador principal de documentos (PDFs)...", "normal")

    try:
        result = subprocess.run(
            ["python", "MainProcesador.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                escribir_log(line)
                if 'error' in line.lower():
                    imprimir_linea(line, "error")
                else:
                    imprimir_linea(line, "normal")

        if result.stderr:
            for line in result.stderr.splitlines():
                escribir_log(f"STDERR: {line}")
                imprimir_linea(f"STDERR: {line}", "error")

        escribir_log("Procesador principal de PDFs finalizado.")
        resetear_color_pantalla("Procesador de PDFs completado.")
        messagebox.showinfo(
            "Procesador PDF", "Procesamiento de documentos PDF finalizado correctamente.\nRevise la carpeta Salida para el CSV generado."
        )
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar MainProcesador.py: código {e.returncode}"
        marcar_error_en_pantalla("Error en el procesador de PDFs.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        if e.stderr:
            imprimir_linea(f"STDERR: {e.stderr}", "error")
    except Exception as e:
        mensaje = f"Error inesperado al ejecutar MainProcesador.py: {str(e)}"
        marcar_error_en_pantalla("Error inesperado en el procesador de PDFs.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)


def execute_database_loader() -> None:
    """Ejecuta DatabaseLoader.py para cargar CSV a la base de datos."""
    escribir_log("Iniciando cargador de base de datos.")
    imprimir_linea("Iniciando carga de CSV a la base de datos...", "normal")

    try:
        result = subprocess.run(
            ["python", "DatabaseLoader.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                escribir_log(line)
                if 'error' in line.lower():
                    imprimir_linea(line, "error")
                else:
                    imprimir_linea(line, "normal")

        if result.stderr:
            for line in result.stderr.splitlines():
                escribir_log(f"STDERR: {line}")
                imprimir_linea(f"STDERR: {line}", "error")

        escribir_log("Cargador de base de datos finalizado.")
        resetear_color_pantalla("Carga a base de datos completada.")
        messagebox.showinfo(
            "Database Loader", "Carga de CSV a la base de datos finalizada correctamente."
        )
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar DatabaseLoader.py: código {e.returncode}"
        marcar_error_en_pantalla("Error en el cargador de base de datos.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        if e.stderr:
            imprimir_linea(f"STDERR: {e.stderr}", "error")
    except Exception as e:
        mensaje = f"Error inesperado al ejecutar DatabaseLoader.py: {str(e)}"
        marcar_error_en_pantalla("Error inesperado en el cargador de base de datos.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)


def execute_new_database_loader() -> None:
    """Ejecuta CargadorBDD.py para cargar CSV a la nueva base de datos."""
    escribir_log("Iniciando cargador de nueva base de datos.")
    imprimir_linea("Iniciando carga de CSV a la nueva base de datos...", "normal")

    try:
        result = subprocess.run(
            ["python", "CargadorBDD.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                escribir_log(line)
                if 'error' in line.lower():
                    imprimir_linea(line, "error")
                else:
                    imprimir_linea(line, "normal")

        if result.stderr:
            for line in result.stderr.splitlines():
                escribir_log(f"STDERR: {line}")
                imprimir_linea(f"STDERR: {line}", "error")

        escribir_log("Cargador de nueva base de datos finalizado.")
        resetear_color_pantalla("Carga a nueva base de datos completada.")
        messagebox.showinfo(
            "Cargador Nueva BDD", "Carga de CSV a la nueva base de datos finalizada correctamente."
        )
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar CargadorBDD.py: código {e.returncode}"
        marcar_error_en_pantalla("Error en el cargador de nueva base de datos.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        if e.stderr:
            imprimir_linea(f"STDERR: {e.stderr}", "error")
    except Exception as e:
        mensaje = f"Error inesperado al ejecutar CargadorBDD.py: {str(e)}"
        marcar_error_en_pantalla("Error inesperado en el cargador de nueva base de datos.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)


# ---------------------------------------
# Manejo de botones y multi-hilo
# ---------------------------------------
def set_buttons_state(state: str) -> None:
    """Habilita / deshabilita todos los botones."""
    for btn in all_buttons:
        btn.config(state=state)


def run_in_thread(func, status_text: str) -> None:
    """Ejecuta func() en un hilo aparte y controla estado de botones."""

    def worker():
        try:
            func()
        finally:
            # Al finalizar, habilitar botones de nuevo
            set_buttons_state("normal")

    # Cada vez que iniciamos una ejecución, volvemos al color normal
    resetear_color_pantalla(status_text)
    limpiar_salida()
    set_buttons_state("disabled")
    threading.Thread(target=worker, daemon=True).start()


def start_execution_all() -> None:
    run_in_thread(execute_all, "Ejecutando: Todo (scripts, SPs y backup)...")


def start_execution_carga_datos() -> None:
    run_in_thread(
        execute_carga_datos, "Ejecutando: Carga Datos (scripts y SPs, sin backup)..."
    )


def start_execution_backup() -> None:
    run_in_thread(execute_only_backup, "Ejecutando: Backup...")


def start_execution_procedures() -> None:
    run_in_thread(
        execute_only_sps, "Ejecutando: Procedimientos (solo stored procedures)..."
    )


def start_execution_main_procesador() -> None:
    run_in_thread(
        execute_main_procesador, "Ejecutando: Procesador de PDFs..."
    )


def start_execution_database_loader() -> None:
    run_in_thread(
        execute_database_loader, "Ejecutando: Carga a Base de Datos..."
    )


def start_execution_new_database_loader() -> None:
    run_in_thread(
        execute_new_database_loader, "Ejecutando: Carga a Nueva Base de Datos..."
    )


def execute_descarga_diaria() -> None:
    """Ejecuta DescargarArchivos.py para descargar archivos."""
    escribir_log("Iniciando descarga diaria de archivos.")
    imprimir_linea("Iniciando descarga diaria de archivos...", "normal")

    try:
        result = subprocess.run(
            ["python", "DescargarArchivos.py"],
            check=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                escribir_log(line)
                if 'error' in line.lower():
                    imprimir_linea(line, "error")
                else:
                    imprimir_linea(line, "normal")

        if result.stderr:
            for line in result.stderr.splitlines():
                escribir_log(f"STDERR: {line}")
                imprimir_linea(f"STDERR: {line}", "error")

        escribir_log("Descarga diaria de archivos finalizada.")
        resetear_color_pantalla("Descarga diaria completada.")
        messagebox.showinfo(
            "Descarga Diaria", "Descarga de archivos finalizada correctamente."
        )
    except subprocess.CalledProcessError as e:
        mensaje = f"Error al ejecutar DescargarArchivos.py: código {e.returncode}"
        marcar_error_en_pantalla("Error en la descarga diaria.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)
        if e.stderr:
            imprimir_linea(f"STDERR: {e.stderr}", "error")
    except Exception as e:
        mensaje = f"Error inesperado al ejecutar DescargarArchivos.py: {str(e)}"
        marcar_error_en_pantalla("Error inesperado en la descarga diaria.")
        imprimir_linea(mensaje, "error")
        escribir_log(mensaje)


def start_execution_descarga_diaria() -> None:
    run_in_thread(
        execute_descarga_diaria, "Ejecutando: Descarga Diaria..."
    )


def run_script_thread(script: str, label: str) -> None:
    run_in_thread(lambda: ejecutar_script(script), f"Ejecutando: {label}...")


def crear_pestana_configuracion(notebook):
    """Crea la pestaña de configuración con todos los campos necesarios."""
    frame = ttk.Frame(notebook, padding=5)
    notebook.add(frame, text="Configuración")
    frame.pack_propagate(False)  # Evita que el frame se ajuste al contenido
    
    # Variables para los campos
    config_vars = {
        'database': {
            'user': tk.StringVar(),
            'password': tk.StringVar(),
            'host': tk.StringVar(),
            'database': tk.StringVar()
        },
        'paths': {
            'directorioBase': tk.StringVar(),
            'carpeta': tk.StringVar()
        }
    }
    
    # Frame principal con scrollbar
    main_frame = ttk.Frame(frame)
    main_frame.pack(fill="both", expand=True)
    
    # Canvas y scrollbar
    canvas = tk.Canvas(main_frame)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Frame para la configuración de la base de datos
    db_frame = ttk.LabelFrame(scrollable_frame, text="Configuración de Base de Datos", padding=5)
    db_frame.pack(fill="x", padx=2, pady=2, expand=True)
    
    # Configurar grid para que se expanda
    db_frame.columnconfigure(0, weight=0, minsize=120)  # Ancho fijo para etiquetas
    db_frame.columnconfigure(1, weight=1)  # Expande la columna de entrada
    
    # Configuración común para los campos de entrada de la base de datos
    db_entry_config = {
        'width': 40,  # Ancho inicial para campos de base de datos
        'font': ('Arial', 9)  # Mismo tamaño de fuente que los demás campos
    }
    
    # Campos de la base de datos
    ttk.Label(db_frame, text="Usuario:").grid(row=0, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        db_frame, 
        textvariable=config_vars['database']['user'],
        **db_entry_config
    ).grid(row=0, column=1, padx=2, pady=1, sticky="ew")
    
    ttk.Label(db_frame, text="Contraseña:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        db_frame, 
        textvariable=config_vars['database']['password'], 
        show="*",
        **db_entry_config
    ).grid(row=1, column=1, padx=2, pady=1, sticky="ew")
    
    ttk.Label(db_frame, text="Host:").grid(row=2, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        db_frame, 
        textvariable=config_vars['database']['host'],
        **db_entry_config
    ).grid(row=2, column=1, padx=2, pady=1, sticky="ew")
    
    ttk.Label(db_frame, text="Base de datos:").grid(row=3, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        db_frame, 
        textvariable=config_vars['database']['database'],
        **db_entry_config
    ).grid(row=3, column=1, padx=2, pady=1, sticky="ew")
    
    # Frame para rutas
    path_frame = ttk.LabelFrame(scrollable_frame, text="Rutas", padding=5)
    path_frame.pack(fill="x", padx=2, pady=2, expand=True)
    path_frame.columnconfigure(0, weight=0, minsize=120)  # Ancho fijo para etiquetas
    path_frame.columnconfigure(1, weight=1)  # Expande la columna de entrada
    
    # Configurar el ancho de las columnas para rutas
    path_frame.columnconfigure(0, weight=0, minsize=120)  # Ancho fijo para etiquetas
    path_frame.columnconfigure(1, weight=1)  # Expande la columna de entrada
    
    # Configuración común para los campos de entrada
    entry_config = {
        'width': 60,  # Ancho inicial más grande
        'font': ('Arial', 9)  # Fuente ligeramente más pequeña para mejor ajuste
    }
    
    ttk.Label(path_frame, text="Directorio Base:").grid(row=0, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        path_frame, 
        textvariable=config_vars['paths']['directorioBase'],
        **entry_config
    ).grid(row=0, column=1, padx=2, pady=1, sticky="ew")
    
    ttk.Label(path_frame, text="Carpeta:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
    ttk.Entry(
        path_frame, 
        textvariable=config_vars['paths']['carpeta'],
        **entry_config
    ).grid(row=1, column=1, padx=2, pady=1, sticky="ew")
    
    # Frame para botones
    btn_frame = ttk.Frame(scrollable_frame)
    btn_frame.pack(fill="x", pady=4, padx=2)
    
    # Asegurar que el frame sea del ancho del contenido
    scrollable_frame.update_idletasks()
    canvas.config(width=scrollable_frame.winfo_reqwidth())
    
    def cargar_configuracion_gui():
        """Carga la configuración actual en los campos del formulario."""
        try:
            config = cargar_configuracion()
            
            # Base de datos
            for key, value in config.get('database', {}).items():
                if key in config_vars['database']:
                    config_vars['database'][key].set(str(value) if value is not None else "")
            
            # Rutas
            for key, value in config.get('paths', {}).items():
                if key in config_vars['paths']:
                    config_vars['paths'][key].set(str(value) if value is not None else "")
            
            # No mostrar mensaje de éxito para no molestar
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la configuración: {e}")
            # Inicializar con valores por defecto si hay error
            config_vars['database']['host'].set("localhost")
    
    def guardar_configuracion():
        """Guarda la configuración en el archivo config.json"""
        try:
            config = {
                "database": {
                    "user": config_vars['database']['user'].get(),
                    "password": config_vars['database']['password'].get(),
                    "host": config_vars['database']['host'].get(),
                    "database": config_vars['database']['database'].get(),
                    "raise_on_warnings": True
                },
                "paths": {
                    "directorioBase": config_vars['paths']['directorioBase'].get(),
                    "carpeta": config_vars['paths']['carpeta'].get()
                },
                "archivos": config.get("archivos", {})  # Mantener la configuración de archivos existente
            }
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Actualizar la configuración global
            global db_config
            db_config = config['database']
            
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
    
    # Botones
    ttk.Button(btn_frame, text="Cargar Configuración", command=cargar_configuracion_gui, width=20).pack(side=tk.LEFT, padx=2, pady=2)
    ttk.Button(btn_frame, text="Guardar Cambios", command=guardar_configuracion, width=20).pack(side=tk.LEFT, padx=2, pady=2)
    
    # Ajustar el tamaño de la ventana
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))
    
    # Cargar configuración al abrir la pestaña
    cargar_configuracion_gui()
    
    return frame

# ---------------------------------------
# Interfaz gráfica (Tkinter)
# ---------------------------------------
root = tk.Tk()
root.title("Ejecutor de Scripts y Backup")
root.geometry("900x800")

# Crear el notebook (pestañas)
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=5)

# Pestaña de ejecución
frame_ejecucion = ttk.Frame(notebook)
notebook.add(frame_ejecucion, text="Ejecución")

# Pestaña de configuración
crear_pestana_configuracion(notebook)

# Estado general (arriba)
status_label = tk.Label(
    frame_ejecucion,
    text="Listo para ejecutar",
    font=("Arial", 11, "italic"),
    anchor="w",
    justify="left",
    fg=STATUS_NORMAL_COLOR,
)
status_label.pack(fill="x", padx=5, pady=(3, 2))

# Frame: Ejecuciones generales
frame_general = tk.LabelFrame(
    frame_ejecucion, text="Ejecuciones generales", font=("Arial", 11, "bold")
)
frame_general.pack(fill="x", padx=5, pady=3)

for col in range(5):
    frame_general.grid_columnconfigure(col, weight=1)

BUTTON_WIDTH = 15


btn_descarga = tk.Button(
    frame_general,
    text="Descarga Diaria",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_descarga_diaria,
)
btn_descarga.grid(row=0, column=0, padx=5, pady=5, sticky="ew")


btn_all = tk.Button(
    frame_general,
    text="Todo",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_all,
)
btn_all.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

btn_carga = tk.Button(
    frame_general,
    text="Carga Datos",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_carga_datos,
)
btn_carga.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

btn_backup = tk.Button(
    frame_general,
    text="Backup",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_backup,
)
btn_backup.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

btn_procedimientos = tk.Button(
    frame_general,
    text="Procedimientos",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_procedures,
)
btn_procedimientos.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

# Frame: Carga Inversiones / amortizaciones
frame_carga_inversiones = tk.LabelFrame(
    frame_ejecucion, text="Carga Inversiones / amortizaciones", font=("Arial", 11, "bold")
)
frame_carga_inversiones.pack(fill="x", padx=5, pady=3)

for col in range(3):
    frame_carga_inversiones.grid_columnconfigure(col, weight=1)

btn_pdf_carga = tk.Button(
    frame_carga_inversiones,
    text="Procesar PDFs",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_main_procesador,
)
btn_pdf_carga.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

btn_db_carga = tk.Button(
    frame_carga_inversiones,
    text="Cargar a old DB",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_database_loader,
)
btn_db_carga.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

btn_new_db_carga = tk.Button(
    frame_carga_inversiones,
    text="Cargar a nueva DB",
    font=("Arial", 11),
    width=BUTTON_WIDTH,
    command=start_execution_new_database_loader,
)
btn_new_db_carga.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

# Frame: Scripts individuales
frame_scripts = tk.LabelFrame(
    frame_ejecucion, text="Ejecución individual de scripts", font=("Arial", 11, "bold")
)
frame_scripts.pack(fill="x", padx=5, pady=3, expand=False)

for col in range(4):
    frame_scripts.grid_columnconfigure(col, weight=1)

scripts_buttons_info = [
    ("Acciones", "DiarioAcciones.py"),
    ("Bonos", "DiarioBonos.py"),
    ("Dividendos", "DiarioDividendos.py"),
    ("Facturas", "DiarioFacturas.py"),
    ("Genericos", "DiarioGenericos.py"),
    ("Obligaciones", "DiarioObligaciones.py"),
    ("Papeles", "DiarioPapeles.py"),
    ("Titularizaciones", "DiarioTitularizaciones.py"),
]

script_buttons = []

for idx, (label, script) in enumerate(scripts_buttons_info):
    row = idx // 4  # 0 o 1
    col = idx % 4   # 0..3
    btn = tk.Button(
        frame_scripts,
        text=label,
        font=("Arial", 11),
        width=BUTTON_WIDTH,
        command=lambda s=script, l=label: run_script_thread(s, l),
    )
    btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
    script_buttons.append(btn)

# Área de resultados con Text + Scrollbar
# Frame para la salida de texto
output_frame = tk.Frame(frame_ejecucion)
output_frame.pack(fill="both", expand=True, padx=5, pady=3)

output_text = tk.Text(
    output_frame,
    wrap="word",
    font=("Arial", 10),
    height=15
)
output_text.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(output_frame, command=output_text.yview)
scrollbar.pack(side="right", fill="y")

output_text.config(yscrollcommand=scrollbar.set)

# Configuración de tags para estilos
output_text.tag_config("normal", foreground="black")
output_text.tag_config("error", foreground="red")

# Registrar todos los botones
all_buttons = [btn_all, btn_carga, btn_backup, btn_procedimientos, btn_descarga, btn_pdf_carga, btn_db_carga, btn_new_db_carga] + script_buttons

root.mainloop()
