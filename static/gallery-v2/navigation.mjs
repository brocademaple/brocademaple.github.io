import {Vector3,Triangle} from './vendor/three.module.js';
// Collision uses source-authored walk surfaces, independently of render materials and quality.
export class WalkWorld {
 constructor(data){
  this.eyeHeight=data.eyeHeight;this.radius=data.radius;this.maxStep=.34;this.spawns=data.spawns;
  this.cell=2;this.floorGrid=new Map();this.wallGrid=new Map();this.tmp=new Vector3();this.point=new Vector3();
  for(const [source,grid] of [[data.floors,this.floorGrid],[data.obstacles,this.wallGrid]])for(const a of source){
   const t=new Triangle(new Vector3(...a.slice(0,3)),new Vector3(...a.slice(3,6)),new Vector3(...a.slice(6,9)));
   t.minY=Math.min(t.a.y,t.b.y,t.c.y);t.maxY=Math.max(t.a.y,t.b.y,t.c.y);
   const minX=Math.floor((Math.min(t.a.x,t.b.x,t.c.x)-this.radius)/this.cell),maxX=Math.floor((Math.max(t.a.x,t.b.x,t.c.x)+this.radius)/this.cell),minZ=Math.floor((Math.min(t.a.z,t.b.z,t.c.z)-this.radius)/this.cell),maxZ=Math.floor((Math.max(t.a.z,t.b.z,t.c.z)+this.radius)/this.cell);
   for(let x=minX;x<=maxX;x++)for(let z=minZ;z<=maxZ;z++){const k=x+','+z;if(!grid.has(k))grid.set(k,[]);grid.get(k).push(t)}
  }
 }
 nearby(grid,x,z){return grid.get(Math.floor(x/this.cell)+','+Math.floor(z/this.cell))||[]}
 heights(x,z){
  const hits=[];for(const t of this.nearby(this.floorGrid,x,z)){
   const {a,b,c}=t,den=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z);if(Math.abs(den)<1e-9)continue;
   const u=((b.z-c.z)*(x-c.x)+(c.x-b.x)*(z-c.z))/den,v=((c.z-a.z)*(x-c.x)+(a.x-c.x)*(z-c.z))/den;
   if(u>=-1e-5&&v>=-1e-5&&u+v<=1.00001)hits.push(u*a.y+v*b.y+(1-u-v)*c.y)
  }return hits;
 }
 floor(x,z,y,up=this.maxStep,drop=.42){
  return this.heights(x,z).filter(h=>h<=y+up+1e-4&&h>=y-drop-1e-4).sort((a,b)=>b-a)[0];
 }
 blocked(x,y,z){
  for(const t of this.nearby(this.wallGrid,x,z)){
   if(t.maxY<y+.13||t.minY>y+1.78)continue;
   for(const h of [.38,.88,1.40,1.58]){
    this.point.set(x,y+h,z);t.closestPointToPoint(this.point,this.tmp);
    if(this.tmp.distanceToSquared(this.point)<this.radius*this.radius)return true;
   }
  }return false;
 }
 supported(x,z,y){
  // Check the footprint, so walking never leaves the deck or falls into the light well.
  for(const [dx,dz] of [[0,0],[.17,0],[-.17,0],[0,.17],[0,-.17]])if(this.floor(x+dx,z+dz,y,.35,.44)===undefined)return false;
  return !this.blocked(x,y,z);
 }
 project(eye,radius=6){
  const expected=eye.y-this.eyeHeight;
  for(let r=0;r<=radius;r+=.2)for(let a=0;a<(r?24:1);a++){
   const x=eye.x+r*Math.cos(a*Math.PI/12),z=eye.z+r*Math.sin(a*Math.PI/12);
   const h=this.floor(x,z,expected,.6,2.2);
   if(h!==undefined&&this.supported(x,z,h))return new Vector3(x,h,z);
  }return null;
 }
 move(feet,dx,dz){
  const parts=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.075));let moved=0;
  for(let i=0;i<parts;i++){
   const ox=feet.x,oz=feet.z;
   // Full movement first; then slide along walls rather than freezing diagonally.
   const variants=[[dx/parts,dz/parts],[dx/parts,0],[0,dz/parts]];
   for(const [sx,sz] of variants){
    if(!sx&&!sz)continue;
    const x=feet.x+sx,z=feet.z+sz,h=this.floor(x,z,feet.y);
    if(h!==undefined&&this.supported(x,z,h)){feet.set(x,h,z);break}
   }
   moved+=Math.hypot(feet.x-ox,feet.z-oz);
  }return moved;
 }
}
export function qualityProfile(mode,dpr=1){
 const high=mode==='high';return {mode,pixelRatio:high?Math.min(1.75,Math.max(1.5,dpr)):Math.min(1,dpr),shadowSize:high?4096:1024,anisotropy:high?16:2,waterMotion:high,waterStrength:high?.24:.09};
}
