import test from 'node:test';
import assert from 'node:assert/strict';

// Small DOM double exercises event wiring without claiming visual/browser coverage.
const nodes=new Map();
function node(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,disabled:false,hidden:false,listeners:{},classList:{add(){},remove(){}},replaceChildren(){},addEventListener(type,fn){this.listeners[type]=fn;}});return nodes.get(id);}
const reviews=['identity','proportions','anatomy','garment','scene'].map(k=>({value:'pass',dataset:{review:k}}));
globalThis.document={getElementById:node,querySelectorAll:s=>s==='[data-review]'?reviews:[]};
globalThis.window={addEventListener(){}};
await import('./app.mjs');
for(const id of ['pose','garmentMode','outfit','scene'])test(`${id} changes invalidate previous review`,()=>{reviews.forEach(x=>x.value='pass');node(id).listeners.input();assert.ok(reviews.every(x=>x.value==='uncertain'));});
for(const id of ['subjectFile','resultFile','garmentFile'])test(`${id} changes invalidate previous review`,async()=>{reviews.forEach(x=>x.value='pass');await node(id).listeners.change({target:{files:[]}});assert.ok(reviews.every(x=>x.value==='uncertain'));});
test('consent changes invalidate previous review',()=>{reviews.forEach(x=>x.value='pass');node('consents').listeners.change();assert.ok(reviews.every(x=>x.value==='uncertain'));});
