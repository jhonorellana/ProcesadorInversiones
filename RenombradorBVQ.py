import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import re

class DateRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Renombrador de Archivos BVQ")
        self.root.geometry("600x400")
        
        # Variables
        self.original_date = tk.StringVar()
        self.new_date = tk.StringVar()
        self.directory = tk.StringVar(value=r"C:\Users\super\DATOS\004. DatosBVQ")
        
        # Fecha de hoy por defecto
        today = datetime.now().strftime("%Y_%m_%d")
        self.original_date.set(today)
        
        # Sugerir la fecha de ayer como fecha objetivo
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y_%m_%d")
        self.new_date.set(yesterday)
        
        # Interfaz
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Directorio
        dir_frame = ttk.LabelFrame(main_frame, text="Directorio Base", padding=5)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(dir_frame, textvariable=self.directory).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(dir_frame, text="Examinar...", command=self.browse_directory).pack(side=tk.LEFT, padx=2)
        
        # Fechas
        date_frame = ttk.LabelFrame(main_frame, text="Fechas", padding=5)
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="Fecha Original:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Entry(date_frame, textvariable=self.original_date).grid(row=0, column=1, sticky=tk.EW, padx=2, pady=2)
        
        ttk.Label(date_frame, text="Nueva Fecha:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Entry(date_frame, textvariable=self.new_date).grid(row=1, column=1, sticky=tk.EW, padx=2, pady=2)
        
        date_frame.columnconfigure(1, weight=1)
        
        # Vista previa
        preview_frame = ttk.LabelFrame(main_frame, text="Vista Previa", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_text = tk.Text(preview_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Generar Vista Previa", command=self.generate_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Ejecutar Cambios", command=self.execute_changes).pack(side=tk.LEFT, padx=2)
        
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.directory.get())
        if directory:
            self.directory.set(directory)
    
    def find_files_to_rename(self, directory, original_date, new_date):
        """Busca recursivamente archivos que contengan la fecha en su nombre."""
        files_to_rename = []
        
        for root, _, files in os.walk(directory):
            for filename in files:
                if original_date in filename:
                    old_path = os.path.join(root, filename)
                    new_filename = filename.replace(original_date, new_date)
                    new_path = os.path.join(root, new_filename)
                    
                    # Guardar información sobre el archivo
                    rel_path = os.path.relpath(old_path, directory)
                    files_to_rename.append({
                        'old_path': old_path,
                        'new_path': new_path,
                        'rel_path': rel_path
                    })
        
        return files_to_rename

    def generate_preview(self):
        original_date = self.original_date.get().strip()
        new_date = self.new_date.get().strip()
        base_dir = self.directory.get().strip()
        
        if not all([original_date, new_date, base_dir]):
            messagebox.showerror("Error", "Por favor complete todos los campos")
            return
        
        original_dir = os.path.join(base_dir, original_date)
        
        if not os.path.exists(original_dir):
            messagebox.showerror("Error", f"El directorio no existe: {original_dir}")
            return
        
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "=== Vista Previa de Cambios ===\n\n")
        
        # Mostrar cambio de nombre del directorio
        new_dir = os.path.join(base_dir, new_date)
        self.preview_text.insert(tk.END, f"Directorio principal:\n{original_dir}\n  -> {new_dir}\n\n")
        
        # Buscar archivos en todos los subdirectorios
        try:
            files_to_rename = self.find_files_to_rename(original_dir, original_date, new_date)
            
            if not files_to_rename:
                self.preview_text.insert(tk.END, "No se encontraron archivos para renombrar.\n")
                return
                
            self.preview_text.insert(tk.END, f"Se renombrarán {len(files_to_rename)} archivos:\n\n")
            
            # Mostrar algunos ejemplos (máximo 10 para no saturar)
            max_examples = min(10, len(files_to_rename))
            for i in range(max_examples):
                file_info = files_to_rename[i]
                self.preview_text.insert(tk.END, f"{file_info['rel_path']}\n  -> {os.path.basename(file_info['new_path'])}\n")
                
            if len(files_to_rename) > max_examples:
                remaining = len(files_to_rename) - max_examples
                self.preview_text.insert(tk.END, f"\n... y {remaining} archivos más\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar archivos: {str(e)}")
    
    def execute_changes(self):
        if not messagebox.askyesno("Confirmar", "¿Está seguro de que desea realizar los cambios?"):
            return
            
        original_date = self.original_date.get().strip()
        new_date = self.new_date.get().strip()
        base_dir = self.directory.get().strip()
        
        if not all([original_date, new_date, base_dir]):
            messagebox.showerror("Error", "Por favor complete todos los campos")
            return
        
        original_dir = os.path.join(base_dir, original_date)
        new_dir = os.path.join(base_dir, new_date)
        
        if not os.path.exists(original_dir):
            messagebox.showerror("Error", f"El directorio no existe: {original_dir}")
            return
            
        try:
            # Encontrar todos los archivos a renombrar
            files_to_rename = self.find_files_to_rename(original_dir, original_date, new_date)
            total_files = len(files_to_rename)
            
            if total_files == 0:
                messagebox.showinfo("Información", "No se encontraron archivos para renombrar.")
                return
            
            # Crear una ventana de progreso
            progress = tk.Toplevel(self.root)
            progress.title("Progreso")
            progress.geometry("400x100")
            progress.resizable(False, False)
            
            progress_label = ttk.Label(progress, text=f"Procesando 0 de {total_files} archivos...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress, orient="horizontal", length=350, mode='determinate')
            progress_bar.pack(pady=10)
            progress_bar['maximum'] = total_files
            
            progress.update()
            
            # Renombrar archivos
            success_count = 0
            for i, file_info in enumerate(files_to_rename, 1):
                try:
                    os.rename(file_info['old_path'], file_info['new_path'])
                    success_count += 1
                except Exception as e:
                    print(f"Error al renombrar {file_info['old_path']}: {str(e)}")
                
                # Actualizar la barra de progreso
                progress_bar['value'] = i
                progress_label.config(text=f"Procesando {i} de {total_files} archivos...")
                progress.update_idletasks()
            
            # Renombrar el directorio principal al final
            if success_count > 0:
                os.rename(original_dir, new_dir)
            
            progress.destroy()
            
            messagebox.showinfo("Éxito", 
                f"Proceso completado.\n"
                f"Archivos renombrados: {success_count} de {total_files}"
            )
            
            # Actualizar la vista previa
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"=== Operación completada con éxito ===\n")
            self.preview_text.insert(tk.END, f"Total de archivos renombrados: {success_count} de {total_files}\n")
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DateRenamerApp(root)
    root.mainloop()
