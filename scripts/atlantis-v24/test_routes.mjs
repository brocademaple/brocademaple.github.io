import fs from 'node:fs';import assert from 'node:assert/strict';import {WalkWorld} from '../web/navigation.mjs';import {Vector3} from '../web/vendor/three.module.js';
const root=new URL('../',import.meta.url),world=new WalkWorld(JSON.parse(fs.readFileSync(new URL('output/navigation.json',root)))),results=[];
for(const [name,xyz,endY,steps] of [['upper_right',[-8.8,8.275,-19.2],11.41,310],['upper_left',[-15.2,8.275,-19.2],11.41,310],['lower_right',[-6.2,8.295,-19.6],2.425,235],['lower_left',[-18,8.295,-19.6],2.425,235],['garden_archive',[-12,4.75,2],6.625,380]]){
 const p=world.project(new Vector3(...xyz),1),start=p.clone();let distance=0;for(let i=0;i<steps;i++)distance+=world.move(p,0,-.04);const end=p.clone();let back=0;for(let i=0;i<steps;i++)back+=world.move(p,0,.04);const good=Math.abs(end.y-endY)<.08&&p.distanceTo(start)<.25;results.push({name,passed:good,start:start.toArray(),end:end.toArray(),returned:p.toArray(),outDistance:distance,backDistance:back});
}
console.log(JSON.stringify(results,null,2));fs.writeFileSync(new URL('route-test.json',root),JSON.stringify(results,null,2));assert(results.every(x=>x.passed),'round-trip routes must pass');
