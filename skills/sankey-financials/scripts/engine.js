const COL={rev:'#2a78d6',profit:'#1baf7a',cost:'#eb6834',other:'#888780',loss:'#e34948'};
const VW=760,NW=10,TOP=72,BASEH=470,LH=15,MINGAP=14,MINH=2;
const VK=Object.keys(CFG.views||{});
const HUB=CFG.hub?CFG.base.find(n=>n.id===CFG.hub):null;
const SCALE=CFG.scale||{v:HUB.v,l:HUB.l};
const K=BASEH*0.72/SCALE.v;
const UNIT=CFG.unit||'usd_m';
const S={view:VK[0]||null,yoy:CFG.yoy!==false};
let NODES=[],LINKS=[],M={},XS=[],NC=1,H=BASEH,VH=600,WRAP=100;
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const tw=(s,z)=>String(s).length*z*0.56;
const fmt=v=>{const a=Math.abs(v),sg=v<0?'-':'';if(UNIT==='pct')return sg+a.toFixed(a<10?2:1)+'%';return sg+(a>=1e6?'$'+(a/1e6).toFixed(2)+'T':a>=1000?'$'+(a/1000).toFixed(2)+'B':'$'+a.toFixed(1)+'M')};
const okP=n=>n.p!=null&&n.p>0;
const yoyStr=n=>{if(!okP(n))return'n/m';const r=(n.v/n.p-1)*100;return Math.abs(r)<0.05?'0.0%':(r>0?'+':'')+r.toFixed(1)+'%'};
const good=n=>n.t==='rev'||n.t==='profit';
const yoyCol=n=>!okP(n)||!good(n)?'var(--text-secondary)':n.v>=n.p?'var(--text-success)':'var(--text-danger)';
function src(){if(!S.view)return[];const v=CFG.views[S.view];return v.same?CFG.views[v.same].nodes:v.nodes}
function side(n){return n.sd||(n.c===0?'left':(n.c===NC-1||!n.out.length)?'right':'above')}
function wrap(s,max){
  if(tw(s,12.5)<=max)return[s];
  const w=s.split(' ');let a=[],cur='';
  w.forEach(x=>{const t=cur?cur+' '+x:x;if(tw(t,12.5)>max&&cur){a.push(cur);cur=x}else cur=t});
  if(cur)a.push(cur);return a;
}
function lines(n){
  const L=[{s:fmt(n.v),f:COL[n.t],z:13,w:500}];
  if(S.yoy)L.push({s:yoyStr(n),f:yoyCol(n),z:12,w:400});
  const names=side(n)==='above'?wrap(n.l,WRAP):[n.l];
  names.forEach(s=>L.push({s,f:'var(--text-primary)',z:12.5,w:400}));
  return L;
}
const labH=n=>lines(n).length*LH;
const topExt=n=>side(n)==='above'?labH(n)+8:Math.max(0,(labH(n)-n.h)/2)+4;
const botExt=n=>side(n)==='above'?0:Math.max(0,(labH(n)-n.h)/2)+4;
function build(){
  const s=src(),pos=s.filter(n=>n.v>0),neg=s.filter(n=>n.v<0);
  NODES=pos.map(n=>({t:'rev',...n,c:0})).concat(CFG.base.map(n=>({...n})));
  if(HUB&&neg.length){
    const hc=HUB.c;
    neg.forEach(n=>NODES.push({...n,c:hc+1,t:'other',v:-n.v,p:n.p!=null&&n.p<0?-n.p:null,neg:true,
      note:(n.note?n.note+' ':'')+`Reduces ${HUB.l.toLowerCase()} by ${fmt(-n.v)}.`}));
  }
  NC=Math.max(...NODES.map(n=>n.c))+1;
  M={};NODES.forEach((n,i)=>{n.i=i;n.in=[];n.out=[];M[n.id]=n});
  const negSum=neg.reduce((a,n)=>a-n.v,0);
  NODES.forEach(n=>{const dv=n.id===CFG.hub?n.v+negSum:n.v;n.dv=dv;n.tiny=dv*K<MINH;n.h=Math.max(MINH,dv*K)});
  if(HUB&&negSum)M[CFG.hub].auto=`Drawn before ${fmt(negSum)} of negative items, which branch off to the right.`;
  LINKS=pos.map(n=>({s:M[n.id],t:M[CFG.hub],v:n.v}))
    .concat(CFG.links.map(([a,b,v])=>({s:M[a],t:M[b],v})))
    .concat(neg.map(n=>({s:M[CFG.hub],t:M[n.id],v:-n.v})));
  LINKS.forEach((l,i)=>{l.i=i;l.w=Math.max(1,l.v*K);l.s.out.push(l);l.t.in.push(l)});
  NODES.forEach(n=>{n.out.sort((a,b)=>a.t.i-b.t.i);let o=0;n.out.forEach(l=>{l.so=o;o+=l.w})});
  const lw=n=>Math.max(...[fmt(n.v),S.yoy?yoyStr(n):'',n.l].map((s,k)=>tw(s,k===0?13:12.5)));
  const c0=NODES.filter(n=>n.c===0),cl=NODES.filter(n=>n.c===NC-1);
  const left=Math.max(110,(c0.length?Math.max(...c0.map(lw)):0)+14);
  const right=Math.min(VW-140,VW-Math.max(...cl.map(lw))-NW-14);
  XS=Array.from({length:NC},(_,c)=>NC===1?left:Math.round(left+c*(right-left)/(NC-1)));
  WRAP=NC>1?(right-left)/(NC-1)-12:200;
}
const gap=(a,b)=>Math.max(MINGAP,botExt(a)+topExt(b));
function cols(){return[...Array(NC)].map((_,c)=>NODES.filter(n=>n.c===c))}
function resolve(col){
  let p=null;
  col.forEach(n=>{const lo=p?p.y+p.h+gap(p,n):TOP+topExt(n);n.y=Math.max(n.ideal,lo);p=n});
}
function layout(){
  const C=cols(),start=TOP+Math.max(...C.filter(c=>c.length).map(c=>topExt(c[0])));
  let from=0;
  if(HUB){
    const hub=M[CFG.hub];hub.y=start;
    if(hub.c===1){let o=0;C[0].forEach(n=>{n.ideal=hub.y+o;o+=n.h});resolve(C[0]);from=1}
  }
  for(let c=from;c<NC;c++){
    C[c].forEach(n=>{n.ideal=HUB&&n.id===CFG.hub?M[CFG.hub].y:n.in.length?Math.min(...n.in.map(l=>l.s.y+l.so)):-Infinity});
    resolve(C[c]);
  }
  NODES.forEach(n=>{n.in.sort((a,b)=>a.s.y-b.s.y||a.s.i-b.s.i);let t=0;n.in.forEach(l=>{l.to=t;t+=l.w})});
  H=Math.max(...NODES.map(n=>n.y+n.h+botExt(n)))-TOP;VH=TOP+H+24;
  return C;
}
function lbox(n){
  const L=lines(n),tot=L.length*LH,sd=side(n),w=Math.max(...L.map(q=>tw(q.s,q.z)));let x0,y0;
  if(sd==='left'){x0=XS[0]-7-w;y0=n.y+n.h/2-tot/2}
  else if(sd==='right'){x0=XS[n.c]+NW+7;y0=n.y+n.h/2-tot/2}
  else{x0=XS[n.c]+NW/2-w/2;y0=n.y-6-tot}
  return{x0,x1:x0+w,y0,y1:y0+tot};
}
const hit=(a,b)=>a.x0<b.x1&&b.x0<a.x1&&a.y0<b.y1&&b.y0<a.y1;
function fixLeaves(){
  let moved=false;
  NODES.filter(n=>n.c>0&&n.c<NC-1&&!n.out.length&&!n.sd).forEach(n=>{
    const b=lbox(n);b.x1+=4;
    const clash=NODES.some(m=>m!==n&&m.c>n.c&&(hit(b,{x0:XS[m.c],x1:XS[m.c]+NW,y0:m.y-4,y1:m.y+m.h+4})||hit(b,lbox(m))));
    if(clash){n.sd='above';moved=true}
  });
  return moved;
}
function label(n){
  const L=lines(n),tot=L.length*LH,sd=side(n);let x,a,y0;
  if(sd==='left'){x=XS[0]-7;a='end';y0=n.y+n.h/2-tot/2+11}
  else if(sd==='right'){x=XS[n.c]+NW+7;a='start';y0=n.y+n.h/2-tot/2+11}
  else{x=XS[n.c]+NW/2;a='middle';y0=n.y-6-tot+11}
  return `<g class="lb" data-n="${n.id}" style="pointer-events:none">`+L.map((q,k)=>`<text x="${x}" y="${(y0+k*LH).toFixed(1)}" text-anchor="${a}" style="fill:${q.f};font-size:${q.z}px;font-weight:${q.w}">${esc(q.s)}</text>`).join('')+'</g>';
}
function render(){
  build();layout();if(fixLeaves())layout();let g='<defs>',p='',nd='',lb='';
  LINKS.forEach(l=>{
    const x0=XS[l.s.c]+NW,x1=XS[l.t.c],xm=(x0+x1)/2,a=l.s.y+l.so,b=a+l.w,c=l.t.y+l.to,d=c+l.w;
    g+=`<linearGradient id="lg${l.i}" gradientUnits="userSpaceOnUse" x1="${x0}" x2="${x1}"><stop offset="0" stop-color="${COL[l.s.t]}"/><stop offset="1" stop-color="${COL[l.t.t]}"/></linearGradient>`;
    p+=`<path class="lk" data-l="${l.i}" d="M${x0},${a}C${xm},${a} ${xm},${c} ${x1},${c}L${x1},${d}C${xm},${d} ${xm},${b} ${x0},${b}Z" fill="url(#lg${l.i})" style="opacity:.26;transition:opacity .12s;cursor:pointer"/>`;
  });
  NODES.forEach(n=>{nd+=`<rect class="nd" data-n="${n.id}" x="${XS[n.c]}" y="${n.y.toFixed(1)}" width="${NW}" height="${n.h.toFixed(1)}" rx="1.5" fill="${COL[n.t]}" style="cursor:pointer;transition:opacity .12s"/>`;lb+=label(n)});
  const t=`<text x="${VW/2}" y="30" text-anchor="middle" style="fill:var(--text-primary);font-size:17px;font-weight:500">${esc(CFG.title)}</text><text x="${VW/2}" y="50" text-anchor="middle" style="fill:var(--text-secondary);font-size:12px">${esc(CFG.sub)}</text>`;
  const sk=document.getElementById('sk');sk.setAttribute('viewBox',`0 0 ${VW} ${Math.ceil(VH)}`);
  sk.innerHTML=g+'</defs>'+t+p+nd+lb;
}
