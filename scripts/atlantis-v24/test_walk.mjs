import fs from 'node:fs';import assert from 'node:assert/strict';
import {WalkWorld,qualityProfile} from '../web/navigation.mjs';import {Vector3} from '../web/vendor/three.module.js';
const data=JSON.parse(fs.readFileSync(new URL('../output/navigation.json',import.meta.url)));const world=new WalkWorld(data),results=[];
for(const id of ['loop','glass','archive','upper','lower','material']){
 const view=data.spawns[id];const eye=new Vector3(...view.position),target=new Vector3(...view.target);const feet=world.project(eye);assert(feet,`${id} spawn`);
 const dx=target.x-eye.x,dz=target.z-eye.z,n=Math.hypot(dx,dz);let distance=0;const start=feet.clone();
 for(let i=0;i<180;i++)distance+=world.move(feet,dx/n*2.6/60,dz/n*2.6/60);
 results.push({id,start:start.toArray(),end:feet.toArray(),distance:+distance.toFixed(3)});
}
// Deterministic regressions: sustained hall traversal, side-wall stopping, sliding, no void crossing.
const hall=world.project(new Vector3(-31,8.275,13));let dist=0;for(let i=0;i<600;i++)dist+=world.move(hall,0,-2.6/60);assert(dist>24,'walk 26m along hall');
const wall=hall.clone();for(let i=0;i<600;i++)world.move(wall,.05,0);assert(wall.x<-26.7,'stop before glass wall');
const slide=wall.clone();let slid=0;for(let i=0;i<100;i++)slid+=world.move(slide,.03,.03);assert(slid>2,'slide along wall');
const loop=world.project(new Vector3(-16.5,5.06,10.3));for(let i=0;i<900;i++)world.move(loop,-.05,.02);assert(world.supported(loop.x,loop.z,loop.y),'stay on deck');
for(const dpr of [1,1.25,2,3]){const h=qualityProfile('high',dpr),l=qualityProfile('balanced',dpr);assert(h.pixelRatio>l.pixelRatio);assert(h.shadowSize===4*l.shadowSize);assert(h.waterMotion&&!l.waterMotion)}
const out={passed:true,spawns:results,hallDistance:dist,wallStop:wall.toArray(),slideDistance:slid,edgeStop:loop.toArray(),qualityDPRs:[1,1.25,2,3]};console.log(JSON.stringify(out,null,2));fs.writeFileSync(new URL('../walk-test.json',import.meta.url),JSON.stringify(out,null,2));
