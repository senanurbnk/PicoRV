import sys
import os
import io
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
from tkinter import font

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assembler import Assembler

class PicoAssemblerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PicoRV32 Assembler Arayüzü")
        self.root.geometry("1000x650")
        self.root.configure(padx=10, pady=10)

        header_frame = tk.Frame(root)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(header_frame, text="PicoRV32 (RV32I) Assembler Arayüzü", font=("Helvetica", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        btn_open = tk.Button(btn_frame, text="Dosya Aç (.asm)", command=self.load_file, width=15)
        btn_open.pack(side=tk.LEFT, padx=5)
        
        btn_assemble = tk.Button(btn_frame, text="Çevir (Assemble)", command=self.assemble_code, bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"), width=15)
        btn_assemble.pack(side=tk.LEFT, padx=5)

        paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=6, bg="#cccccc")
        paned_window.pack(fill=tk.BOTH, expand=True)

        input_frame = tk.Frame(paned_window, padx=5, pady=5)
        tk.Label(input_frame, text="Assembly Kodu (Girdi):", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        code_font = font.Font(family="Consolas", size=11)
        self.text_input = scrolledtext.ScrolledText(input_frame, font=code_font, wrap=tk.NONE)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        paned_window.add(input_frame, minsize=350)

        output_frame = tk.Frame(paned_window, padx=5, pady=5)
        
        out_header = tk.Frame(output_frame)
        out_header.pack(fill=tk.X, pady=(0, 5))
        tk.Label(out_header, text="Makine Kodu ve Rapor (Çıktı):", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        
        btn_copy = tk.Button(out_header, text="Çıktıyı Kopyala", command=self.copy_output)
        btn_copy.pack(side=tk.RIGHT)

        self.text_output = scrolledtext.ScrolledText(output_frame, font=code_font, wrap=tk.NONE, bg="#f8f9fa")
        self.text_output.pack(fill=tk.BOTH, expand=True)
        paned_window.add(output_frame, minsize=450)

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")])
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}")

    def assemble_code(self):
        source_code = self.text_input.get("1.0", tk.END)
        lines = source_code.splitlines(keepends=True)
        
        if not lines or all(line.strip() == "" for line in lines):
            messagebox.showwarning("Uyarı", "Girdi boş. Derlenecek kod yok.")
            return

        old_stdout = sys.stdout
        sys.stdout = my_stdout = io.StringIO()

        try:
            asm = Assembler()
            success = asm.assemble(lines, program_name="GUI", start_address=0)
            
            print("=" * 60)
            print(f"  PicoRV32 (RV32I) ASSEMBLER RAPORU")
            print(f"  Durum   : {'BAŞARILI ✓' if success else 'HATA VAR ✗'}")
            print("=" * 60)

            asm.print_listing()
            asm.print_symbol_table()
            asm.print_object_program()
            asm.print_errors()

            if success:
                binary = asm.get_binary()
                print(f"\n{'='*60}")
                print(f"  HEX DUMP ({len(binary)} byte) - Makine Kodu")
                print(f"{'='*60}")
                for i in range(0, len(binary), 16):
                    chunk = binary[i:i+16]
                    hex_part  = " ".join(f"{b:02X}" for b in chunk)
                    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    print(f"  {i:08X}  {hex_part:<47}  |{ascii_part}|")
                print(f"{'='*60}")

        except Exception as e:
            print(f"\nBeklenmeyen Hata: {e}")
        finally:
            sys.stdout = old_stdout
            
        output_text = my_stdout.getvalue()
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, output_text)

    def copy_output(self):
        output_text = self.text_output.get("1.0", tk.END)
        if output_text.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(output_text)
            messagebox.showinfo("Bilgi", "Çıktı panoya kopyalandı!")
        else:
            messagebox.showwarning("Uyarı", "Kopyalanacak çıktı yok.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PicoAssemblerGUI(root)
    root.mainloop()
