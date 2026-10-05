import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {MeshoptDecoder} from './vendor/meshopt_decoder.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {WalkWorld,qualityProfile} from './navigation.mjs';
const $=id=>document.getElementById(id),reduced=matchMedia('(prefers-reduced-motion:reduce)').matches;
const state={ready:false,errors:[],views:{},artworks:0,frames:[],quality:'high',mode:'orbit'};window.galleryReview=state;addEventListener('error',e=>state.errors.push(e.message));addEventListener('unhandledrejection',e=>state.errors.push(String(e.reason)));
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
renderer.debug.onShaderError=(gl,program,vs,fs)=>{state.errors.push(gl.getShaderInfoLog(vs)||gl.getShaderInfoLog(fs)||'shader link error')};renderer.setPixelRatio(Math.min(devicePixelRatio,1.65));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=1.23;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;document.body.prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#087b9c');scene.fog=new THREE.FogExp2('#40737c',.003);
const camera=new THREE.PerspectiveCamera(46,innerWidth/innerHeight,.08,400);camera.position.set(-63,36,72);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=!reduced;controls.dampingFactor=.065;controls.minDistance=.25;controls.maxDistance=160;controls.maxPolarAngle=Math.PI*.51;controls.target.set(-1,5,-6);controls.update();
// A marine sky environment feeds the same roughness, normals and metallic maps exported from Blender.
const env=new THREE.Scene();const sky=new THREE.Mesh(new THREE.SphereGeometry(150,32,16),new THREE.ShaderMaterial({side:THREE.BackSide,vertexShader:'varying vec3 p;void main(){p=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec3 p;void main(){float y=normalize(p).y;vec3 c=mix(vec3(.025,.11,.14),vec3(.35,.61,.66),smoothstep(-.4,.9,y));float sun=pow(max(dot(normalize(p),normalize(vec3(-.3,.9,.2))),0.),110.);gl_FragColor=vec4(c+sun*vec3(2.,1.9,1.5),1.);}' }));env.add(sky);const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(env,.04).texture;pmrem.dispose();sky.geometry.dispose();sky.material.dispose();
scene.add(new THREE.HemisphereLight('#c4dce0','#607873',1.55));
const sun=new THREE.DirectionalLight('#ffe9c6',2.75);sun.position.set(-26,55,20);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-66,right:66,top:62,bottom:-62,near:1,far:160});sun.shadow.normalBias=.06;sun.shadow.bias=-.00015;scene.add(sun);
const fill=new THREE.DirectionalLight('#73b9c9',.65);fill.position.set(30,20,-35);scene.add(fill);
const roomLamp=new THREE.PointLight('#ffce8d',280,25,2);scene.add(roomLamp);
const ray=new THREE.Raycaster(),pointer=new THREE.Vector2(),artMeshes=[],collisionMeshes=[],nav={},targets={};let artworks=[],currentArt=0,transition=null,lastTime=0,walking=false,yaw=0,pitch=0,drag=null;
let walkWorld=null,feet=null; const causticTime={value:0},causticStrength={value:.24};const materials=new Set();
function waterLight(material){
 if(!material.isMeshStandardMaterial||material.transmission>.1||material.emissiveIntensity>.4)return;
 material.onBeforeCompile=shader=>{shader.uniforms.uWaterTime=causticTime;shader.uniforms.uWaterStrength=causticStrength;shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vWaterWorld;').replace('#include <begin_vertex>','#include <begin_vertex>\nvWaterWorld=(modelMatrix*vec4(position,1.)).xyz;');shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nuniform float uWaterTime;uniform float uWaterStrength;varying vec3 vWaterWorld;').replace('#include <opaque_fragment>',`vec2 cp=vWaterWorld.xz*.65;float cw=sin(cp.x+sin(cp.y*1.3+uWaterTime*.22))+sin(cp.y+sin(cp.x*.9-uWaterTime*.18));float ca=pow(clamp(1.-abs(cw)*2.,0.,1.),5.);float top=max(0.,normal.y);outgoingLight+=diffuseColor.rgb*ca*uWaterStrength*(.4+top);\n#include <opaque_fragment>`);};material.customProgramCacheKey=()=> 'atlantis-water-24';
}
function setView(id,instant=false){id=nav[id]?id:'hero';camera.fov=['hero','plan'].includes(id)?36:55;camera.updateProjectionMatrix();const v=nav[id],t=targets[id];if(!v||!t)return;walking=false;keys.clear();feet=null;mobilePad.style.display='none';controls.enabled=true;$('walk').setAttribute('aria-pressed','false');state.mode='orbit';$('walk').textContent='步行';$('hint').textContent='W A S D 开始步行 · 拖动环顾 · 点击画作查看';state.currentView=id;delete state.walkBlocked;
 const pos=v.getWorldPosition(new THREE.Vector3()),target=t.getWorldPosition(new THREE.Vector3());
 if(instant||reduced){transition=null;camera.position.copy(pos);controls.target.copy(target);controls.update();}else transition={from:camera.position.clone(),to:pos,fromTarget:controls.target.clone(),target,start:performance.now()};
 $('place').textContent=v.userData.gallery_nav_label;document.querySelectorAll('#nav button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.id===id?'true':'false'));roomLamp.position.copy(target).add(new THREE.Vector3(0,2,0));roomLamp.intensity=['hero','plan','loop'].includes(id)?0:280;}
function showArt(i){currentArt=(i+artworks.length)%artworks.length;const a=artworks[currentArt];$('artIndex').textContent=`${currentArt+1} / ${artworks.length}`;$('artImage').src='.'+a.src;$('artImage').alt=(a.titleZh||a.title);$('artTheme').textContent=({color:'色彩',lighting:'光影',composition:'重构',material:'材质',mood:'情绪',scene:'物件'})[a.room];$('artTitle').textContent=(a.titleZh||a.title);$('artDesc').textContent=a.translation;$('artPrompt').textContent=a.prompt;$('artFull').href='.'+a.src;if(!$('art').open)$('art').showModal();}
$('closeArt').onclick=()=>$('art').close();$('previous').onclick=()=>showArt(currentArt-1);$('next').onclick=()=>showArt(currentArt+1);$('closeCatalog').onclick=()=>$('collection').close();$('catalog').onclick=()=>$('collection').showModal();
function applyQuality(mode){
 const profile=qualityProfile(mode,devicePixelRatio);state.quality=mode;state.qualitySettings=profile;
 renderer.setPixelRatio(profile.pixelRatio);renderer.setSize(innerWidth,innerHeight);causticStrength.value=profile.waterStrength;
 sun.shadow.mapSize.set(profile.shadowSize,profile.shadowSize);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}renderer.shadowMap.needsUpdate=true;
 for(const m of materials)for(const k of ['map','normalMap','roughnessMap','metalnessMap','aoMap'])if(m[k])m[k].anisotropy=Math.min(profile.anisotropy,renderer.capabilities.getMaxAnisotropy());
 const high=mode==='high';$('quality').textContent=high?'高清':'流畅';$('quality').setAttribute('aria-pressed',String(high));
 $('qualityNote').textContent=high?'高清 · 精细阴影 / 动态水光':'流畅 · 轻量阴影 / 静态水光';
 $('quality').title=high?'切换到流畅：较低渲染负载，保留全部模型和材质':'切换到高清：更清晰的边缘、阴影与动态水光';
 state.drawingBuffer=[renderer.domElement.width,renderer.domElement.height];state.frames.length=0;
}
$('quality').onclick=()=>applyQuality(state.quality==='high'?'balanced':'high');
function fail(err){state.errors.push(String(err));$('loading').classList.add('hidden');$('fallback').style.display='block';$('hint').textContent='三维加载未完成，可选择 Blender 渲染查看画廊';console.error(err);}
async function start(){
 const asset=await fetch('./build-version.json',{cache:'no-store'}).then(r=>r.json());state.assetVersion=asset.model;
 walkWorld=new WalkWorld(await fetch('./navigation.json?v='+asset.navigation).then(r=>{if(!r.ok)throw new Error('步行地面加载失败');return r.json()}));
 artworks=await fetch('./artworks.json').then(r=>{if(!r.ok)throw new Error('作品目录不可用');return r.json()});state.artworks=artworks.length;$('count').textContent=artworks.length;
 for(const [i,a] of artworks.entries()){const button=document.createElement('button'),im=document.createElement('img'),text=document.createElement('span');im.src='.'+a.thumb;im.loading='lazy';im.alt=(a.titleZh||a.title);text.textContent=(a.titleZh||a.title);button.append(im,text);button.onclick=()=>{$('collection').close();showArt(i)};$('catalogGrid').append(button);}
 const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync('./atlantis-web.glb?v='+asset.model,e=>{if(e.total){$('bar').max=e.total;$('bar').value=e.loaded;$('progress').textContent=`海底长廊正在浮出 · ${Math.round(e.loaded/e.total*100)}%`;}});
 scene.add(gltf.scene);gltf.scene.updateMatrixWorld(true);
 const seen=new Set();gltf.scene.traverse(o=>{if(o.userData.gallery_nav_id){nav[o.userData.gallery_nav_id]=o;state.views[o.userData.gallery_nav_id]=o.userData.gallery_nav_label;}if(o.userData.gallery_nav_target_for)targets[o.userData.gallery_nav_target_for]=o;
 if(o.isMesh){o.castShadow=!(Array.isArray(o.material)?o.material:[o.material]).some(m=>m.transparent||m.transmission>.1);o.receiveShadow=true;if(o.userData.gallery_interactive)artMeshes.push(o);else collisionMeshes.push(o);for(const m of Array.isArray(o.material)?o.material:[o.material]){if(seen.has(m))continue;seen.add(m);materials.add(m);for(const k of ['map','normalMap','roughnessMap','metalnessMap'])if(m[k])m[k].anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());m.envMapIntensity=.8;if(m.transmission>.1){m.transmission=0;m.opacity=.72;m.transparent=true;m.depthWrite=false;m.roughness=.13;m.ior=1.33;m.side=THREE.DoubleSide;m.forceSinglePass=true;o.castShadow=false;}else waterLight(m);}}});
 for(const label of ['RECOMPOSITION','MATERIAL','MOOD_OBJECT']){const works=artMeshes.filter(o=>o.name.includes(label));if(works.length){const p=new THREE.Vector3();for(const o of works)p.add(new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()));p.divideScalar(works.length);p.y+=1.6;const lamp=new THREE.PointLight('#ffd19a',145,18,2);lamp.position.copy(p);scene.add(lamp)}}
 for(const id of ['hero','plan','loop','glass','archive','upper','lower','material']){if(!nav[id])continue;const button=document.createElement('button');button.textContent=nav[id].userData.gallery_nav_label;button.dataset.id=id;button.setAttribute('aria-pressed','false');button.onclick=()=>setView(id);$('nav').append(button);}
 setView(new URLSearchParams(location.search).get('view')||'hero',true);applyQuality(new URLSearchParams(location.search).get('quality')==='balanced'?'balanced':'high');state.ready=true;state.modelArtworks=artMeshes.length;state.materials=seen.size;$('loading').classList.add('hidden');$('loading').setAttribute('aria-hidden','true');renderer.shadowMap.needsUpdate=true;renderer.render(scene,camera);renderer.shadowMap.autoUpdate=false;
 // Debug hooks are read-only evidence; visual state is operated through the page controls.
 state.assetGeometry='same evaluated master mesh; no decimation';
}
start().catch(fail);
renderer.domElement.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,lastX:e.clientX,lastY:e.clientY};});
renderer.domElement.addEventListener('pointermove',e=>{if(walking&&drag){yaw-=(e.clientX-drag.lastX)*.003;pitch=THREE.MathUtils.clamp(pitch-(e.clientY-drag.lastY)*.003,-1.25,1.25);drag.lastX=e.clientX;drag.lastY=e.clientY;}});
renderer.domElement.addEventListener('pointerup',e=>{if(!drag)return;const moved=Math.hypot(e.clientX-drag.x,e.clientY-drag.y);drag=null;if(moved>6||!state.ready)return;pointer.set(e.clientX/innerWidth*2-1,1-e.clientY/innerHeight*2);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(artMeshes,false)[0];if(hit){const i=artworks.findIndex(a=>a.thumb===hit.object.userData.gallery_artwork_thumb);if(i>=0)showArt(i);}});
const keys=new Set(),tapStarted=new Map();
const movementCodes=['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'];
addEventListener('keydown',e=>{
 if(e.code==='Escape'&&walking&&!$('art').open&&!$('collection').open){leaveWalk();return}
 if(movementCodes.includes(e.code)&&state.ready&&!walking&&!$('art').open&&!$('collection').open&&!e.metaKey&&!e.ctrlKey)$('walk').click();
 if(!walking||$('art').open||$('collection').open||e.metaKey||e.ctrlKey)return;
 if(movementCodes.includes(e.code)){const first=!keys.has(e.code);keys.add(e.code);if(first){tapStarted.set(e.code,performance.now());stepWalk(1/60)}state.lastInput=e.code;e.preventDefault()}
});
addEventListener('keyup',e=>{keys.delete(e.code);tapStarted.delete(e.code)});
function clearInput(){keys.clear();tapStarted.clear();drag=null}
addEventListener('blur',clearInput);document.addEventListener('visibilitychange',()=>{if(document.hidden)clearInput()});
for(const id of ['art','collection'])$(id).addEventListener('close',clearInput);
function leaveWalk(){
 walking=false;clearInput();controls.enabled=true;const d=new THREE.Vector3();camera.getWorldDirection(d);controls.target.copy(camera.position).addScaledVector(d,4);controls.update();
 state.mode='orbit';$('walk').setAttribute('aria-pressed','false');$('walk').textContent='步行';mobilePad.style.display='none';$('hint').textContent='W A S D 开始步行 · 拖动环顾 · 点击画作查看';
}
$('walk').onclick=()=>{
 if(!state.ready)return;if(walking){leaveWalk();return}
 if(['hero','plan'].includes(state.currentView))setView('loop',true);
 // Finish any view transition before querying the floor, so entry never uses a camera in mid-air.
 if(transition){camera.position.copy(transition.to);controls.target.copy(transition.target);transition=null;controls.update()}
 feet=walkWorld.project(camera.position);
 if(!feet){$('hint').textContent='当前位置没有通路，请选择一个展厅或花园入口';return}
 camera.position.copy(feet).add(new THREE.Vector3(0,walkWorld.eyeHeight,0));
 const d=new THREE.Vector3();camera.getWorldDirection(d);yaw=Math.atan2(-d.x,-d.z);pitch=THREE.MathUtils.clamp(Math.asin(d.y),-.65,.65);
 walking=true;controls.enabled=false;clearInput();state.mode='walk';state.walkDistance=0;delete state.walkBlocked;
 $('walk').setAttribute('aria-pressed','true');$('walk').textContent='退出步行';
 $('hint').textContent='W A S D / 方向键行走 · 拖动环顾 · Esc 退出';mobilePad.style.display='flex';
 renderer.domElement.focus({preventScroll:true});
};
function stepWalk(dt){
 camera.rotation.set(pitch,yaw,0,'YXZ');
 const f=+(keys.has('KeyW')||keys.has('ArrowUp'))-+(keys.has('KeyS')||keys.has('ArrowDown')),
 s=+(keys.has('KeyD')||keys.has('ArrowRight'))-+(keys.has('KeyA')||keys.has('ArrowLeft'));
 if(f||s){const n=Math.hypot(f,s),distance=Math.min(dt,.1)*2.6;
 const moved=walkWorld.move(feet,(-Math.sin(yaw)*f+Math.cos(yaw)*s)/n*distance,(-Math.cos(yaw)*f-Math.sin(yaw)*s)/n*distance);
 state.walkDistance+=moved;state.walkBlocked=moved<.0001?'墙面或通路边缘':undefined;
 }
 camera.position.x=feet.x;camera.position.z=feet.z;camera.position.y=THREE.MathUtils.lerp(camera.position.y,feet.y+walkWorld.eyeHeight,1-Math.exp(-14*Math.min(dt,.1)));
}
renderer.setAnimationLoop(time=>{const dt=(time-lastTime)/1000;lastTime=time;if(!reduced&&state.quality==='high')causticTime.value=time/1000;if(transition){let t=Math.min(1,(performance.now()-transition.start)/1400);t=t*t*(3-2*t);camera.position.lerpVectors(transition.from,transition.to,t);controls.target.lerpVectors(transition.fromTarget,transition.target,t);if(t>=1)transition=null;}if(walking){if(!$('art').open&&!$('collection').open)stepWalk(dt);else clearInput()}else controls.update();renderer.render(scene,camera);if(state.ready){state.drawCalls=renderer.info.render.calls;state.triangles=renderer.info.render.triangles;if(dt>0&&dt<1){state.frames.push(dt);if(state.frames.length>120)state.frames.shift();state.fps=Math.round(state.frames.length/state.frames.reduce((a,b)=>a+b,0));}}});
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);state.drawingBuffer=[renderer.domElement.width,renderer.domElement.height]});
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();state.ready=false;$('fallback').style.display='block';$('hint').textContent='显示 Blender 渲染图；重新载入可恢复三维浏览';});

// Directional water backdrop stays behind architecture; it does not obscure the art.
const waterBackdrop=new THREE.Mesh(new THREE.SphereGeometry(190,48,24),new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,vertexShader:'varying vec3 wp;void main(){wp=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:`varying vec3 wp;void main(){vec3 d=normalize(wp);float h=smoothstep(-.25,.75,d.y);vec3 c=mix(vec3(.014,.15,.22),vec3(.05,.48,.62),h);float a=atan(d.x,d.z);float shafts=pow(max(0.,sin(a*31.+d.y*3.)*.5+.5),18.)*.065*smoothstep(-.22,.7,d.y);c+=vec3(.50,.85,.90)*shafts;gl_FragColor=vec4(c,1.);
#include <tonemapping_fragment>
#include <colorspace_fragment>}`.replace(';#include',';\n#include')}));waterBackdrop.renderOrder=-2;scene.add(waterBackdrop);
if(new URLSearchParams(location.search).has('audit')){const stats=document.createElement('output');stats.id='auditStats';stats.style.cssText='position:fixed;right:20px;top:130px;background:#032435e8;padding:12px;z-index:4;font:11px monospace;white-space:pre';document.body.append(stats);setInterval(()=>{stats.textContent=JSON.stringify({ready:state.ready,errors:state.errors,artworks:state.modelArtworks,views:Object.keys(state.views).length,drawCalls:state.drawCalls,triangles:state.triangles,fps:state.fps,view:state.currentView,mode:state.mode,camera:camera.position.toArray().map(v=>Math.round(v*100)/100),walkBlocked:state.walkBlocked,distance:Math.round((state.walkDistance||0)*100)/100,quality:state.qualitySettings,buffer:state.drawingBuffer},null,2)},1500)}
const mobilePad=document.createElement('div');mobilePad.id='mobilePad';mobilePad.setAttribute('aria-label','步行方向');
for(const [label,code] of [['←','KeyA'],['↑','KeyW'],['↓','KeyS'],['→','KeyD']]){
 const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-label',({'KeyA':'向左移动','KeyW':'向前行走','KeyS':'向后行走','KeyD':'向右移动'})[code]);
 b.onpointerdown=e=>{e.preventDefault();b.focus({preventScroll:true});keys.add(code);stepWalk(1/60);b.setPointerCapture(e.pointerId)};
 b.onpointerup=b.onpointercancel=b.onlostpointercapture=()=>keys.delete(code);
 // Keyboard activation of on-screen arrows makes a useful discrete step too.
 b.onclick=e=>{if(e.detail===0&&walking){keys.add(code);stepWalk(.1);keys.delete(code)}};mobilePad.append(b)
}document.body.append(mobilePad);
renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label','三维海底画廊');
renderer.domElement.addEventListener('pointercancel',()=>drag=null);
renderer.domElement.addEventListener('lostpointercapture',()=>drag=null);
renderer.domElement.addEventListener('pointerdown',e=>{if(walking)renderer.domElement.setPointerCapture(e.pointerId)});
