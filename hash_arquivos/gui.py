"""Frontend Tk: somente a thread principal acessa widgets."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .core import ALGORITHMS, process, scan
from .exporters import export


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Hash Arquivos')
        self.geometry('1150x780')
        self.minsize(850, 600)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.results = []
        self.paths = []
        self.folder = tk.StringVar()
        self.recursive = tk.BooleanVar()
        self.algorithm = tk.StringVar(value='SHA-256')
        self.block = tk.StringVar(value='4')
        self.details = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Selecione uma pasta para começar.')
        self.selection_label = tk.StringVar(value='0 arquivos selecionados (máximo 100)')
        self.controls = []
        top = ttk.Frame(self, padding=10)
        top.pack(fill='x')
        def button(text, command):
            b = ttk.Button(top, text=text, command=command)
            b.pack(side='left', padx=4)
            self.controls.append(b)
        button('Selecionar pasta', self.choose)
        ttk.Label(top, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        check = ttk.Checkbutton(top, text='Incluir subpastas', variable=self.recursive)
        check.pack(side='left')
        self.controls.append(check)
        button('Atualizar lista', self.refresh)
        options = ttk.Frame(self, padding=10)
        options.pack(fill='x')
        ttk.Label(options, text='Algoritmo:').pack(side='left')
        combo = ttk.Combobox(options, textvariable=self.algorithm, values=list(ALGORITHMS), state='readonly', width=12)
        combo.pack(side='left', padx=5)
        self.combo = combo
        ttk.Label(options, text='Bloco (MiB, 0 < tamanho ≤ 64):').pack(side='left')
        entry = ttk.Entry(options, textvariable=self.block, width=10)
        entry.pack(side='left', padx=5)
        self.controls.append(entry)
        start = ttk.Button(options, text='Processar selecionados', command=self.start)
        start.pack(side='left', padx=5)
        self.controls.append(start)
        self.stop = ttk.Button(options, text='Cancelar', command=self.cancel.set, state='disabled')
        self.stop.pack(side='left')
        ttk.Label(self, text='Selecione com Ctrl/Shift. Se houver mais de 100 arquivos, escolha até 100 antes de iniciar.').pack(anchor='w', padx=12)
        ttk.Label(self, textvariable=self.selection_label).pack(anchor='w', padx=12)
        self.files = self.tree(self, ['Caminho do arquivo'], [1050], height=7)
        self.files.bind('<<TreeviewSelect>>', lambda e: self.selection_label.set(f'{len(self.files.selection())} de {len(self.paths)} arquivos selecionados (máximo 100)'))
        ttk.Label(self, textvariable=self.status, wraplength=1050).pack(anchor='w', padx=12)
        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.pack(fill='x', padx=12, pady=4)
        ttk.Label(self, text='Resultados — clique duas vezes para consultar os blocos').pack(anchor='w', padx=12)
        self.output = self.tree(self, ['Nome', 'Caminho', 'Bytes', 'Algoritmo', 'Hash completo', 'Blocos', 'Status'], [150, 260, 90, 90, 460, 60, 110], height=8)
        self.output.bind('<Double-1>', self.show_blocks)
        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill='x')
        ttk.Checkbutton(bottom, text='Incluir detalhes dos blocos na exportação', variable=self.details).pack(side='left')
        self.export_button = ttk.Button(bottom, text='Exportar relatório…', command=self.save, state='disabled')
        self.export_button.pack(side='right')
        self.log = tk.Text(self, height=6, state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True, padx=12, pady=5)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(80, self.poll)

    def tree(self, parent, headers, widths, height=10):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=12)
        tree = ttk.Treeview(frame, columns=list(range(len(headers))), show='headings', height=height)
        for i, (name, width) in enumerate(zip(headers, widths)):
            tree.heading(i, text=name)
            tree.column(i, width=width, stretch=False)
        y = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tree.grid(row=0, column=0, sticky='nsew')
        y.grid(row=0, column=1, sticky='ns')
        x.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def append(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def set_busy(self, busy):
        self.busy = busy
        for c in self.controls:
            c.configure(state='disabled' if busy else 'normal')
        self.combo.configure(state='disabled' if busy else 'readonly')
        self.stop.configure(state='normal' if busy else 'disabled')
        self.export_button.configure(state='normal' if self.results and not busy else 'disabled')

    def launch(self, task, done):
        self.cancel.clear()
        self.set_busy(True)
        def work():
            try:
                self.events.put((done, task()))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def choose(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)
            self.refresh()

    def refresh(self):
        if self.busy or not self.folder.get():
            return
        folder, recursive = self.folder.get(), self.recursive.get()
        self.status.set('Listando arquivos…')
        self.launch(lambda: scan(folder, recursive, self.cancel), 'scan')

    def start(self):
        if self.busy:
            return
        selected = self.files.selection()
        if not 1 <= len(selected) <= 100:
            messagebox.showwarning('Seleção necessária', 'Selecione entre 1 e 100 arquivos. Nenhum arquivo será ignorado automaticamente.')
            return
        try:
            value = float(self.block.get().replace(',', '.'))
            size = int(value * 1024 * 1024)
            if not 1 <= size <= 64 * 1024 * 1024:
                raise ValueError()
        except (ValueError, OverflowError):
            messagebox.showerror('Bloco inválido', 'Informe um tamanho maior que zero e no máximo 64 MiB.')
            return
        paths = [self.paths[int(i)] for i in selected]
        algorithm = self.algorithm.get()
        self.results = []
        self.output.delete(*self.output.get_children())
        self.append(f'Início: {len(paths)} arquivo(s), {algorithm}, bloco de {size} bytes.')
        self.progress['value'] = 0
        # Uma única atualização pendente evita acumular milhões de eventos por bloco.
        self.latest_progress = None
        self.last_file = None
        def progress(*args):
            self.latest_progress = args
        self.launch(lambda: process(paths, algorithm, size, self.cancel, progress), 'results')

    def show_blocks(self, event=None):
        selected = self.output.selection()
        if not selected:
            return
        r = self.results[int(selected[0])]
        win = tk.Toplevel(self)
        win.title('Blocos — ' + r.name)
        win.geometry('1000x500')
        ttk.Label(win, text=f'{r.path}\n{r.status}: {r.error}', wraplength=950).pack(fill='x')
        tree = self.tree(win, ['Número', 'Posição inicial (bytes)', 'Tamanho (bytes)', 'Hash independente'], [70, 160, 130, 620])
        # Inserção em lotes mantém a janela responsiva em arquivos com muitos blocos.
        def insert(start=0):
            if not tree.winfo_exists():
                return
            for b in r.blocks[start:start + 200]:
                tree.insert('', 'end', values=(b.number, b.offset, b.size, b.digest))
            if start + 200 < len(r.blocks):
                win.after(1, insert, start + 200)
        insert()

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF', '*.pdf'), ('Word 97', '*.doc'), ('Excel 97–2003', '*.xls')])
        if path:
            details = self.details.get()
            self.status.set('Exportando relatório…')
            self.launch(lambda: export(path, self.results, details), 'export')
            self.stop.configure(state='disabled')

    def poll(self):
        progress = getattr(self, 'latest_progress', None)
        if progress:
            self.latest_progress = None
            index, count, path, read, total = progress
            if getattr(self, 'last_file', None) != (index, path):
                self.last_file = (index, path)
                self.append(f'Lendo arquivo {index + 1}/{count}: {path}')
            self.progress['value'] = 100 * (index + min(read / total, 1) if total else index) / count
            self.status.set(f'Arquivo {index + 1}/{count}: {path} — {read}/{total} bytes')
        try:
            while True:
                kind, data = self.events.get_nowait()
                self.set_busy(False)
                if kind == 'scan':
                    self.paths, errors = data
                    self.files.delete(*self.files.get_children())
                    for i, path in enumerate(self.paths):
                        self.files.insert('', 'end', iid=str(i), values=(str(path),))
                    if len(self.paths) <= 100:
                        self.files.selection_set(self.files.get_children())
                    for error in errors:
                        self.append('Falha na listagem: ' + error)
                    self.status.set(f'{len(self.paths)} arquivos encontrados. {len(errors)} falha(s). ' + ('Listagem cancelada; lista parcial.' if self.cancel.is_set() else ''))
                elif kind == 'results':
                    self.latest_progress = None
                    self.results = data
                    for i, r in enumerate(data):
                        self.output.insert('', 'end', iid=str(i), values=(r.name, r.path, r.size, r.algorithm, r.digest, len(r.blocks), r.status))
                        self.append(f'{r.status}: {r.path} {r.error}')
                    self.status.set('Processamento finalizado. Consulte os status individuais.')
                    self.progress['value'] = 100
                    self.set_busy(False)
                elif kind == 'export':
                    self.status.set('Relatório exportado.')
                    self.append('Exportação concluída.')
                else:
                    self.status.set('Operação falhou.')
                    self.append('Erro: ' + data)
                    messagebox.showerror('Erro', data)
        except queue.Empty:
            pass
        self.after(80, self.poll)

    def close(self):
        if self.busy:
            self.cancel.set()
            messagebox.showinfo('Operação em andamento', 'Cancelamento solicitado. Aguarde o término antes de fechar. Exportações em andamento precisam terminar.')
        else:
            self.destroy()


def main():
    App().mainloop()
