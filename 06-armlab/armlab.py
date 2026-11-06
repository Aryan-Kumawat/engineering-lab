"""ArmLab: two-link planar arm planning. Python 3.10+, standard library."""
import math
import csv
import argparse
from pathlib import Path


def fk(lengths, joints):
    a, b = joints
    l1, l2 = lengths
    elbow = (l1*math.cos(a), l1*math.sin(a))
    return elbow, (elbow[0]+l2*math.cos(a+b), elbow[1]+l2*math.sin(a+b))


def ik(lengths, target, branch=1):
    l1, l2 = lengths
    x, y = target
    if not all(math.isfinite(v) for v in (*lengths, *target)) or min(lengths) <= 0:
        raise ValueError('Lengths must be positive and inputs finite')
    cosine = (x*x+y*y-l1*l1-l2*l2)/(2*l1*l2)
    if cosine < -1-1e-10 or cosine > 1+1e-10:
        raise ValueError('Target is outside the reachable workspace')
    b = (1 if branch >= 0 else -1)*math.acos(max(-1, min(1, cosine)))
    a = math.atan2(y, x)-math.atan2(l2*math.sin(b), l1+l2*math.cos(b))
    return a, b


def trajectory(start, end, duration=3.0, samples=151):
    if not math.isfinite(duration) or duration <= 0 or samples < 2:
        raise ValueError('Duration must be positive and samples at least two')
    if not all(math.isfinite(v) for v in (*start, *end)):
        raise ValueError('Joint angles must be finite')
    # Continuous joints: use the nearest equivalent destination angle.
    delta = [math.atan2(math.sin(b-a), math.cos(b-a)) for a,b in zip(start,end)]
    rows=[]
    for i in range(samples):
        s=i/(samples-1)
        blend=10*s**3-15*s**4+6*s**5
        rows.append((s*duration, *(a+d*blend for a,d in zip(start,delta))))
    return rows


def export(path, rows, lengths):
    with Path(path).open('w', newline='') as file:
        writer=csv.writer(file)
        writer.writerow(['time_s','joint1_rad','joint2_rad','tip_x','tip_y'])
        for t,a,b in rows:
            _, tip=fk(lengths,(a,b))
            writer.writerow([t,a,b,*tip])


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root=tk.Tk(); root.title('ArmLab · Plan a robot arm movement'); root.geometry('1000x720')
    frame=ttk.Frame(root,padding=16);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='ArmLab',font=('',24,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Click the workspace to choose a target. Plan, preview, then export.').pack(anchor='w')
    controls=ttk.Frame(frame);controls.pack(fill='x',pady=12)
    variables={}
    for key,default in [('Link 1',150),('Link 2',110),('Target X',160),('Target Y',100),('Duration',3)]:
        ttk.Label(controls,text=key).pack(side='left',padx=4)
        variables[key]=tk.StringVar(value=str(default))
        ttk.Entry(controls,width=6,textvariable=variables[key]).pack(side='left')
    branch=tk.BooleanVar(value=False)
    ttk.Checkbutton(frame,text='Use alternate elbow configuration',variable=branch).pack(anchor='w')
    canvas=tk.Canvas(frame,bg='#101a2b',highlightthickness=0);canvas.pack(fill='both',expand=True,pady=12)
    status=tk.StringVar(value='Lengths and target use the same arbitrary units. Angles exported in radians.')
    ttk.Label(frame,textvariable=status,wraplength=900).pack(anchor='w')
    state={'lengths':(150,110),'joints':(0.5,0.7),'rows':None,'playing':False,'generation':0}
    def mapping():
        w,h=canvas.winfo_width(),canvas.winfo_height()
        return w/2,h/2,min(w,h)*0.42/sum(state['lengths'])
    def draw():
        canvas.delete('all');cx,cy,scale=mapping()
        def point(p):return cx+p[0]*scale,cy-p[1]*scale
        for radius in [sum(state['lengths']),abs(state['lengths'][0]-state['lengths'][1])]:
            r=radius*scale;canvas.create_oval(cx-r,cy-r,cx+r,cy+r,outline='#344660',dash=(4,5))
        canvas.create_line(0,cy,canvas.winfo_width(),cy,fill='#24344b')
        canvas.create_line(cx,0,cx,canvas.winfo_height(),fill='#24344b')
        if state['rows']:
            points=[v for _,a,b in state['rows'] for v in point(fk(state['lengths'],(a,b))[1])]
            canvas.create_line(*points,fill='#bd94f9',width=2)
        elbow,tip=fk(state['lengths'],state['joints'])
        points=[point((0,0)),point(elbow),point(tip)]
        canvas.create_line(*[v for p in points for v in p],fill='#55d8b4',width=9,capstyle='round')
        for x,y in points:canvas.create_oval(x-6,y-6,x+6,y+6,fill='#f4cb76',outline='')
        try:
            x,y=point((float(variables['Target X'].get()),float(variables['Target Y'].get())))
            canvas.create_line(x-8,y,x+8,y,fill='#ff7990',width=2)
            canvas.create_line(x,y-8,x,y+8,fill='#ff7990',width=2)
        except ValueError:pass
        canvas.create_text(18,18,anchor='nw',fill='#cbd8e9',text='GREEN: ARM    PURPLE: TIP PATH    PINK: TARGET\nDashed circles mark reach limits')
    def plan():
        try:
            lengths=tuple(float(variables[k].get()) for k in ['Link 1','Link 2'])
            if not all(1 <= v <= 10000 for v in lengths):raise ValueError('Link lengths must be between 1 and 10000')
            target=tuple(float(variables[k].get()) for k in ['Target X','Target Y'])
            end=ik(lengths,target,-1 if branch.get() else 1)
            duration=float(variables['Duration'].get())
            if not 0.1 <= duration <= 60:raise ValueError('Duration must be 0.1 to 60 seconds')
            rows=trajectory(state['joints'],end,duration)
            state.update(lengths=lengths,rows=rows,playing=False,generation=state['generation']+1)
            draw();status.set('Path ready · 151 samples · smooth joint interpolation · simulation only')
        except ValueError as exc:messagebox.showerror('Cannot plan',str(exc))
    def play():
        if not state['rows']:return
        state['generation']+=1;generation=state['generation']
        import time
        started=time.monotonic();rows=state['rows']
        def tick():
            if generation!=state['generation']:return
            elapsed=time.monotonic()-started
            index=min(len(rows)-1,int(elapsed/rows[-1][0]*(len(rows)-1)))
            state['joints']=rows[index][1:];draw()
            if index<len(rows)-1:root.after(16,tick)
        tick()
    def save():
        if not state['rows']:
            messagebox.showinfo('Plan first','Create a path before exporting.');return
        path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if path:
            try:export(path,state['rows'],state['lengths']);status.set('Saved '+path)
            except OSError as exc:messagebox.showerror('Export failed',str(exc))
    def click(event):
        cx,cy,scale=mapping()
        variables['Target X'].set(f'{(event.x-cx)/scale:.2f}')
        variables['Target Y'].set(f'{(cy-event.y)/scale:.2f}')
        draw()
    buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8)
    for label,command in [('1 · Plan path',plan),('2 · Play',play),('3 · Export CSV',save)]:
        ttk.Button(buttons,text=label,command=command).pack(side='left',padx=4)
    canvas.bind('<Button-1>',click);canvas.bind('<Configure>',lambda event:draw())
    root.mainloop()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',type=Path,help='Export a sample path without launching the GUI')
    args=parser.parse_args()
    if args.export:
        lengths=(150,110)
        export(args.export,trajectory((0.5,0.7),ik(lengths,(160,100))),lengths)
        print('Exported',args.export)
    else:gui()
