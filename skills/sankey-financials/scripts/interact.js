function related(id){
  const set=new Set([id]),ls=new Set();
  const up=n=>n.in.forEach(l=>{ls.add(l.i);if(!set.has(l.s.id)){set.add(l.s.id);up(l.s)}});
  const dn=n=>n.out.forEach(l=>{ls.add(l.i);if(!set.has(l.t.id)){set.add(l.t.id);dn(l.t)}});
  up(M[id]);dn(M[id]);return{set,ls};
}
const sk=document.getElementById('sk'),tip=document.getElementById('tip'),wrapEl=document.getElementById('wrap');
function hilite(r){
  sk.querySelectorAll('.lk').forEach(e=>e.style.opacity=!r?.26:r.ls.has(+e.dataset.l)?.5:.06);
  sk.querySelectorAll('.nd,.lb').forEach(e=>e.style.opacity=!r||r.set.has(e.dataset.n)?1:.25);
}
function showTip(e,h){tip.innerHTML=h;tip.style.opacity=1;const r=wrapEl.getBoundingClientRect();let x=e.clientX-r.left+14;if(x>r.width-250)x=e.clientX-r.left-250;tip.style.left=x+'px';tip.style.top=(e.clientY-r.top+14)+'px'}
function nodeTip(n){
  let h=`<div style="font-weight:500;color:var(--text-primary)">${esc(n.full||n.l)}</div><div style="color:var(--text-primary)">${fmt(n.v)} · ${(n.v/SCALE.v*100).toFixed(1)}% of ${esc(SCALE.l.toLowerCase())}</div>`;
  if(CFG.yoy!==false&&n.p!=null)h+=`<div style="color:var(--text-secondary)">${esc(CFG.prevLabel||'Year ago')} ${fmt(n.p)} · ${esc(CFG.cmp||'Y/Y')} ${yoyStr(n)}</div>`;
  [n.note,n.auto,n.tiny?'Too small to draw to scale, so shown at a minimum width.':''].forEach(t=>{if(t)h+=`<div style="color:var(--text-secondary)">${esc(t)}</div>`});
  return h+'<div style="color:var(--text-muted)">Click to ask about this line</div>';
}
sk.addEventListener('mousemove',e=>{
  const t=e.target;
  if(t.classList.contains('nd')){const n=M[t.dataset.n];hilite(related(n.id));showTip(e,nodeTip(n))}
  else if(t.classList.contains('lk')){const l=LINKS[+t.dataset.l];hilite({set:new Set([l.s.id,l.t.id]),ls:new Set([l.i])});showTip(e,`<div style="font-weight:500;color:var(--text-primary)">${esc(l.s.l)} → ${esc(l.t.l)}</div><div style="color:var(--text-primary)">${fmt(l.v)}</div><div style="color:var(--text-secondary)">${(l.v/SCALE.v*100).toFixed(1)}% of ${esc(SCALE.l.toLowerCase())} · ${(l.v/l.s.v*100).toFixed(1)}% of ${esc(l.s.l.toLowerCase())}</div>`)}
  else{hilite(null);tip.style.opacity=0}
});
sk.addEventListener('mouseleave',()=>{hilite(null);tip.style.opacity=0});
sk.addEventListener('click',e=>{const t=e.target;if(t.classList.contains('nd')){const n=M[t.dataset.n];sendPrompt(`Explain ${CFG.company}'s ${CFG.title.replace(CFG.ticker+' ','')} ${n.full||n.l} line (${fmt(n.v)}${S.yoy&&okP(n)?', '+yoyStr(n)+' '+(CFG.cmp||'Y/Y'):''}). What drove it and what should I watch?`)}});
const LEG=CFG.legend||[['Revenue','rev'],['Expense','cost'],['Profit','profit']];
document.getElementById('legend').innerHTML=LEG.map(([l,t])=>`<span class="lg"><span class="dot" style="background:${COL[t]}"></span>${esc(l)}</span>`).join('');
document.getElementById('cmpl').textContent=CFG.cmp||'Y/Y';
if(CFG.yoy===false)document.getElementById('yoy').style.display='none';
const vb=document.getElementById('views');
vb.innerHTML=VK.map((k,i)=>`<button data-v="${k}"${i?'':' class="on"'}>${esc(CFG.views[k].label)}</button>`).join('');
if(VK.length<2)vb.style.display='none';
vb.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;vb.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));S.view=b.dataset.v;document.getElementById('note').textContent=(S.view&&CFG.views[S.view].note)||'';render()});
function setSw(){document.getElementById('yoy').setAttribute('aria-checked',S.yoy);document.getElementById('trk').style.background=S.yoy?'#2a78d6':'var(--border-stronger)';document.getElementById('knb').style.left=S.yoy?'16px':'2px'}
document.getElementById('yoy').addEventListener('click',()=>{S.yoy=!S.yoy;setSw();render()});
setSw();document.getElementById('note').textContent=(S.view&&CFG.views[S.view].note)||'';render();
