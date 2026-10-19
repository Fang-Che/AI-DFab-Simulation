// Standard DH; degrees in the ABB convention, metres in the renderer.
function abbFK(degrees){
 let t=new T.Matrix4(),out=[t.clone()];const sign=[1,-1,-1,1,-1,1];
 for(let i=0;i<6;i++){
  const q=degrees[i]*Math.PI/180*sign[i]+(i===1?Math.PI/2:0),a=DATA.robot.a[i]/1000,d=DATA.robot.d[i]/1000,al=DATA.robot.alpha[i];
  const c=Math.cos(q),s=Math.sin(q),ca=Math.cos(al),sa=Math.sin(al);
  t.multiply(new T.Matrix4().set(c,-s*ca,s*sa,a*c,s,c*ca,-c*sa,a*s,0,sa,ca,d,0,0,0,1));out.push(t.clone());
 }return out;
}
function abbIK(target,previous){
 const e=target.elements, w=V([e[12]-.2*e[8],e[13]-.2*e[9],e[14]-.2*e[10]]),L=Math.hypot(.225,1.52),phi=Math.atan2(1.52,.225),candidates=[];
 const clamp=x=>Math.max(-1,Math.min(1,x));
 for(const flip of [false,true]){
  const yaw=Math.atan2(w.y,w.x)+(flip?Math.PI:0),r=Math.hypot(w.x,w.y)*(flip?-1:1)-.24,z=w.z-.8,co=(r*r+z*z-1.05**2-L*L)/(2*1.05*L);
  if(Math.abs(co)>1+1e-8)continue;
  for(const sign of [-1,1]){
   const elbow=sign*Math.acos(clamp(co)),t2=Math.atan2(z,r)-Math.atan2(L*Math.sin(elbow),1.05+L*Math.cos(elbow));
   const first=[yaw,Math.PI/2-t2,-elbow-phi].map(x=>x*180/Math.PI);
   const R=abbFK([...first,0,0,0])[3].invert().multiply(target).elements,beta=Math.acos(clamp(R[10]));
   for(const ws of [1,-1]){
    let b=beta*ws,a,c;if(Math.abs(Math.sin(b))<1e-7){a=previous[3]*Math.PI/180;c=Math.atan2(R[1],R[0])-a}
    else{a=Math.atan2(R[9]/Math.sin(b),R[8]/Math.sin(b));c=Math.atan2(R[6]/Math.sin(b),-R[2]/Math.sin(b))}
    const q=[...first,...[a,-b,c].map(x=>x*180/Math.PI)];let valid=true;
    for(let i=0;i<6;i++){
     const choices=[];for(let k=-2;k<=2;k++){let v=q[i]+360*k;if(v>=DATA.robot.joint_limits_deg[i][0]-1e-6&&v<=DATA.robot.joint_limits_deg[i][1]+1e-6)choices.push(v)}
     if(!choices.length){valid=false;break}q[i]=choices.sort((a,b)=>Math.abs(a-previous[i])-Math.abs(b-previous[i]))[0];
    }
    if(valid){const f=abbFK(q)[6].elements;if(Math.max(...f.map((v,i)=>Math.abs(v-e[i])))<1e-5)candidates.push(q)}
   }
  }
 }
 return candidates.sort((a,b)=>a.reduce((s,x,i)=>s+(x-previous[i])**2,0)-b.reduce((s,x,i)=>s+(x-previous[i])**2,0))[0]||null;
}
let abbMeshes=[],abbHomeInverse=[],abbAngles=[0,25,25,0,45,0],toolGroup,trajectory,obstacles=[],collisionBoxes=[];
const toolOffset=.22,toolFlip=new T.Quaternion().setFromAxisAngle(V([1,0,0]),Math.PI);
function createABB(){
 const home=abbFK([0,0,0,0,0,0]);abbHomeInverse=home.map(m=>m.clone().invert());
 DATA.robot.links.forEach((link,i)=>{const m=meshData(link.v,link.f,i===0?'#4c6368':'#65a2a4');m.matrixAutoUpdate=false;scene.add(m);abbMeshes.push(m)});
 toolGroup=new T.Group();const body=new T.Mesh(new T.BoxGeometry(.38,.26,.07),material('#465762'));toolGroup.add(body);
 const stem=new T.Mesh(new T.CylinderGeometry(.045,.06,.19,16),material('#637c84'));stem.rotation.x=Math.PI/2;stem.position.z=.12;toolGroup.add(stem);
 for(const x of [-.13,.13])for(const y of [-.075,.075]){const cup=new T.Mesh(new T.CylinderGeometry(.04,.05,.035,16),material('#203d41'));cup.rotation.x=Math.PI/2;cup.position.set(x,y,-.045);toolGroup.add(cup)}scene.add(toolGroup);
 trajectory=line([V([0,0,0]),V([0,0,0])],'#208dbc');
}
function moveABB(tcp,q){
 const normal=V([0,0,1]).applyQuaternion(q),flangeQ=q.clone().multiply(toolFlip),flangeP=tcp.clone().addScaledVector(normal,toolOffset);
 const target=new T.Matrix4().compose(flangeP,flangeQ,V([1,1,1])),solved=abbIK(target,abbAngles);
 const jump=solved&&Math.max(...solved.map((x,i)=>Math.abs(x-abbAngles[i])))>60;
 if(solved)abbAngles=solved;
 const frames=abbFK(abbAngles);abbMeshes.forEach((m,i)=>m.matrix.copy(frames[i]).multiply(abbHomeInverse[i]));
 const fp=V([0,0,0]).setFromMatrixPosition(frames[6]),fq=new T.Quaternion().setFromRotationMatrix(frames[6]);
 const actualQ=fq.clone().multiply(toolFlip),actualTCP=fp.addScaledVector(V([0,0,1]).applyQuaternion(fq),toolOffset);
 toolGroup.position.copy(actualTCP);toolGroup.quaternion.copy(actualQ);scene.updateMatrixWorld(true);
 return {valid:!!solved,jump,actualTCP,actualQ,error:actualTCP.distanceTo(tcp)*1000};
}
function factoryPose(p,t,index){
 const dest=mm(p.target),normal=V(p.normal),stack=p.stack.clone(),high=1.55,hover=dest.clone().setZ(high),lift=stack.clone().setZ(high);
 const contact=pos=>pos.clone().addScaledVector(normal,.055);
 const previous=index?DATA.parts[index-1]:null;
 const previousTCP=previous?mm(previous.target).addScaledVector(V(previous.normal),.055).setZ(high+previous.normal[2]*.055):V([1,0,2.1]);
 const previousQ=previous?previous.q:new T.Quaternion();
 let pos=stack.clone(),q=p.pickQ.clone(),tcp,toolQ=q.clone(),stage,held=false;
 if(t<.06){tcp=previousTCP;toolQ.copy(previousQ).slerp(p.pickQ,t/.06);stage='高處退離／調整夾具'}
 else if(t<.12){tcp=previousTCP.clone().lerp(stack.clone().setZ(high+.055),(t-.06)/.06);stage='高處移至料台'}
 else if(t<.22){tcp=stack.clone().setZ(high+.055).lerp(stack.clone().add(V([0,0,.055])),(t-.12)/.1);stage='下降／吸附夾持'}
 else if(t<.39){pos.lerp(lift,(t-.22)/.17);held=true;stage='垂直提板至淨空高度'}
 else if(t<.55){pos=lift.clone().lerp(hover,(t-.39)/.16);held=true;stage='高處平移'}
 else if(t<.67){pos=hover.clone();q.slerp(p.q,(t-.55)/.12);held=true;stage='組裝區上方轉向'}
 else if(t<.88){pos=hover.clone().lerp(dest,(t-.67)/.21);q.copy(p.q);held=true;stage='由上往下插入定位'}
 else{pos=dest;q.copy(p.q);toolQ.copy(q);tcp=contact(dest).lerp(contact(hover),(t-.88)/.12);stage='釋放／垂直退離'}
 if(held){toolQ.copy(q);tcp=pos.clone().addScaledVector(V([0,0,1]).applyQuaternion(q),.055)}
 return {pos,q,tcp,toolQ,stage,held};
}
function updateTrajectory(p,index){
 const points=[];for(let i=0;i<=100;i++)points.push(factoryPose(p,i/100,index).tcp);
 trajectory.geometry.dispose();trajectory.geometry=new T.BufferGeometry().setFromPoints(points);trajectory.visible=document.getElementById('trajectory').checked;
}
function collisionCheck(active,done,held,finalApproach){
 collisionBoxes.forEach(m=>{scene.remove(m);m.geometry.dispose();m.material.dispose()});collisionBoxes=[];
 if(!document.getElementById('collisions').checked)return ['碰撞預檢已關閉'];
 scene.updateMatrixWorld(true);const hits=[],targets=[];
 for(let i=0;i<done;i++)targets.push({mesh:installed[i],name:DATA.parts[i].role_label});
 targets.push(...obstacles);
 const movers=abbMeshes.slice(1).map((mesh,i)=>({mesh,name:'A'+(i+1)+' 臂段'}));movers.push({mesh:toolGroup,name:'夾具'});
 if(held)movers.push({mesh:active,name:'搬運板件'});
 for(const moving of movers){const a=new T.Box3().setFromObject(moving.mesh);
  for(const target of targets){const b=new T.Box3().setFromObject(target.mesh);if(a.intersectsBox(b)){
   hits.push(moving.name+'／'+target.name+(moving.name==='搬運板件'&&finalApproach?'（定位接觸待核對）':''));
   const helper=new T.Box3Helper(b,0xe15550);helper.material.depthTest=false;helper.material.transparent=true;helper.material.opacity=.85;helper.renderOrder=100;scene.add(helper);collisionBoxes.push(helper);
  }}
 }
 return [...new Set(hits)];
}
