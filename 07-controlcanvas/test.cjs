const assert=require('node:assert/strict'),C=require('./engine.js');
const p=C.simulate(C.example('P'));assert(Math.abs(p.rows.at(-1)[p.headers.indexOf('motor')]-2/3)<1e-5);
const pi=C.simulate(C.example('PI'),{duration:40});assert(Math.abs(pi.rows.at(-1)[pi.headers.indexOf('motor')]-1)<1e-5);
const open={version:1,nodes:[{id:'s',type:'Step',p:{value:1,at:0}},{id:'m',type:'Motor',p:{tau:1}}],edges:[{from:'s',to:'m',port:0}]};const r=C.simulate(open);for(const row of r.rows)assert(Math.abs(row[r.headers.indexOf('m')]-(1-Math.exp(-row[0])))<1e-10);
const bad=C.example();bad.edges.find(e=>e.to==='controller').from='controller';assert.throws(()=>C.simulate(bad),/Algebraic loop/);
assert.throws(()=>C.simulate(C.example(),{dt:0}));
const missing=C.example();missing.edges.pop();assert.throws(()=>C.simulate(missing),/unconnected/);
assert.deepEqual(C.simulate(JSON.parse(JSON.stringify(C.example()))),C.simulate(C.example()));
console.log('7 numerical, validation and serialization checks passed');
