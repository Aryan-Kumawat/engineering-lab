"""Desktop experiment workspace. All simulation work runs outside Tk's UI thread."""
import bisect
import json
import math
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import numpy as np
from . import __version__
from .engine import run_experiment
from .experiment import load_experiment,prepare_experiment
from .results import atomic_json,load_run,export_csv,compare_runs
from .robot import Robot,forward
from .workspace import initialize,save_workspace_run,discover_runs


class App:
    def __init__(self,root,workspace=None):
        self.root=root;self.workspace=None;self.source=None;self.current=None;self.baseline=None
        self.current_robot=None;self.busy=False;self.dirty=False;self.queue=queue.Queue();self.stop=threading.Event()
        self.generation=0;self.frame_index=0;self.yaw=-.7;self.pitch=.55;self.zoom=1.;self.drag=None
        self.history_paths={};self.events=[];self.experiment_paths={}
        root.title('RobotBench · robot experiment workbench');root.geometry('1320x920');root.configure(bg='#0c1422')
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('.',background='#142236',foreground='#dde8f5',fieldbackground='#1c2e46',bordercolor='#334962')
        style.configure('TFrame',background='#142236');style.configure('TLabel',background='#142236')
        style.configure('TButton',padding=(9,7),background='#233c57');style.map('TButton',background=[('active','#345474')])
        style.configure('TNotebook',background='#0c1422');style.configure('TNotebook.Tab',padding=(14,7),background='#20344c',foreground='#c9d9ee')
        style.map('TNotebook.Tab',background=[('selected','#315572')],foreground=[('selected','#ffffff')])
        style.map('TCombobox',fieldbackground=[('readonly','#1c2e46')],foreground=[('readonly','#dde8f5')],selectbackground=[('readonly','#315572')],selectforeground=[('readonly','#ffffff')])
        style.configure('Horizontal.TProgressbar',troughcolor='#1c2e46',background='#64dfc0')
        style.configure('Treeview',background='#17283e',fieldbackground='#17283e',rowheight=26)
        style.map('Treeview',background=[('selected','#285b76')]);style.configure('TEntry',fieldbackground='#1c2e46')
        style.configure('Header.TLabel',font=('',24,'bold'));style.configure('Muted.TLabel',foreground='#9fb2cc')
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        header=ttk.Frame(outer);header.pack(fill='x')
        ttk.Label(header,text='RobotBench',style='Header.TLabel').pack(side='left')
        ttk.Label(header,text='  EXPERIMENT WORKSPACE  /  '+__version__,style='Muted.TLabel').pack(side='left')
        self.status_badge=ttk.Label(header,text='READY',foreground='#66dfc0');self.status_badge.pack(side='right')
        toolbar=ttk.Frame(outer);toolbar.pack(fill='x',pady=12)
        for text,command in [('Open workspace',self.choose_workspace),('Save experiment',self.save_experiment),
                             ('Open run',self.open_run),('Save run',self.save_current_run),('Export CSV',self.export_csv),('Pin baseline',self.pin_baseline)]:
            ttk.Button(toolbar,text=text,command=command).pack(side='left',padx=3)
        self.run_button=ttk.Button(toolbar,text='▶ Run experiment',command=self.start);self.run_button.pack(side='right',padx=3)
        self.cancel_button=ttk.Button(toolbar,text='Cancel run',command=self.cancel_run,state='disabled');self.cancel_button.pack(side='right',padx=3)
        self.workspace_label=ttk.Label(outer,text='Choose a workspace directory',style='Muted.TLabel');self.workspace_label.pack(anchor='w',pady=(0,10))
        split=ttk.Panedwindow(outer,orient='horizontal');split.pack(fill='both',expand=True)
        sidebar=ttk.Frame(split,padding=10);split.add(sidebar,weight=1)
        ttk.Label(sidebar,text='EXPERIMENT',font=('',11,'bold')).pack(anchor='w',pady=(0,8))
        self.experiment_name=tk.StringVar()
        self.experiments=ttk.Combobox(sidebar,textvariable=self.experiment_name,state='readonly',width=27)
        self.experiments.pack(fill='x');self.experiments.bind('<<ComboboxSelected>>',self.select_experiment)
        ttk.Label(sidebar,text='Controller gains · scalar or JSON array',style='Muted.TLabel').pack(anchor='w',pady=(16,6))
        self.gains={}
        for key in ['kp','ki','kd']:
            ttk.Label(sidebar,text=key.upper()).pack(anchor='w');self.gains[key]=tk.StringVar()
            ttk.Entry(sidebar,textvariable=self.gains[key]).pack(fill='x',pady=(2,5))
        ttk.Button(sidebar,text='Apply gains to draft',command=self.apply_gains).pack(fill='x',pady=5)
        ttk.Label(sidebar,text='RUN HISTORY',font=('',11,'bold')).pack(anchor='w',pady=(22,8))
        self.history=ttk.Treeview(sidebar,columns=('file',),show='headings',height=9,selectmode='browse')
        self.history.heading('file',text='Select a run to replay');self.history.column('file',width=220)
        self.history.pack(fill='both',expand=True);self.history.bind('<<TreeviewSelect>>',self.select_run)
        ttk.Button(sidebar,text='Refresh history',command=self.refresh_history).pack(fill='x',pady=8)
        self.notebook=ttk.Notebook(split);split.add(self.notebook,weight=5)
        view=ttk.Frame(self.notebook,padding=10);config=ttk.Frame(self.notebook,padding=10)
        event_tab=ttk.Frame(self.notebook,padding=10);compare=ttk.Frame(self.notebook,padding=10)
        for label,tab in [('Replay + signals',view),('Experiment JSON',config),('Diagnostics',event_tab),('Compare runs',compare)]:self.notebook.add(tab,text=label)
        self.canvas=tk.Canvas(view,bg='#0d1727',highlightthickness=0,height=345);self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw_robot());self.canvas.bind('<ButtonPress-1>',self.begin_drag)
        self.canvas.bind('<B1-Motion>',self.orbit);self.canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag',None))
        self.canvas.bind('<MouseWheel>',lambda e:self.change_zoom(1.12 if e.delta>0 else 1/1.12))
        self.canvas.bind('<Button-4>',lambda e:self.change_zoom(1.12));self.canvas.bind('<Button-5>',lambda e:self.change_zoom(1/1.12))
        replay=ttk.Frame(view);replay.pack(fill='x',pady=8)
        ttk.Button(replay,text='Play',command=self.play).pack(side='left');ttk.Button(replay,text='Pause',command=self.pause).pack(side='left',padx=5)
        self.scrub=ttk.Scale(replay,from_=0,to=1,command=self.seek);self.scrub.pack(side='left',fill='x',expand=True,padx=8)
        self.clock=ttk.Label(replay,text='0.000 s');self.clock.pack(side='right')
        plotbar=ttk.Frame(view);plotbar.pack(fill='x')
        self.joint=tk.StringVar();self.joint_choice=ttk.Combobox(plotbar,textvariable=self.joint,state='readonly',width=18);self.joint_choice.pack(side='left')
        self.signal=tk.StringVar(value='Position');signal=ttk.Combobox(plotbar,textvariable=self.signal,values=['Position','Tracking error','Effort'],state='readonly',width=18);signal.pack(side='left',padx=8)
        for widget in [self.joint_choice,signal]:widget.bind('<<ComboboxSelected>>',lambda e:self.draw_signals())
        ttk.Label(plotbar,text='Green: actual / signal · gold: target · pink: baseline',style='Muted.TLabel').pack(side='left')
        self.plot=tk.Canvas(view,bg='#0d1727',height=190,highlightthickness=0);self.plot.pack(fill='x',pady=8);self.plot.bind('<Configure>',lambda e:self.draw_signals())
        self.metrics_label=ttk.Label(view,text='Run an experiment to inspect its tracking and geometry.',wraplength=1000);self.metrics_label.pack(fill='x')
        ttk.Label(config,text='Draft changes run as a snapshot. Save experiment to keep them in the workspace. SI units: metres, radians, seconds.').pack(anchor='w',pady=(0,8))
        self.editor=tk.Text(config,background='#0d1727',foreground='#dce8f7',insertbackground='#ffffff',wrap='none',undo=True,font=('monospace',11))
        self.editor.pack(fill='both',expand=True);self.editor.bind('<<Modified>>',self.editor_changed)
        self.editor.bind('<Control-a>',self.select_all)
        self.event_table=ttk.Treeview(event_tab,columns=('time','level','code','message'),show='headings')
        for key,width in [('time',85),('level',85),('code',160),('message',550)]:self.event_table.heading(key,text=key.title());self.event_table.column(key,width=width)
        self.event_table.pack(fill='both',expand=True);self.event_table.bind('<<TreeviewSelect>>',self.select_event)
        ttk.Label(event_tab,text='Click an event to jump to its sample. Collisions and joint limits terminate the run.',style='Muted.TLabel').pack(anchor='w',pady=8)
        self.comparison=tk.Text(compare,bg='#0d1727',fg='#dce8f7',wrap='word',font=('monospace',11));self.comparison.pack(fill='both',expand=True);self.comparison.configure(state='disabled')
        bottom=ttk.Frame(outer);bottom.pack(fill='x',pady=(10,0))
        self.progress=ttk.Progressbar(bottom,length=140,maximum=100);self.progress.pack(side='right')
        self.status=tk.StringVar(value='Local joint-servo simulation · geometric collision checks · no hardware commands')
        ttk.Label(bottom,textvariable=self.status,wraplength=1100).pack(side='left')
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(50,self.poll)
        if workspace is not None:self.set_workspace(workspace)
        else:root.after(0,self.choose_workspace)

    def select_all(self,event):
        self.editor.tag_add('sel','1.0','end');return 'break'

    def editor_changed(self,event=None):
        if self.editor.edit_modified():self.dirty=True;self.editor.edit_modified(False)

    def replace_editor(self,value):
        self.editor.delete('1.0','end');self.editor.insert('1.0',json.dumps(value,indent=2));self.editor.edit_modified(False);self.dirty=False
        for key in self.gains:self.gains[key].set(json.dumps(value.get('controller',{}).get(key,0)))

    def discard_ok(self):
        return not self.dirty or messagebox.askyesno('Unsaved experiment draft','Discard the unsaved experiment draft and continue?')

    def choose_workspace(self):
        if self.busy:return
        if not self.discard_ok():return
        path=filedialog.askdirectory(title='Choose a workspace (an empty folder creates the bundled examples)')
        if path:
            try:self.set_workspace(path)
            except (OSError,ValueError) as exc:messagebox.showerror('Workspace error',str(exc))

    def set_workspace(self,path):
        path=Path(path).resolve()
        if not path.exists() or not any(path.iterdir()):initialize(path)
        candidates={}
        for file in sorted(path.glob('*.json')):
            if file.stat().st_size>200000:continue
            try:
                raw=json.loads(file.read_text(encoding='utf-8'))
                if isinstance(raw,dict) and isinstance(raw.get('robot'),str):candidates[file.name]=file
            except (OSError,ValueError):continue
        if not candidates:raise ValueError('No experiment JSON found. Use an empty directory for bundled examples.')
        self.pause();self.workspace=path;self.experiment_paths=candidates;self.workspace_label.configure(text=str(path))
        self.experiments.configure(values=list(candidates));name='reach.json' if 'reach.json' in candidates else next(iter(candidates))
        self.experiment_name.set(name);self.load_source(candidates[name]);self.refresh_history()

    def select_experiment(self,event=None):
        if self.busy:return
        if not self.discard_ok():
            if self.source:self.experiment_name.set(self.source.name)
            return
        try:self.load_source(self.experiment_paths[self.experiment_name.get()])
        except (OSError,ValueError) as exc:messagebox.showerror('Experiment error',str(exc))

    def load_source(self,path):
        config,robot=load_experiment(path);self.source=Path(path);self.replace_editor(config)
        self.preview_robot=robot;self.preview_config=config
        self.current=None;self.current_robot=None;self.pause();self.frame_index=0;self.events=[]
        self.event_table.delete(*self.event_table.get_children());self.scrub.configure(to=1);self.scrub.set(0);self.clock.configure(text='0.000 s')
        self.joint_choice.configure(values=robot.names);self.joint.set(robot.names[0]);self.draw_robot();self.draw_signals()
        self.metrics_label.configure(text=f'{robot.name} · {len(robot.active)} joints · {config["duration_s"]:g} s · seed {config["seed"]}')
        self.status.set('Experiment loaded. Run as-is, apply gains, or edit the JSON draft.');self.status_badge.configure(text='READY',foreground='#66dfc0')

    def apply_gains(self):
        try:
            raw=json.loads(self.editor.get('1.0','end'));raw['controller']={k:json.loads(v.get()) for k,v in self.gains.items()}
            config,robot=prepare_experiment(raw,self.source.parent)
            self.replace_editor(config);self.dirty=True;self.preview_config=config;self.preview_robot=robot
            self.status.set('Controller changes applied to the draft. Run to measure the effect.')
        except (ValueError,TypeError,AttributeError) as exc:messagebox.showerror('Invalid controller',str(exc))

    def save_experiment(self):
        if not self.source:return
        try:
            raw=json.loads(self.editor.get('1.0','end'));config,_=prepare_experiment(raw,self.source.parent)
            path=filedialog.asksaveasfilename(initialdir=self.source.parent,initialfile=self.source.name,defaultextension='.json')
            if not path:return
            prepare_experiment(config,Path(path).parent)
            atomic_json(path,config);self.source=Path(path);self.dirty=False
            self.experiment_paths[self.source.name]=self.source;self.experiments.configure(values=list(self.experiment_paths));self.experiment_name.set(self.source.name)
            self.status.set('Saved experiment '+str(path))
        except (OSError,ValueError,TypeError) as exc:messagebox.showerror('Save failed',str(exc))

    def start(self):
        if self.busy or not self.source:return
        try:config,robot=prepare_experiment(json.loads(self.editor.get('1.0','end')),self.source.parent)
        except (OSError,ValueError,TypeError) as exc:messagebox.showerror('Invalid experiment',str(exc));return
        self.pause();self.busy=True;self.stop.clear();self.run_button.configure(state='disabled');self.cancel_button.configure(state='normal');self.experiments.configure(state='disabled')
        self.status_badge.configure(text='RUNNING',foreground='#f2c779');self.progress['value']=0;self.status.set('Running a frozen experiment snapshot…')
        workspace=self.workspace
        def worker():
            try:
                result=run_experiment(config,robot,cancel=self.stop,progress=lambda value:self.queue.put(('progress',value)))
                error=None;path=None
                try:path=save_workspace_run(workspace,result)
                except (OSError,ValueError) as exc:error=str(exc)
                self.queue.put(('done',(result,path,error)))
            except Exception as exc:self.queue.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def cancel_run(self):
        self.stop.set();self.status.set('Cancellation requested; waiting for the next simulation sample boundary.')

    def poll(self):
        try:
            while True:
                kind,value=self.queue.get_nowait()
                if kind=='progress':self.progress['value']=value*100
                elif kind in {'done','error'}:
                    self.busy=False;self.run_button.configure(state='normal');self.cancel_button.configure(state='disabled');self.experiments.configure(state='readonly')
                    if kind=='error':self.status_badge.configure(text='ERROR',foreground='#f28f9e');self.status.set(value)
                    else:
                        result,path,error=value;self.show_run(result);self.refresh_history()
                        if error:
                            self.status.set('Result is in memory; automatic save failed: '+error)
                            messagebox.showwarning('Run not saved','Automatic save failed. Use Save run to choose another destination. '+error)
                        else:self.status.set('Run saved: '+str(path))
        except queue.Empty:pass
        self.root.after(50,self.poll)

    def refresh_history(self):
        self.history.delete(*self.history.get_children());self.history_paths={}
        if not self.workspace:return
        for index,path in enumerate(discover_runs(self.workspace)[:200]):
            key=str(index);self.history_paths[key]=path;self.history.insert('','end',iid=key,values=(path.name.replace('.run.json',''),))

    def select_run(self,event=None):
        selected=self.history.selection()
        if selected:
            try:self.show_run(load_run(self.history_paths[selected[0]]));self.status.set('Replaying '+str(self.history_paths[selected[0]]))
            except (OSError,ValueError) as exc:messagebox.showerror('Run load failed',str(exc))

    def open_run(self):
        path=filedialog.askopenfilename(initialdir=self.workspace,filetypes=[('Run JSON','*.json')])
        if path:
            try:self.show_run(load_run(path));self.status.set('Replaying saved snapshot '+path)
            except (OSError,ValueError) as exc:messagebox.showerror('Run load failed',str(exc))

    def show_run(self,run):
        self.pause();self.current=run;self.current_robot=Robot.restore(run['robot']);self.frame_index=0
        self.joint_choice.configure(values=run['joint_names'])
        if self.joint.get() not in run['joint_names']:self.joint.set(run['joint_names'][0])
        self.times=[s['time_s'] for s in run['samples']];self.scrub.configure(to=len(run['samples'])-1);self.scrub.set(0)
        self.events=run['events'];self.event_table.delete(*self.event_table.get_children())
        for index,event in enumerate(self.events):self.event_table.insert('','end',iid=str(index),values=(f'{event["time_s"]:.3f}',event['level'],event['code'],event['message']))
        self.status_badge.configure(text=run['status'].upper(),foreground='#66dfc0' if run['status']=='completed' else '#f28f9e')
        m=run['metrics'];self.metrics_label.configure(text=f'{run["experiment"]["name"]} · RMS error {m["rms_error_rad"]:.5f} rad · {len(run["samples"])} samples · {run["failure_reason"] or "goal reached"}')
        self.update_comparison();self.draw_robot();self.draw_signals()

    def seek(self,value):
        if not self.current:return
        self.frame_index=max(0,min(len(self.current['samples'])-1,round(float(value))))
        self.clock.configure(text=f'{self.current["samples"][self.frame_index]["time_s"]:.3f} s')
        self.draw_robot();self.draw_signals()

    def play(self):
        if not self.current:return
        if self.frame_index>=len(self.times)-1:self.scrub.set(0)
        self.generation+=1;generation=self.generation;started=time.monotonic();offset=self.times[self.frame_index]
        def tick():
            if generation!=self.generation:return
            t=offset+time.monotonic()-started;index=min(len(self.times)-1,bisect.bisect_left(self.times,t));self.scrub.set(index)
            if index<len(self.times)-1:self.root.after(25,tick)
        tick()

    def pause(self):self.generation+=1

    def begin_drag(self,event):self.drag=(event.x,event.y,self.yaw,self.pitch)

    def orbit(self,event):
        if self.drag:
            x,y,a,b=self.drag;self.yaw=a+(event.x-x)*.008;self.pitch=max(-1.4,min(1.4,b+(event.y-y)*.008));self.draw_robot()

    def change_zoom(self,factor):self.zoom=max(.3,min(4.,self.zoom*factor));self.draw_robot()

    def draw_robot(self):
        canvas=self.canvas;canvas.delete('all')
        robot=self.current_robot if self.current else getattr(self,'preview_robot',None)
        if robot is None:return
        c=self.current['experiment'] if self.current else self.preview_config
        row=self.current['samples'][self.frame_index] if self.current else None
        q=row['positions_rad'] if row else c['initial_rad'];goal=row['targets_rad'] if row else c['waypoints'][0]['positions_rad']
        points,_=forward(robot,q,c['tool_offset_m']);target,_=forward(robot,goal,c['tool_offset_m'])
        reach=max(.3,sum(np.linalg.norm(j.xyz) for j in robot.joints)+np.linalg.norm(c['tool_offset_m']))
        center=np.array([0.,0.,reach*.25]);a,b=self.yaw,self.pitch
        rotation=np.array([[math.cos(a),-math.sin(a),0],[math.sin(b)*math.sin(a),math.sin(b)*math.cos(a),math.cos(b)],[-math.cos(b)*math.sin(a),-math.cos(b)*math.cos(a),math.sin(b)]])
        scale=min(max(canvas.winfo_width(),200),max(canvas.winfo_height(),200))*.65/reach*self.zoom
        def project(p):
            v=(np.asarray(p)-center)@rotation.T
            return np.column_stack((v[:,0]*scale+canvas.winfo_width()/2,-v[:,1]*scale+canvas.winfo_height()/2))
        for x in np.linspace(-reach,reach,9):
            for line in [[(x,-reach,0),(x,reach,0)],[(-reach,x,0),(reach,x,0)]]:
                canvas.create_line(*project(line).ravel(),fill='#1d3047')
        for obstacle in c['obstacles']:
            x,y=project([obstacle['center_m']])[0];r=obstacle['radius_m']*scale
            canvas.create_oval(x-r,y-r,x+r,y+r,outline='#f18d9d',fill='#502c40',stipple='gray25',width=2)
            canvas.create_text(x,y-r-12,text=obstacle['id'],fill='#f18d9d')
        if self.current and self.frame_index:
            trail=[s['tip_m'] for s in self.current['samples'][:self.frame_index+1:max(1,self.frame_index//200)]]
            if len(trail)>1:canvas.create_line(*project(trail).ravel(),fill='#d4a55f',width=1)
        canvas.create_line(*project(target).ravel(),fill='#6a7c95',dash=(4,4),width=3)
        color='#f18d9d' if row and row['clearance_m'] is not None and row['clearance_m']<=0 else '#64dfc0'
        for p1,p2 in zip(project(points),project(points)[1:]):canvas.create_line(*p1,*p2,fill=color,width=7,capstyle='round')
        for x,y in project(points):canvas.create_oval(x-4,y-4,x+4,y+4,fill='#f0c875',outline='')
        canvas.create_text(14,16,anchor='nw',text=f'{robot.name} · {len(robot.active)} joints\nGreen: robot · dashed: target · gold: tip trail',fill='#d4e1f2')
        canvas.create_text(14,canvas.winfo_height()-14,anchor='sw',text='Drag to orbit · scroll to zoom · skeleton/capsule geometry',fill='#93abc8')

    def draw_signals(self):
        canvas=self.plot;canvas.delete('all')
        if not self.current:return
        names=self.current['joint_names']
        if self.joint.get() not in names:return
        index=names.index(self.joint.get());rows=self.current['samples'];mode=self.signal.get()
        def values(run):
            data=run['samples']
            if mode=='Effort':return [s['effort_nm'][index] for s in data]
            if mode=='Tracking error':return [s['targets_rad'][index]-s['positions_rad'][index] for s in data]
            return [s['positions_rad'][index] for s in data]
        series=[(self.times,values(self.current),'#64dfc0')]
        if mode=='Position':series.append((self.times,[s['targets_rad'][index] for s in rows],'#f0c875'))
        if self.baseline and self.baseline['robot']==self.current['robot']:series.append(([s['time_s'] for s in self.baseline['samples']],values(self.baseline),'#ee8eaf'))
        all_values=[v for _,ys,_ in series for v in ys];low=min(0.,min(all_values));high=max(0.,max(all_values));span=max(high-low,1e-6)
        width=max(canvas.winfo_width(),300);height=max(canvas.winfo_height(),150);left,top,right,bottom=65,18,width-16,height-29
        end=max([ts[-1] for ts,_,_ in series]+[.001])
        for i in range(5):
            y=top+(bottom-top)*i/4;canvas.create_line(left,y,right,y,fill='#24364e');canvas.create_text(left-7,y,text=f'{high-span*i/4:.2f}',anchor='e',fill='#9fb2cc')
        for times,ys,color in series:
            stride=max(1,len(times)//1500);coordinates=[]
            for t,value in zip(times[::stride],ys[::stride]):coordinates.extend([left+t/end*(right-left),bottom-(value-low)/span*(bottom-top)])
            if len(coordinates)>2:canvas.create_line(*coordinates,fill=color,width=2)
        t=rows[self.frame_index]['time_s'];x=left+t/end*(right-left);canvas.create_line(x,top,x,bottom,fill='#dde9f7',dash=(3,3))
        canvas.create_text(left,height-10,text='0 s',anchor='w',fill='#9fb2cc');canvas.create_text(right,height-10,text=f'{end:g} s · '+('Nm' if mode=='Effort' else 'rad'),anchor='e',fill='#9fb2cc')

    def select_event(self,event=None):
        selected=self.event_table.selection()
        if selected and self.current:
            t=self.events[int(selected[0])]['time_s'];self.scrub.set(min(len(self.times)-1,bisect.bisect_left(self.times,t)));self.notebook.select(0)

    def pin_baseline(self):
        if not self.current:return
        self.baseline=self.current;self.update_comparison();self.draw_signals();self.status.set('Baseline pinned: '+self.current['run_id'][:12])

    def update_comparison(self):
        self.comparison.configure(state='normal');self.comparison.delete('1.0','end')
        if self.current and self.baseline:
            try:
                comparison=compare_runs(self.baseline,self.current)
                text='RUN COMPARISON\n\n'
                text+=f'Baseline  {self.baseline["experiment"]["name"]}\n          {self.baseline["status"].upper()} · {self.baseline["run_id"][:12]}\n'
                text+=f'Current   {self.current["experiment"]["name"]}\n          {self.current["status"].upper()} · {self.current["run_id"][:12]}\n\n'
                text+=f'RMS tracking error   {comparison["baseline_rms_error_rad"]:.6f} → {comparison["current_rms_error_rad"]:.6f} rad\n'
                text+=f'Change               {comparison["rms_error_delta_rad"]:+.6f} rad\n'
                text+='Context              '+('same; controller changes permitted' if comparison['same_experiment_context'] else 'CHANGED: '+', '.join(comparison['context_changes']))+'\n'
                text+=f'Observed duration    {comparison["baseline_observed_duration_s"]:g} / {comparison["current_observed_duration_s"]:g} s\n'
                if comparison['status_regressed']:text+='Outcome              REGRESSION: baseline passed; current did not.\n'
                text+='\nPER-JOINT RMS ERROR (rad)\n\n'
                for name,a,b in zip(self.current['joint_names'],self.baseline['metrics']['rms_per_joint_rad'],self.current['metrics']['rms_per_joint_rad']):text+=f'{name:18} {a:.6f} → {b:.6f}   delta {b-a:+.6f}\n'
                text+='\nEarly-terminated runs cover different time intervals. Compare their failure events as well as aggregate error.'
            except ValueError as exc:text=str(exc)
        else:text='Replay a run and pin it as baseline. Then replay another run or change controller gains and run again.'
        self.comparison.insert('1.0',text);self.comparison.configure(state='disabled')

    def save_current_run(self):
        if not self.current:return
        path=filedialog.asksaveasfilename(defaultextension='.run.json')
        if path:
            try:atomic_json(path,self.current);self.status.set('Saved run snapshot '+path)
            except (OSError,ValueError) as exc:messagebox.showerror('Save run failed',str(exc))

    def export_csv(self):
        if not self.current:return
        path=filedialog.asksaveasfilename(defaultextension='.csv')
        if path:
            try:export_csv(self.current,path);self.status.set('Exported '+path)
            except OSError as exc:messagebox.showerror('Export failed',str(exc))

    def close(self):
        if self.busy:
            self.cancel_run();messagebox.showinfo('Run stopping','Cancellation requested. Close again after the run has stopped and been saved.');return
        if self.discard_ok():self.pause();self.root.destroy()


def launch(workspace=None):
    root=tk.Tk()
    try:App(root,workspace)
    except (OSError,ValueError) as exc:messagebox.showerror('RobotBench startup',str(exc));root.destroy();return
    root.mainloop()
