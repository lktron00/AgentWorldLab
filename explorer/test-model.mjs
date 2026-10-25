import test from 'node:test';
import assert from 'node:assert/strict';
import {routeFromURL,graphLayout,decisionAt,decisionsAt,routesThrough,colorForBelief} from './model.mjs';

const cases=[{id:'security-modified',pairs:[{seed:7},{seed:16}]},{id:'cloud-index',pairs:[{seed:2}]}];
test('shared links cannot select another case seed or a privileged condition',()=>{
 const r=routeFromURL('?case=cloud-index&seed=7&condition=operator&turn=900&agent=-1&view=world',cases);
 assert.deepEqual(r,{caseId:'cloud-index',seed:2,branch:'diagnostic',turn:9,actor:1,view:'network'});
 assert.equal(routeFromURL('?turn=NaN&agent=0',cases).turn,9);
 assert.equal(routeFromURL('?turn=0&agent=0',cases).actor,0);
});
test('graph layout is deterministic, finite and fills the visual area without implying geography',()=>{
 const nodes=Array.from({length:21},(_,id)=>({id}));const edges=nodes.flatMap(n=>[{source:n.id,target:(n.id+1)%21},{source:n.id,target:(n.id+4)%21}]);
 const a=graphLayout(nodes,edges),b=graphLayout(nodes,edges);assert.deepEqual(a,b);
 assert.equal(a.length,21);for(const n of a){assert.ok(Number.isFinite(n.x)&&Number.isFinite(n.y));assert.ok(n.x>=89&&n.x<=871&&n.y>=54&&n.y<=466);}
 assert.ok(Math.max(...a.map(n=>n.x))-Math.min(...a.map(n=>n.x))>=779);
});
const world={branches:{generic:{decisions:[{step:0,actor:1,reason:'first'},{step:1,actor:1,reason:'later'},{step:0,actor:2,reason:'another'}],events:[{step:0,source:1,target:2},{step:2,source:2,target:3}]},diagnostic:{decisions:[],events:[]}}};
test('turn selection returns the saved observation of that turn, not a future decision',()=>{
 assert.equal(decisionAt(world,'generic',0,1).reason,'first');assert.equal(decisionAt(world,'generic',1,1).reason,'later');assert.equal(decisionAt(world,'generic',0,0),null);
 assert.equal(decisionsAt(world,'generic',0).length,2);assert.equal(decisionsAt(world,'diagnostic',0).length,0);
});
test('message maps never include a later turn or borrow routes from the other branch',()=>{
 assert.deepEqual(routesThrough(world,'generic',0),[{step:0,source:1,target:2}]);assert.equal(routesThrough(world,'generic',2).length,2);assert.deepEqual(routesThrough(world,'diagnostic',9),[]);
});
test('probability colors clamp to the declared scale',()=>{assert.equal(colorForBelief(-5),colorForBelief(0));assert.equal(colorForBelief(120),colorForBelief(100));assert.notEqual(colorForBelief(0),colorForBelief(100));});
