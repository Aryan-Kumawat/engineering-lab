"""CloudLabel desktop annotation viewer. Python 3.10+, NumPy, Tkinter."""
import copy
import itertools
import math
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
from cloud import load_cloud, demo_points, validate_box, load_annotations, save_annotations


class CloudLabel:
    def __init__(self, root):
        self.root = root
        self.points = demo_points(); self.boxes = []; self.history = []; self.future = []
        self.path = None; self.selected = None; self.autosave_job = None; self.dirty = False
        self.yaw = -.6; self.pitch = .6; self.zoom = 1.; self.pan = np.zeros(2)
        self.center = (self.points.min(0) + self.points.max(0))/2
        root.title('CloudLabel · local 3D annotations'); root.geometry('1180x800')
        frame = ttk.Frame(root, padding=12); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='CloudLabel', font=('', 24, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Drag to orbit · right-drag to pan · scroll to zoom · Shift-drag to box projected sampled points').pack(anchor='w')
        bar = ttk.Frame(frame); bar.pack(fill='x', pady=10)
        for label, action in [('Open cloud', self.open_cloud), ('Reset view', self.reset_view), ('New box', self.new_box),
                              ('Undo', self.undo), ('Redo', self.redo), ('Save labels', self.save), ('Load labels', self.load)]:
            ttk.Button(bar, text=label, command=action).pack(side='left', padx=3)
        split = ttk.Panedwindow(frame, orient='horizontal'); split.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(split, bg='#101a2a', highlightthickness=0); split.add(self.canvas, weight=4)
        side = ttk.Frame(split, padding=10); split.add(side, weight=1)
        self.table = ttk.Treeview(side, columns=('label',), show='headings', height=8, selectmode='browse')
        self.table.heading('label', text='Annotations'); self.table.pack(fill='x')
        self.table.bind('<<TreeviewSelect>>', self.select)
        self.entries = {}
        for name in ['Label', 'Min X', 'Min Y', 'Min Z', 'Max X', 'Max Y', 'Max Z']:
            ttk.Label(side, text=name).pack(anchor='w', pady=(6, 0))
            value = tk.StringVar(); self.entries[name] = value
            ttk.Entry(side, textvariable=value).pack(fill='x')
        ttk.Button(side, text='Apply box edits', command=self.apply).pack(fill='x', pady=(10, 3))
        ttk.Button(side, text='Delete selected', command=self.delete).pack(fill='x')
        self.status = tk.StringVar(value='Synthetic demo loaded. Coordinates retain source units; no unit conversion.')
        ttk.Label(frame, textvariable=self.status, wraplength=1100).pack(fill='x', pady=8)
        self.canvas.bind('<Configure>', lambda e: self.render())
        self.canvas.bind('<ButtonPress-1>', self.begin)
        self.canvas.bind('<B1-Motion>', self.move)
        self.canvas.bind('<ButtonRelease-1>', self.end)
        self.canvas.bind('<ButtonPress-3>', lambda e: setattr(self, 'drag', ('pan', e.x, e.y, self.pan.copy())))
        self.canvas.bind('<B3-Motion>', self.move)
        self.canvas.bind('<MouseWheel>', lambda e: self.scale(1.12 if e.delta > 0 else 1/1.12))
        self.canvas.bind('<Button-4>', lambda e: self.scale(1.12))
        self.canvas.bind('<Button-5>', lambda e: self.scale(1/1.12))
        root.bind('<Control-z>', lambda e: self.undo()); root.bind('<Control-y>', lambda e: self.redo())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.drag = None; self.selection_rect = None

    def project(self, points):
        cy, sy, cp, sp = math.cos(self.yaw), math.sin(self.yaw), math.cos(self.pitch), math.sin(self.pitch)
        matrix = np.array([[cy, -sy, 0], [sp*sy, sp*cy, cp], [-cp*sy, -cp*cy, sp]])
        p = (points-self.center)@matrix.T
        span = max(float(np.ptp(self.points, axis=0).max()), 1e-6)
        scale = min(self.canvas.winfo_width(), self.canvas.winfo_height())*.72/span*self.zoom
        return np.column_stack((p[:, 0]*scale+self.canvas.winfo_width()/2+self.pan[0],
                                -p[:, 1]*scale+self.canvas.winfo_height()/2+self.pan[1], p[:, 2]))

    def render(self):
        self.canvas.delete('all')
        stride = max(1, math.ceil(len(self.points)/15000))
        self.display_points = self.points[::stride]
        self.projected = self.project(self.display_points)
        for x, y, depth in self.projected[np.argsort(self.projected[:, 2])]:
            if 0 <= x <= self.canvas.winfo_width() and 0 <= y <= self.canvas.winfo_height():
                self.canvas.create_line(x, y, x+1, y, fill='#789dbd', width=2)
        for box in self.boxes:
            corners = np.array(list(itertools.product(*zip(box['min'], box['max']))))
            view = self.project(corners)
            color = '#f5c96f' if box['id'] == self.selected else '#55d4b3'
            for i in range(8):
                for j in range(i+1, 8):
                    if (i^j) in [1, 2, 4]:
                        self.canvas.create_line(*view[i, :2], *view[j, :2], fill=color, width=2)
            self.canvas.create_text(*view[0, :2], text=box['label'], anchor='sw', fill=color)
        self.canvas.create_text(14, 16, anchor='nw', fill='#d7e5f5',
                                text=f'{len(self.points):,} points · rendering {len(self.display_points):,} · {len(self.boxes)} boxes')
        if self.drag and self.drag[0] == 'select' and self.selection_rect:
            self.canvas.create_rectangle(*self.selection_rect, outline='#f5c96f', dash=(4, 3))

    def begin(self, event):
        if event.state & 0x0001:
            self.drag = ('select', event.x, event.y); self.selection_rect = (event.x, event.y, event.x, event.y)
        else:
            self.drag = ('orbit', event.x, event.y, self.yaw, self.pitch)

    def move(self, event):
        if not self.drag: return
        mode, x, y, *values = self.drag
        if mode == 'orbit':
            self.yaw = values[0]+(event.x-x)*.008
            self.pitch = max(-1.5, min(1.5, values[1]+(event.y-y)*.008))
        elif mode == 'pan': self.pan = values[0]+[event.x-x, event.y-y]
        else: self.selection_rect = (x, y, event.x, event.y)
        self.render()

    def end(self, event):
        if self.drag and self.drag[0] == 'select':
            x0, y0, x1, y1 = self.selection_rect
            p = self.projected
            mask = (p[:, 0]>=min(x0, x1)) & (p[:, 0]<=max(x0, x1)) & (p[:, 1]>=min(y0, y1)) & (p[:, 1]<=max(y0, y1))
            selected = self.display_points[mask]
            if len(selected): self.add_bounds(selected.min(0), selected.max(0))
            else: self.status.set('No displayed points in that rectangle.')
        self.drag = None; self.selection_rect = None; self.render()

    def scale(self, factor):
        self.zoom = min(20., max(.1, self.zoom*factor)); self.render()

    def reset_view(self):
        self.yaw = -.6; self.pitch = .6; self.zoom = 1.; self.pan = np.zeros(2); self.render()

    def change(self, boxes):
        if len(boxes)>500:
            messagebox.showerror('Box limit', 'At most 500 boxes are supported.'); return
        self.history.append(copy.deepcopy(self.boxes)); self.history = self.history[-50:]
        self.boxes = boxes; self.future.clear(); self.updated()

    def updated(self):
        self.dirty = True; self.refresh(); self.render()
        if self.path:
            if self.autosave_job: self.root.after_cancel(self.autosave_job)
            self.autosave_job = self.root.after(800, self.autosave)
        else: self.status.set('Unsaved labels. Save labels to choose a file and enable autosave.')

    def autosave(self):
        self.autosave_job = None
        if self.path: self.write(self.path)

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for b in self.boxes: self.table.insert('', 'end', iid=b['id'], values=(b['label'],))
        if self.selected and self.table.exists(self.selected): self.table.selection_set(self.selected)

    def select(self, event=None):
        items = self.table.selection()
        if not items: return
        self.selected = items[0]
        b = next(b for b in self.boxes if b['id']==self.selected)
        self.entries['Label'].set(b['label'])
        for side in ['Min', 'Max']:
            for i, axis in enumerate('XYZ'): self.entries[side+' '+axis].set(repr(b[side.lower()][i]))
        self.render()

    def add_bounds(self, low, high):
        padding = max(float(np.ptp(self.points, axis=0).max())*.005, 1e-6)
        b = {'id':uuid.uuid4().hex, 'label':'object', 'min':(low-padding).tolist(), 'max':(high+padding).tolist()}
        try:
            checked = validate_box(b)
        except ValueError as exc:
            self.status.set(str(exc)); return
        self.selected = b['id']; self.change([*copy.deepcopy(self.boxes), checked])
        self.select()

    def new_box(self):
        center = self.center; size = max(float(np.ptp(self.points, axis=0).max())*.1, 1e-6)
        self.add_bounds(center-size/2, center+size/2)

    def apply(self):
        if not self.selected: return
        try:
            box = validate_box({'id': self.selected, 'label':self.entries['Label'].get(),
                                'min':[float(self.entries['Min '+a].get()) for a in 'XYZ'],
                                'max':[float(self.entries['Max '+a].get()) for a in 'XYZ']})
            self.change([box if b['id']==self.selected else copy.deepcopy(b) for b in self.boxes])
        except (ValueError, TypeError) as exc: messagebox.showerror('Invalid box', str(exc))

    def delete(self):
        if self.selected: self.change([copy.deepcopy(b) for b in self.boxes if b['id']!=self.selected])
        self.selected = None

    def undo(self):
        if self.history:
            self.future.append(copy.deepcopy(self.boxes)); self.boxes = self.history.pop(); self.updated()

    def redo(self):
        if self.future:
            self.history.append(copy.deepcopy(self.boxes)); self.boxes = self.future.pop(); self.updated()

    def write(self, path):
        try:
            save_annotations(path, self.points, self.boxes); self.path = Path(path); self.dirty = False
            self.status.set('Labels saved; autosave enabled: '+str(path)); return True
        except (OSError, ValueError, TypeError) as exc:
            self.status.set('Save failed: '+str(exc)); return False

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('Annotations JSON','*.json')])
        return self.write(path) if path else False

    def discard_ok(self):
        if not self.dirty: return True
        choice = messagebox.askyesnocancel('Unsaved labels', 'Save current labels before continuing?')
        if choice is None: return False
        return self.save() if choice else True

    def open_cloud(self):
        if not self.discard_ok(): return
        path = filedialog.askopenfilename(filetypes=[('Point clouds','*.ply *.pcd')])
        if not path: return
        try: points = load_cloud(path)
        except (OSError, ValueError, UnicodeError) as exc: messagebox.showerror('Cloud load failed', str(exc)); return
        if self.autosave_job: self.root.after_cancel(self.autosave_job); self.autosave_job = None
        self.points = points; self.center = (points.min(0)+points.max(0))/2
        self.boxes = []; self.history = []; self.future = []; self.path = None; self.selected = None; self.dirty = False
        self.refresh(); self.reset_view(); self.status.set('Loaded '+Path(path).name+'; labels use source XYZ units.')

    def load(self):
        if not self.discard_ok(): return
        path = filedialog.askopenfilename(filetypes=[('Annotations JSON','*.json')])
        if not path: return
        try: boxes = load_annotations(path, self.points)
        except (OSError, ValueError, TypeError) as exc: messagebox.showerror('Labels load failed', str(exc)); return
        if self.autosave_job: self.root.after_cancel(self.autosave_job); self.autosave_job = None
        self.boxes = boxes; self.path = Path(path); self.history = []; self.future = []; self.selected = None; self.dirty = False
        self.refresh(); self.render(); self.status.set('Annotations restored. Autosave enabled: '+str(path))

    def close(self):
        if self.discard_ok():
            if self.autosave_job: self.root.after_cancel(self.autosave_job)
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk(); app = CloudLabel(root); root.mainloop()
