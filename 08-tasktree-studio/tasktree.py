"""TaskTree Studio: deterministic behavior-tree execution and desktop editing."""
import argparse
import json
from pathlib import Path

EXAMPLE={'type':'Sequence','name':'Pick and place','children':[
    {'type':'Action','name':'Locate part','key':'located','value':True},
    {'type':'Retry','name':'Grasp with recovery','attempts':3,'child':
        {'type':'Action','name':'Close gripper','fail_first':1,'key':'grasped','value':True}},
    {'type':'Wait','name':'Transport part','ticks':3},
    {'type':'Action','name':'Release','key':'grasped','value':False}]}


def validate(tree):
    count=0
    def visit(node,depth):
        nonlocal count
        count+=1
        if count>200 or depth>30:raise ValueError('Tree exceeds size or depth limit')
        if not isinstance(node,dict):raise ValueError('Each node must be an object')
        kind=node.get('type')
        if kind not in {'Sequence','Fallback','Retry','Wait','Action'}:raise ValueError('Unknown node type')
        if not isinstance(node.get('name'),str) or not node['name']:raise ValueError('Node name required')
        def integer(key,default,minimum):
            value=node.get(key,default)
            if type(value) is not int or not minimum<=value<=1000:raise ValueError(key+' out of range')
        if kind in {'Sequence','Fallback'}:
            children=node.get('children')
            if not isinstance(children,list) or not children:raise ValueError('Composite requires children')
            for child in children:visit(child,depth+1)
        elif kind=='Retry':
            integer('attempts',1,1);visit(node.get('child'),depth+1)
        elif kind=='Wait':integer('ticks',1,0)
        else:
            integer('fail_first',0,0)
            if 'key' in node and not isinstance(node['key'],str):raise ValueError('Blackboard key must be a string')
    visit(tree,0)


class Runner:
    def __init__(self,tree):
        validate(tree)
        self.tree=tree;self.blackboard={};self.calls={};self.cancelled=False
    def cancel(self):self.cancelled=True
    def events(self):
        yield from self._run(self.tree,'root')
    def _run(self,node,path):
        def event(status):return {'path':path,'name':node['name'],'status':status,'blackboard':dict(self.blackboard)}
        if self.cancelled:yield event('CANCELLED');return False
        yield event('RUNNING')
        kind=node['type'];success=False
        if kind=='Action':
            self.calls[path]=self.calls.get(path,0)+1
            success=self.calls[path]>node.get('fail_first',0)
            if success and 'key' in node:self.blackboard[node['key']]=node.get('value')
        elif kind=='Wait':
            for _ in range(node.get('ticks',1)):
                if self.cancelled:yield event('CANCELLED');return False
                yield event('WAITING')
            success=True
        elif kind=='Retry':
            for _ in range(node.get('attempts',1)):
                success=yield from self._run(node['child'],path+'/0')
                if success or self.cancelled:break
        else:
            success=kind=='Sequence'
            for i,child in enumerate(node['children']):
                result=yield from self._run(child,path+'/'+str(i))
                if self.cancelled:break
                if kind=='Sequence' and not result:success=False;break
                if kind=='Fallback' and result:success=True;break
        if self.cancelled:yield event('CANCELLED');return False
        yield event('SUCCESS' if success else 'FAILURE')
        return success


def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    root=tk.Tk();root.title('TaskTree Studio');root.geometry('1000x700')
    ttk.Label(root,text='TaskTree Studio',font=('',22,'bold')).pack(anchor='w',padx=16,pady=10)
    ttk.Label(root,text='Edit the tree, validate, then step through a simulated robot task.').pack(anchor='w',padx=16)
    toolbar=ttk.Frame(root);toolbar.pack(fill='x',padx=16,pady=10)
    panes=ttk.Panedwindow(root,orient='horizontal');panes.pack(fill='both',expand=True,padx=16)
    editor=tk.Text(panes,wrap='none',width=55);panes.add(editor,weight=1)
    right=ttk.Frame(panes);panes.add(right,weight=1)
    view=ttk.Treeview(right,columns=('type',),show='tree headings');view.heading('#0',text='Task');view.heading('type',text='Type');view.pack(fill='both',expand=True)
    log=tk.Text(right,height=12,state='disabled');log.pack(fill='both',expand=True)
    status=tk.StringVar(value='Load the example, or edit its JSON structure.');ttk.Label(root,textvariable=status).pack(fill='x',padx=16,pady=10)
    state={'runner':None,'iterator':None,'trace':[],'playing':False,'generation':0}
    editor.insert('1.0',json.dumps(EXAMPLE,indent=2))
    def append(event):
        state['trace'].append(event);status.set(event['name']+' · '+event['status'])
        if view.exists(event['path']):view.selection_set(event['path']);view.see(event['path'])
        log.configure(state='normal');log.insert('end',json.dumps(event)+'\n');log.see('end');log.configure(state='disabled')
    def prepare():
        try:
            tree=json.loads(editor.get('1.0','end'));runner=Runner(tree)
            state.update(runner=runner,iterator=runner.events(),trace=[],playing=False,generation=state['generation']+1)
            view.delete(*view.get_children());log.configure(state='normal');log.delete('1.0','end');log.configure(state='disabled')
            def render(n,path,parent=''):
                view.insert(parent,'end',iid=path,text=n['name'],values=(n['type'],),open=True)
                children=n.get('children',[n['child']] if 'child' in n else [])
                for i,c in enumerate(children):render(c,path+'/'+str(i),path)
            render(tree,'root');status.set('Validated. Execution uses this snapshot; prepare again after editing.')
        except (ValueError,TypeError) as exc:messagebox.showerror('Invalid tree',str(exc))
    def step():
        if not state['iterator']:return False
        try:append(next(state['iterator']));return True
        except StopIteration:state['iterator']=None;return False
    def play():
        state['generation']+=1;generation=state['generation']
        def tick():
            if generation!=state['generation']:return
            if step():root.after(250,tick)
        tick()
    def pause():state['generation']+=1
    def cancel():
        pause()
        if state['runner']:state['runner'].cancel();step()
    def save():
        path=filedialog.asksaveasfilename(defaultextension='.json')
        if path:
            try:Path(path).write_text(editor.get('1.0','end'),encoding='utf-8')
            except OSError as exc:messagebox.showerror('Save failed',str(exc))
    def load():
        path=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if path:
            try:
                content=Path(path).read_text(encoding='utf-8');validate(json.loads(content));pause();editor.delete('1.0','end');editor.insert('1.0',content);prepare()
            except (OSError,ValueError) as exc:messagebox.showerror('Load failed',str(exc))
    def export():
        path=filedialog.asksaveasfilename(defaultextension='.json')
        if path:
            try:Path(path).write_text(json.dumps(state['trace'],indent=2),encoding='utf-8')
            except OSError as exc:messagebox.showerror('Export failed',str(exc))
    for label,command in [('Prepare / reset',prepare),('Step',step),('Play',play),('Pause',pause),('Cancel',cancel),('Save tree',save),('Load tree',load),('Export trace',export)]:ttk.Button(toolbar,text=label,command=command).pack(side='left',padx=2)
    prepare();root.mainloop()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path);parser.add_argument('--example',action='store_true');args=parser.parse_args()
    if args.example or args.run:
        try:
            tree=json.loads(args.run.read_text()) if args.run else EXAMPLE
            for event in Runner(tree).events():print(json.dumps(event))
        except (OSError,ValueError) as exc:parser.error(str(exc))
    else:gui()
