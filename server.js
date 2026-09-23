import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { URL } from 'node:url';
import crypto from 'node:crypto';

const PORT = Number(process.env.PORT || 3000);
const CLIENT_ID = process.env.ML_CLIENT_ID || '';
const CLIENT_SECRET = process.env.ML_CLIENT_SECRET || '';
const REDIRECT_URI = process.env.ML_REDIRECT_URI || '';
const sessions = new Map();
const tokens = new Map();
const publicFile = new URL('./public/index.html', import.meta.url);

function json(res, code, data){ res.writeHead(code, {'content-type':'application/json; charset=utf-8','cache-control':'no-store'}); res.end(JSON.stringify(data)); }
function cookie(name,value){ return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Secure`; }
function getSession(req,res){
  const raw=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('sid='));
  let sid=raw?.slice(4);
  if(!sid){ sid=crypto.randomBytes(24).toString('hex'); sessions.set(sid,{state:null,codeVerifier:null}); res.setHeader('Set-Cookie',cookie('sid',sid)); }
  if(!sessions.has(sid)) sessions.set(sid,{});
  return {sid,s:sessions.get(sid)};
}
function mlAuthUrl(state, verifier){
  const p=new URLSearchParams({response_type:'code',client_id:CLIENT_ID,redirect_uri:REDIRECT_URI,state});
  if(verifier){
    const challenge=crypto.createHash('sha256').update(verifier).digest('base64url');
    p.set('code_challenge',challenge); p.set('code_challenge_method','S256');
  }
  return `https://auth.mercadolivre.com.br/authorization?${p}`;
}
async function exchange(code, verifier){
  const body=new URLSearchParams({grant_type:'authorization_code',client_id:CLIENT_ID,client_secret:CLIENT_SECRET,code,redirect_uri:REDIRECT_URI});
  if(verifier) body.set('code_verifier',verifier);
  const r=await fetch('https://api.mercadolibre.com/oauth/token',{method:'POST',headers:{accept:'application/json','content-type':'application/x-www-form-urlencoded'},body});
  const data=await r.json(); if(!r.ok) throw new Error(data.message || data.error || `OAuth ${r.status}`); return data;
}
async function mlFetch(path, access){
  const r=await fetch(`https://api.mercadolibre.com${path}`,{headers:{Authorization:`Bearer ${access}`,accept:'application/json'}});
  const data=await r.json(); if(!r.ok) throw new Error(data.message || data.error || `API ${r.status}`); return data;
}
function analyze(items,{cost=0,freight=0,commissionPct=0,taxPct=0,other=0,fixed=0,minMargin=20,maxDays=10}={}){
  const prices=items.map(x=>Number(x.price)).filter(Number.isFinite).sort((a,b)=>a-b);
  const median=prices.length?(prices.length%2?prices[(prices.length-1)/2]:(prices[prices.length/2-1]+prices[prices.length/2])/2):null;
  const base=Number(cost)+Number(freight)+Number(other)+Number(fixed);
  const feePct=(Number(commissionPct)+Number(taxPct))/100;
  const minPrice=feePct<1 ? base/(1-0.20-feePct) : null;
  const suggested=median ?? minPrice;
  return {count:items.length,market:{min:prices[0]??null,max:prices.at(-1)??null,median},minimumPriceFor20Margin:minPrice,suggestedPrice:suggested,items:items.map(i=>{const p=Number(i.price);const fees=p*feePct;const profit=p-base-fees;const margin=p?profit/p*100:0;return {...i,profit,margin,decision:margin>=Number(minMargin)?'APROVAR':'REJEITAR'};})};
}
async function handler(req,res){
  const {sid,s}=getSession(req,res); const u=new URL(req.url,`http://${req.headers.host}`);
  if(u.pathname==='/health') return json(res,200,{ok:true,version:'1.6.0'});
  if(u.pathname==='/oauth/start'){
    if(!CLIENT_ID||!REDIRECT_URI) return json(res,503,{error:'OAuth não configurado no servidor. Preencha ML_CLIENT_ID e ML_REDIRECT_URI.'});
    s.state=crypto.randomBytes(24).toString('hex'); s.codeVerifier=crypto.randomBytes(32).toString('base64url');
    res.writeHead(302,{Location:mlAuthUrl(s.state,s.codeVerifier)}); return res.end();
  }
  if(u.pathname==='/oauth/callback'){
    const state=u.searchParams.get('state'), code=u.searchParams.get('code'), err=u.searchParams.get('error');
    if(err) return json(res,400,{error:err,description:u.searchParams.get('error_description')});
    if(!code||!state||state!==s.state) return json(res,400,{error:'state inválido ou código ausente'});
    try{ const t=await exchange(code,s.codeVerifier); tokens.set(sid,t); s.connectedAt=Date.now(); res.writeHead(302,{Location:'/'}); return res.end(); }
    catch(e){return json(res,400,{error:e.message});}
  }
  if(u.pathname==='/api/status') return json(res,200,{configured:Boolean(CLIENT_ID&&CLIENT_SECRET&&REDIRECT_URI),connected:tokens.has(sid),redirectUri:REDIRECT_URI||null});
  if(u.pathname==='/api/me'){
    const t=tokens.get(sid); if(!t) return json(res,401,{error:'not_connected'});
    try{return json(res,200,await mlFetch('/users/me',t.access_token));}catch(e){return json(res,401,{error:e.message});}
  }
  if(u.pathname==='/api/search'){
    const t=tokens.get(sid); if(!t) return json(res,401,{error:'not_connected'});
    const q=(u.searchParams.get('q')||'').trim(); if(!q) return json(res,400,{error:'Informe o produto.'});
    try{
      const data=await mlFetch(`/sites/MLB/search?q=${encodeURIComponent(q)}&limit=20`,t.access_token);
      const items=(data.results||[]).map(x=>({id:x.id,title:x.title,price:x.price,currency:x.currency_id,sellerId:x.seller?.id??x.seller_id??null,condition:x.condition,availableQuantity:x.available_quantity,permalink:x.permalink,thumbnail:x.thumbnail,shipping:x.shipping||null}));
      return json(res,200,{query:q,total:data.paging?.total??items.length,items});
    }catch(e){return json(res,502,{error:e.message});}
  }
  if(u.pathname==='/api/analyze'){
    const t=tokens.get(sid); if(!t) return json(res,401,{error:'not_connected'});
    const q=(u.searchParams.get('q')||'').trim(); if(!q) return json(res,400,{error:'Informe o produto.'});
    try{const data=await mlFetch(`/sites/MLB/search?q=${encodeURIComponent(q)}&limit=20`,t.access_token);const items=(data.results||[]).map(x=>({id:x.id,title:x.title,price:x.price,permalink:x.permalink}));return json(res,200,analyze(items,{cost:Number(u.searchParams.get('cost')||0),freight:Number(u.searchParams.get('freight')||0),commissionPct:Number(u.searchParams.get('commission')||0),taxPct:Number(u.searchParams.get('tax')||0),other:Number(u.searchParams.get('other')||0),fixed:Number(u.searchParams.get('fixed')||0),minMargin:Number(u.searchParams.get('minMargin')||20),maxDays:Number(u.searchParams.get('maxDays')||10)}));}catch(e){return json(res,502,{error:e.message});}
  }
  if(req.method==='GET' && (u.pathname==='/'||u.pathname==='/index.html')){res.writeHead(200,{'content-type':'text/html; charset=utf-8'});return res.end(await readFile(publicFile));}
  res.writeHead(404);res.end('Not found');
}
http.createServer(handler).listen(PORT,()=>console.log(`V1.6 running on port ${PORT}`));
