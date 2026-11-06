"""Tkinter report viewer; core math also works without a desktop."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core import calibrate, save_report


def launch():
    root = tk.Tk()
    root.title('CalibLab · Measure, fit, validate')
    root.geometry('1050x780')
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='CalibLab', font=('', 25, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Estimate a tool offset or coordinate-frame transform. Validate on measurements excluded from fitting.').pack(anchor='w')
    controls = ttk.Frame(frame); controls.pack(fill='x', pady=14)
    mode = tk.StringVar(value='tcp'); threshold = tk.StringVar(value='0.5')
    ttk.Combobox(controls, textvariable=mode, values=['tcp', 'registration'], state='readonly', width=18).pack(side='left')
    ttk.Label(controls, text='Residual warning (mm)').pack(side='left', padx=8)
    ttk.Entry(controls, textvariable=threshold, width=8).pack(side='left')
    status = tk.StringVar(value='Load a CSV or the included TCP demo. All lengths must use millimetres.')
    ttk.Label(frame, textvariable=status, wraplength=970).pack(anchor='w')
    summary = tk.Text(frame, height=13, wrap='word', background='#132033', foreground='#dce9f8', padx=12, pady=12)
    summary.pack(fill='x', pady=12); summary.configure(state='disabled')
    canvas = tk.Canvas(frame, height=190, background='#132033', highlightthickness=0)
    canvas.pack(fill='x')
    table = ttk.Treeview(frame, columns=['id', 'split', 'error', 'flag'], show='headings', height=7)
    for column, label in [('id','Observation'), ('split','Split'), ('error','Residual (mm)'), ('flag','Above warning')]:
        table.heading(column, text=label)
    table.pack(fill='both', expand=True, pady=12)
    state = {'report': None}

    def plot(event=None):
        canvas.delete('all')
        report = state['report']
        if report is None:
            return
        rows = report['observations']; width = max(canvas.winfo_width(), 400)
        top = max(report['warning_threshold_mm'], max(r['residual_mm'] for r in rows), 1e-9) * 1.1
        n = min(100, len(rows)); bar = (width - 80) / n
        canvas.create_text(20, 16, anchor='w', text='Residuals · green: fit · gold: held out · pink: warning threshold', fill='#dce9f8')
        for i, row in enumerate(rows[:n]):
            x = 60 + i * bar; y = 155 - row['residual_mm'] / top * 115
            canvas.create_rectangle(x, y, x + max(1, bar-2), 155, outline='', fill='#eac271' if row['split']=='held_out' else '#60d6ba')
        y = 155 - report['warning_threshold_mm'] / top * 115
        canvas.create_line(60, y, width-20, y, fill='#ef91b4', dash=(4,4))
        canvas.create_text(8, y, anchor='w', text=f'{report["warning_threshold_mm"]:g}', fill='#ef91b4')
        canvas.create_text(60, 178, anchor='w', text=f'First {n} of {len(rows)} observations; full results in table/export.', fill='#a9bbd0')

    def calculate(path):
        try:
            report = calibrate(path, mode.get(), float(threshold.get()))
        except (OSError, ValueError) as exc:
            messagebox.showerror('Calibration failed', str(exc)); return
        state['report'] = report
        content = json.dumps({k: report[k] for k in ['model', 'fit', 'held_out', 'warnings']}, indent=2)
        summary.configure(state='normal'); summary.delete('1.0','end'); summary.insert('1.0',content); summary.configure(state='disabled')
        table.delete(*table.get_children())
        for row in report['observations']:
            table.insert('', 'end', values=[row['id'], row['split'], f'{row["residual_mm"]:.5f}', 'YES' if row['above_warning_threshold'] else ''])
        status.set(f'{Path(path).name} · {report["fit"]["count"]} fit / {report["held_out"]["count"]} held out. Showing saved fit; reload after changing mode or threshold.')
        plot()

    def load():
        path = filedialog.askopenfilename(filetypes=[('Measurements CSV','*.csv')])
        if path: calculate(path)

    def demo():
        mode.set('tcp'); calculate(Path(__file__).parent / 'examples' / 'tcp.csv')

    def save():
        if state['report'] is None:
            messagebox.showinfo('No calibration', 'Load and fit measurements first.'); return
        directory = filedialog.askdirectory()
        if directory:
            try:
                save_report(state['report'], directory)
                status.set('Saved report.json and residuals.csv in ' + directory)
            except (OSError, ValueError) as exc:
                messagebox.showerror('Export failed', str(exc))

    for label, command in [('Load CSV and fit',load), ('TCP demo',demo), ('Export report',save)]:
        ttk.Button(controls, text=label, command=command).pack(side='left', padx=5)
    canvas.bind('<Configure>', plot)
    root.mainloop()
