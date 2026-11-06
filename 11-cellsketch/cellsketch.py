"""CellSketch: a workcell layout editor and deterministic simulation runner."""
import argparse
import copy
import csv
import json
from pathlib import Path
from simulator import example,validate,simulate


def save_report(report,path):
    Path(path).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def launch():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    root=tk.Tk();root.title('CellSketch · layout and throughput');root.geometry('1200x840')
    frame=ttk.Frame(root,padding=14);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='CellSketch',font=('',24,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Arrange process stations on a 40 × 25 m floor. Route order follows the station list.').pack(anchor='w')
    toolbar=ttk.Frame(frame);toolbar.pack(fill='x',pady=10)
    state={'model':example(),'report':None,'baseline':None,'selected':'load','dirty':False}
    model=state['model']
    controls={}
    settings=ttk.Frame(frame);settings.pack(fill='x')
    for label,key in [('Jobs','jobs'),('Arrival interval (s)','arrival_interval_s'),('Horizon (s)','horizon_s'),('Travel speed (m/s)','travel_speed_m_s')]:
        ttk.Label(settings,text=label).pack(side='left',padx=5)
        controls[key]=tk.StringVar(value=str(model[key]));ttk.Entry(settings,textvariable=controls[key],width=9).pack(side='left')
    split=ttk.Panedwindow(frame,orient='horizontal');split.pack(fill='both',expand=True,pady=12)
    canvas=tk.Canvas(split,background='#111d2e',highlightthickness=0);split.add(canvas,weight=4)
    side=ttk.Frame(split,padding=10);split.add(side,weight=1)
    table=ttk.Treeview(side,columns=['station'],show='headings',height=6,selectmode='browse');table.heading('station',text='Process route');table.pack(fill='x')
    entries={}
    for key in ['name','kind','x','y','cycle_s','capacity']:
        ttk.Label(side,text={'x':'X (m)','y':'Y (m)','cycle_s':'Cycle time (s)'}.get(key,key.replace('_',' ').title())).pack(anchor='w',pady=(5,0))
        entries[key]=tk.StringVar()
        if key=='kind':ttk.Combobox(side,textvariable=entries[key],values=['robot','workbench','conveyor'],state='readonly').pack(fill='x')
        else:ttk.Entry(side,textvariable=entries[key]).pack(fill='x')
    summary=tk.Text(frame,height=6,wrap='word',bg='#15243a',fg='#dbe7f5',padx=10,pady=10);summary.pack(fill='x')
    status=tk.StringVar(value='Demo loaded. Drag stations, change service times, then run.');ttk.Label(frame,textvariable=status,wraplength=1150).pack(fill='x',pady=8)

    def changed():
        state['report']=None;state['dirty']=True
        summary.delete('1.0','end');status.set('Layout changed. Run to update results.')
    def world(x,y):return 30+x/40*max(canvas.winfo_width()-60,1),30+y/25*max(canvas.winfo_height()-60,1)
    def draw(event=None):
        canvas.delete('all');stations=state['model']['stations']
        for x in range(0,41,5):
            xx,_=world(x,0);canvas.create_line(xx,30,xx,canvas.winfo_height()-30,fill='#23364e');canvas.create_text(xx,15,text=str(x),fill='#91abc9')
        for y in range(0,26,5):
            _,yy=world(0,y);canvas.create_line(30,yy,canvas.winfo_width()-30,yy,fill='#23364e')
        for a,b in zip(stations,stations[1:]):
            x,y=world(a['x'],a['y']);xx,yy=world(b['x'],b['y'])
            canvas.create_line(x,y,xx,yy,fill='#698bad',width=2,arrow='last')
        metrics={s['id']:s for s in state['report']['stations']} if state['report'] else {}
        for i,s in enumerate(stations):
            x,y=world(s['x'],s['y']);color='#f1ca78' if s['id']==state['selected'] else '#5ed9ba'
            tag='station:'+s['id']
            canvas.create_rectangle(x-50,y-26,x+50,y+26,fill='#213b53',outline=color,width=2,tags=(tag,))
            name=s['name'][:12];caption=f'{i+1}. {name}\n{s["cycle_s"]:g}s × {s["capacity"]}'
            canvas.create_text(x,y,text=caption,fill='#e5eef8',tags=(tag,))
            if s['id'] in metrics:canvas.create_text(x,y+39,text=f'Utilization {metrics[s["id"]]["utilization"]:.0%}',fill=color)
    def refresh():
        table.delete(*table.get_children())
        for i,s in enumerate(state['model']['stations']):table.insert('','end',iid=s['id'],values=(f'{i+1}. {s["name"]}',))
        if state['selected'] and table.exists(state['selected']):table.selection_set(state['selected'])
        draw()
    def select(event=None):
        selection=table.selection()
        if not selection:return
        state['selected']=selection[0]
        s=next(s for s in state['model']['stations'] if s['id']==selection[0])
        for k in entries:entries[k].set(str(s[k]))
        draw()
    table.bind('<<TreeviewSelect>>',select)
    def settings_model():
        candidate=copy.deepcopy(state['model'])
        for k,v in controls.items():candidate[k]=int(v.get()) if k=='jobs' else float(v.get())
        validate(candidate);return candidate
    def apply():
        try:
            candidate=settings_model()
            s=next((s for s in candidate['stations'] if s['id']==state['selected']),None)
            if s is None:raise ValueError('Select a station first')
            for k,v in entries.items():s[k]=int(v.get()) if k=='capacity' else float(v.get()) if k in ['x','y','cycle_s'] else v.get()
            validate(candidate);state['model']=candidate;changed();refresh()
        except (ValueError,TypeError) as exc:messagebox.showerror('Invalid settings',str(exc))
    def add():
        if len(state['model']['stations'])>=20:return
        stations=state['model']['stations'];i=1
        while any(s['id']==f'station_{i}' for s in stations):i+=1
        s={'id':f'station_{i}','name':f'Station {i}','kind':'workbench','x':20.,'y':12.,'cycle_s':3.,'capacity':1}
        stations.append(s);state['selected']=s['id'];changed();refresh();select()
    def delete():
        if len(state['model']['stations'])<=1:return
        state['model']['stations']=[s for s in state['model']['stations'] if s['id']!=state['selected']]
        state['selected']=state['model']['stations'][0]['id'];changed();refresh();select()
    def reorder(delta):
        stations=state['model']['stations'];i=next((i for i,s in enumerate(stations) if s['id']==state['selected']),0);j=i+delta
        if 0<=j<len(stations):stations[i],stations[j]=stations[j],stations[i];changed();refresh()
    def run():
        try:
            candidate=settings_model();report=simulate(candidate);state['model']=candidate;state['report']=report
            s=report['summary'];summary.delete('1.0','end')
            lines=[f'Completed: {s["completed_jobs"]}/{s["arrived_jobs"]} arrived · WIP: {s["wip_at_end"]}',
                   f'Throughput: {s["throughput_jobs_per_hour"]:.2f} jobs/hour · Highest utilization: {s["highest_utilization_station"]}',
                   f'Mean completed-job lead time: {format(s["mean_lead_time_s_completed_jobs"], ".3f") if s["mean_lead_time_s_completed_jobs"] is not None else "n/a"} seconds']
            if state['baseline']:
                baseline=state['baseline']['summary'];delta=s['throughput_jobs_per_hour']-baseline['throughput_jobs_per_hour']
                lines.append(f'Throughput change vs baseline: {delta:+.2f} jobs/hour. Baseline retains its original settings.')
            summary.insert('1.0','\n'.join(lines));status.set('Run complete. Statistics use the configured horizon; reports include settings and event trace.');draw()
        except (ValueError,TypeError) as exc:messagebox.showerror('Simulation failed',str(exc))
    def baseline():
        if state['report']:state['baseline']=copy.deepcopy(state['report']);status.set('Current simulation pinned as baseline. Change layout and run again.')
    def save():
        try:candidate=settings_model()
        except ValueError as exc:messagebox.showerror('Invalid settings',str(exc));return False
        path=filedialog.asksaveasfilename(defaultextension='.json')
        if not path:return False
        try:Path(path).write_text(json.dumps(candidate,indent=2)+'\n',encoding='utf-8')
        except OSError as exc:messagebox.showerror('Save failed',str(exc));return False
        state['model']=candidate;state['dirty']=False;status.set('Saved '+path);return True
    def load():
        if state['dirty'] and not messagebox.askyesno('Replace current layout?','Discard unsaved layout changes and load another file?'):return
        path=filedialog.askopenfilename(filetypes=[('Cell JSON','*.json')])
        if not path:return
        try:
            if Path(path).stat().st_size>200000:raise ValueError('Layout exceeds 200 KB')
            candidate=validate(json.loads(Path(path).read_text(encoding='utf-8')))
        except (OSError,ValueError,TypeError) as exc:messagebox.showerror('Load failed',str(exc));return
        state.update(model=candidate,selected=candidate['stations'][0]['id'],report=None,dirty=False)
        for k,v in controls.items():v.set(str(candidate[k]))
        state['dirty']=False
        summary.delete('1.0','end');refresh();select();status.set('Loaded '+path)
    def export():
        if not state['report']:messagebox.showinfo('Run first','Simulate the current layout before exporting.');return
        path=filedialog.asksaveasfilename(defaultextension='.json')
        if path:
            try:save_report(state['report'],path);status.set('Exported report and event trace: '+path)
            except OSError as exc:messagebox.showerror('Export failed',str(exc))
    def press(event):
        ids=canvas.find_overlapping(event.x-2,event.y-2,event.x+2,event.y+2)
        for item in reversed(ids):
            for tag in canvas.gettags(item):
                if tag.startswith('station:'):
                    state['selected']=tag.split(':',1)[1];table.selection_set(state['selected']);select();state['drag']=True;return
    def drag(event):
        if not state.get('drag'):return
        s=next(s for s in state['model']['stations'] if s['id']==state['selected'])
        s['x']=round(max(0,min(40,(event.x-30)/max(canvas.winfo_width()-60,1)*40)),2)
        s['y']=round(max(0,min(25,(event.y-30)/max(canvas.winfo_height()-60,1)*25)),2)
        entries['x'].set(str(s['x']));entries['y'].set(str(s['y']));changed();draw()
    def release(event):state['drag']=False
    canvas.bind('<Configure>',draw);canvas.bind('<ButtonPress-1>',press);canvas.bind('<B1-Motion>',drag);canvas.bind('<ButtonRelease-1>',release)
    for label,action in [('Add station',add),('Delete',delete),('Earlier',lambda:reorder(-1)),('Later',lambda:reorder(1)),('Run simulation',run),('Pin baseline',baseline),('Save layout',save),('Load layout',load),('Export report',export)]:
        ttk.Button(toolbar,text=label,command=action).pack(side='left',padx=2)
    ttk.Button(side,text='Apply station and run settings',command=apply).pack(fill='x',pady=10)
    def close():
        if not state['dirty'] or messagebox.askyesno('Unsaved layout','Close and discard unsaved layout edits?'):root.destroy()
    def settings_changed(*args):
        changed();draw()
    for variable in controls.values():variable.trace_add('write',settings_changed)
    root.protocol('WM_DELETE_WINDOW',close);refresh();select();root.mainloop()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,help='Run a layout JSON without opening the GUI')
    parser.add_argument('--demo',action='store_true',help='Run the built-in workcell without a GUI')
    parser.add_argument('--report',type=Path,default=Path('report.json'))
    parser.add_argument('--events',type=Path,help='Optional CSV event trace')
    args=parser.parse_args()
    if args.run or args.demo:
        try:
            if args.run and args.run.stat().st_size>200000:raise ValueError('Layout exceeds 200 KB')
            model=json.loads(args.run.read_text(encoding='utf-8')) if args.run else example()
            report=simulate(model);save_report(report,args.report)
            if args.events:
                with args.events.open('w',newline='',encoding='utf-8') as file:
                    writer=csv.DictWriter(file,fieldnames=['time_s','event','station','job','queue','busy']);writer.writeheader();writer.writerows(report['events'])
            print(json.dumps(report['summary'],indent=2))
        except (OSError,ValueError,TypeError) as exc:parser.error(str(exc))
    else:launch()


if __name__=='__main__':main()
