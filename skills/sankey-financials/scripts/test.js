// Static checks for a sankey-financials CFG: arithmetic, structure and label layout.
// Usage: node test.js cfg.json   (exit 1 on any ERROR)
const fs=require('fs'),vm=require('vm'),path=require('path');
const CFG=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const engine=fs.readFileSync(path.join(__dirname,'engine.js'),'utf8');
const TOL=0.51,VW=760;
const issues=[];const add=(sev,area,msg)=>issues.push({sev,area,msg});

// ---------- data ----------
const base=Object.fromEntries(CFG.base.map(n=>[n.id,n]));
const hub=CFG.hub?base[CFG.hub]:null;
if(CFG.hub&&!hub)add('ERROR','data',`hub "${CFG.hub}" not in base`);
if(!hub&&!CFG.scale)add('ERROR','data','no hub, so CFG.scale {v,l} is required');
if(!hub&&CFG.views)add('ERROR','data','views need a hub to flow into');
for(const [k,v] of Object.entries(CFG.views||{})){
  const nodes=v.same?CFG.views[v.same]?.nodes:v.nodes;
  if(!nodes){add('ERROR','data',`view ${k} has no nodes`);continue}
  if(!v.label)add('ERROR','data',`view ${k} has no label`);
  const sum=nodes.reduce((a,n)=>a+n.v,0);
  if(hub&&Math.abs(sum-hub.v)>TOL)add('ERROR','data',`view ${k}: items sum ${sum.toFixed(1)} != ${hub.l} ${hub.v}`);
  nodes.forEach(n=>{
    if(n.v===0)add('ERROR','data',`view ${k}: ${n.id} is zero; drop it`);
    if(n.v<0)add('INFO','data',`view ${k}: ${n.id} is negative; drawn as a gray branch off ${hub?.l}`);
    if(base[n.id])add('ERROR','data',`view ${k}: id ${n.id} collides with a base node`);
  });
}
const ids=new Set();CFG.base.forEach(n=>{if(ids.has(n.id))add('ERROR','data',`duplicate id ${n.id}`);ids.add(n.id);
  if(!(n.v>0))add('ERROR','data',`${n.id} value ${n.v} must be positive; restructure (gains/losses become separate nodes)`);
  if(!['rev','profit','cost','other','loss'].includes(n.t))add('ERROR','data',`${n.id} bad type ${n.t}`);
  if(!Number.isInteger(n.c)||n.c<0)add('ERROR','data',`${n.id} bad column ${n.c}`)});
const inflow={},outflow={};
CFG.links.forEach(([a,b,v])=>{
  if(!base[a])add('ERROR','data',`link source ${a} missing`);
  if(!base[b])add('ERROR','data',`link target ${b} missing`);
  if(!(v>0))add('ERROR','data',`link ${a}->${b} must be positive, got ${v}`);
  outflow[a]=(outflow[a]||0)+v;inflow[b]=(inflow[b]||0)+v;
  if(base[a]&&base[b]&&base[b].c<=base[a].c)add('ERROR','data',`link ${a}->${b} must move right (c ${base[a].c} -> ${base[b].c})`);
});
if(hub&&CFG.views)inflow[CFG.hub]=hub.v;
CFG.base.forEach(n=>{
  const i=inflow[n.id],o=outflow[n.id];
  if(i!=null&&Math.abs(i-n.v)>TOL)add('ERROR','data',`${n.id}: inflows ${i.toFixed(1)} != value ${n.v}`);
  if(o!=null&&Math.abs(o-n.v)>TOL)add('ERROR','data',`${n.id}: outflows ${o.toFixed(1)} != value ${n.v}`);
  if(i==null&&o==null)add('ERROR','data',`${n.id} is not connected`);
  if(n.p!=null&&n.p<=0)add('INFO','yoy',`${n.id} prior ${n.p} <= 0, shows n/m`);
  if(n.p!=null&&n.p>0&&Math.abs(n.v/n.p-1)>3)add('WARN','yoy',`${n.id} change ${(100*(n.v/n.p-1)).toFixed(0)}%, double-check the prior figure`);
});

// ---------- layout ----------
const el={innerHTML:'',style:{},setAttribute(k,v){this[k]=v},addEventListener(){},querySelectorAll:()=>[]};
const ctx={CFG,document:{getElementById:()=>el},console};vm.createContext(ctx);
vm.runInContext(engine+';this.S=S;this.render=render;this.st=()=>({NODES,XS,VH,NC,lbox,K})',ctx);
const ov=(a,b)=>a.x0<b.x1-1&&b.x0<a.x1-1&&a.y0<b.y1-1&&b.y0<a.y1-1;
const views=CFG.views?Object.keys(CFG.views):[null];
const yoys=CFG.yoy===false?[false]:[true,false];
for(const view of views)for(const yoy of yoys){
  ctx.S.view=view;ctx.S.yoy=yoy;
  try{ctx.render()}catch(e){add('ERROR','engine',`${view}: render threw ${e.message}`);continue}
  const tag=`${view||'main'}/${yoy?'cmp':'no-cmp'}`;const G=ctx.st();
  G.NODES.forEach(n=>{if(!isFinite(n.y))add('ERROR','layout',`${tag}: ${n.id} has no position`);if(n.tiny)add('INFO','layout',`${tag}: ${n.id} drawn at minimum width`)});
  for(let c=0;c<G.NC;c++){const col=G.NODES.filter(n=>n.c===c).sort((a,b)=>a.y-b.y);
    for(let i=1;i<col.length;i++)if(col[i].y<col[i-1].y+col[i-1].h-0.5)add('ERROR','layout',`${tag}: nodes ${col[i-1].id} and ${col[i].id} overlap`)}
  const B=G.NODES.map(n=>({id:n.id,...G.lbox(n)}));
  B.forEach(b=>{if(b.x0<0||b.x1>VW||b.y0<56||b.y1>G.VH)add('ERROR','label',`${tag}: label ${b.id} off canvas`)});
  for(let i=0;i<B.length;i++)for(let j=i+1;j<B.length;j++)if(ov(B[i],B[j]))add('ERROR','label',`${tag}: labels ${B[i].id} and ${B[j].id} overlap`);
  B.forEach(b=>G.NODES.forEach(n=>{if(n.id!==b.id&&ov(b,{x0:G.XS[n.c],x1:G.XS[n.c]+10,y0:n.y,y1:n.y+n.h}))add('ERROR','label',`${tag}: label ${b.id} covers node ${n.id}`)}));
  if(G.VH>1400)add('WARN','layout',`${tag}: chart is ${Math.round(G.VH)}px tall; consider grouping small items`);
}
const seen=new Set(),u=issues.filter(i=>{const k=i.sev+i.msg.replace(/^\S+\/\S+: /,'');if(seen.has(k))return false;seen.add(k);return true});
const ord={ERROR:0,WARN:1,INFO:2};u.sort((a,b)=>ord[a.sev]-ord[b.sev]);
const quiet=process.argv.includes('-q');
u.filter(i=>!quiet||i.sev!=='INFO').forEach(i=>console.log(`${i.sev.padEnd(5)} [${i.area}] ${i.msg}`));
const n=s=>u.filter(i=>i.sev===s).length;
console.log(`${path.basename(process.argv[2])}: ${n('ERROR')} errors, ${n('WARN')} warnings, ${n('INFO')} info`);
process.exit(n('ERROR')?1:0);
