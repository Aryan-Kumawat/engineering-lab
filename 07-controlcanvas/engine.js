(function(root){
'use strict';
const ports={Step:0,Gain:1,Sum:2,PID:1,Saturation:1,Motor:1,Scope:1};
function validate(model){
 if(!model||model.version!==1||!Array.isArray(model.nodes)||!Array.isArray(model.edges))throw Error('Expected version 1 graph');
 if(!model.nodes.length||model.nodes.length>60||model.edges.length>120)throw Error('Graph size exceeds limits');
 const nodes=new Map();
 for(const n of model.nodes){
  if(typeof n.id!=='string'||nodes.has(n.id)||!Object.hasOwn(ports,n.type))throw Error('Invalid node or duplicate ID');
  n.p=n.p||{};
  for(const v of Object.values(n.p))if(typeof v!=='number'||!Number.isFinite(v))throw Error('Parameters must be finite numbers');
  const required={Step:['value','at'],Gain:['gain'],Sum:[],PID:['kp','ki','kd'],Saturation:['min','max'],Motor:['tau'],Scope:[]}[n.type];
  if(required.some(k=>!Object.hasOwn(n.p,k)))throw Error(n.type+' parameters missing');
  if(n.type==='Motor'&&n.p.tau<=0)throw Error('Motor tau must be positive');
  if(n.type==='Saturation'&&n.p.min>n.p.max)throw Error('Saturation min must be <= max');
  nodes.set(n.id,n);
 }
 const inputs=new Map();
 for(const e of model.edges){
  if(!nodes.has(e.from)||!nodes.has(e.to)||!Number.isInteger(e.port)||e.port<0||e.port>=ports[nodes.get(e.to).type])throw Error('Invalid wire');
  const key=e.to+':'+e.port;if(inputs.has(key))throw Error('Only one wire per input');inputs.set(key,e.from);
 }
 for(const n of model.nodes)for(let p=0;p<ports[n.type];p++)if(!inputs.has(n.id+':'+p))throw Error(n.id+' has an unconnected input '+p);
 // Stateful motor outputs are available before evaluating direct-feedthrough blocks.
 const order=[],visiting=new Set(),done=new Set();
 function visit(id){if(done.has(id))return;if(visiting.has(id))throw Error('Algebraic loop: add a Motor state to break feedback');visiting.add(id);
 const n=nodes.get(id);if(n.type!=='Motor')for(let p=0;p<ports[n.type];p++)visit(inputs.get(id+':'+p));
 visiting.delete(id);done.add(id);order.push(n);}
 for(const n of model.nodes)visit(n.id);
 return {nodes,inputs,order};
}
function simulate(model,{dt=.01,duration=10}={}){
 if(!Number.isFinite(dt)||!Number.isFinite(duration)||dt<=0||duration<dt||duration/dt>100000)throw Error('Use positive duration/dt with 1–100,000 steps');
 const {inputs,order}=validate(model),state={},out={},rows=[];
 for(const n of order){state[n.id]={y:0,i:0,last:0,filter:0};if(n.type==='Motor'&&dt>n.p.tau/10)throw Error('Use dt <= smallest motor tau / 10');}
 const ids=order.map(n=>n.id);
 for(let step=0;step<=Math.floor(duration/dt);step++){
 const t=step*dt;
 for(const n of order){const p=n.p,s=state[n.id],get=k=>out[inputs.get(n.id+':'+k)];let v;
 switch(n.type){
 case 'Motor':v=s.y;break;
 case 'Step':v=t>=p.at?p.value:0;break;
 case 'Gain':v=get(0)*p.gain;break;
 case 'Sum':v=get(0)-get(1);break;
 case 'Saturation':v=Math.max(p.min,Math.min(p.max,get(0)));break;
 case 'Scope':v=get(0);break;
 case 'PID':{const e=get(0);s.i+=e*dt;const d=step?(e-s.last)/dt:0;s.filter+=dt/(.05+dt)*(d-s.filter);v=p.kp*e+p.ki*s.i+p.kd*s.filter;s.last=e;break;}
 }
 if(!Number.isFinite(v)||Math.abs(v)>1e12)throw Error('Simulation diverged at '+t.toFixed(3)+' s');out[n.id]=v;
 }
 rows.push([t,...ids.map(id=>out[id])]);
 for(const n of order)if(n.type==='Motor'){const u=out[inputs.get(n.id+':0')],s=state[n.id];s.y=u+(s.y-u)*Math.exp(-dt/n.p.tau);}
 }
 return {headers:['time_s',...ids],rows};
}
function example(kind='PI'){
 const nodes=[{id:'target',type:'Step',p:{value:1,at:0},x:30,y:90},{id:'error',type:'Sum',p:{},x:220,y:90},{id:'controller',type:'PID',p:{kp:2,ki:kind==='P'?0:1,kd:kind==='PID'?.1:0},x:420,y:90},{id:'motor',type:'Motor',p:{tau:1},x:620,y:90},{id:'speed',type:'Scope',p:{},x:620,y:260}];
 return {version:1,nodes,edges:[{from:'target',to:'error',port:0},{from:'motor',to:'error',port:1},{from:'error',to:'controller',port:0},{from:'controller',to:'motor',port:0},{from:'motor',to:'speed',port:0}]};
}
const api={ports,validate,simulate,example};if(typeof module!=='undefined')module.exports=api;else root.ControlCanvas=api;
})(typeof globalThis!=='undefined'?globalThis:this);
