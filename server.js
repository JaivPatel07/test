const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 4173);
const ROOT = __dirname;
const sessions = new Map();
const requests = new Map();
const now = () => new Date().toISOString();

const locations = [
  { id:'karsog', name:'Karsog', district:'Mandi', state:'Himachal Pradesh', risk:86, landslideProbability:78, floodProbability:81, leadTimeMinutes:32, rainfall3h:68, soilMoisture:88, slope:37, population:8420, level:'CRITICAL' },
  { id:'thunag', name:'Thunag', district:'Mandi', state:'Himachal Pradesh', risk:74, landslideProbability:74, floodProbability:63, leadTimeMinutes:48, rainfall3h:54, soilMoisture:79, slope:42, population:5680, level:'VERY HIGH' },
  { id:'janjehli', name:'Janjehli', district:'Mandi', state:'Himachal Pradesh', risk:69, landslideProbability:69, floodProbability:57, leadTimeMinutes:66, rainfall3h:48, soilMoisture:72, slope:34, population:4210, level:'HIGH' },
  { id:'sundernagar', name:'Sundernagar', district:'Mandi', state:'Himachal Pradesh', risk:57, landslideProbability:48, floodProbability:57, leadTimeMinutes:84, rainfall3h:41, soilMoisture:68, slope:26, population:12900, level:'HIGH' },
  { id:'aut', name:'Aut', district:'Mandi', state:'Himachal Pradesh', risk:43, landslideProbability:37, floodProbability:44, leadTimeMinutes:130, rainfall3h:29, soilMoisture:58, slope:24, population:3160, level:'MODERATE' },
  { id:'gohar', name:'Gohar', district:'Mandi', state:'Himachal Pradesh', risk:31, landslideProbability:28, floodProbability:32, leadTimeMinutes:185, rainfall3h:22, soilMoisture:46, slope:19, population:6730, level:'MODERATE' },
  { id:'pandoh', name:'Pandoh', district:'Mandi', state:'Himachal Pradesh', risk:22, landslideProbability:19, floodProbability:26, leadTimeMinutes:null, rainfall3h:16, soilMoisture:35, slope:16, population:2840, level:'LOW' },
];
const alerts = [
  { id:'ALT-0923-001', locationId:'karsog', severity:'EMERGENCY', event:'Flash flood', probability:86, leadTimeMinutes:32, message:'Move residents to designated shelters immediately.', issuedAt:'2026-09-23T18:22:00+05:30', status:'ACTIVE' },
  { id:'ALT-0923-002', locationId:'thunag', severity:'WARNING', event:'Landslide', probability:74, leadTimeMinutes:48, message:'Prepare evacuation and inspect vulnerable roads.', issuedAt:'2026-09-23T18:08:00+05:30', status:'ACTIVE' },
  { id:'ALT-0923-003', locationId:'sundernagar', severity:'WARNING', event:'Flash flood', probability:57, leadTimeMinutes:84, message:'Prepare response teams near river-adjacent wards.', issuedAt:'2026-09-23T17:51:00+05:30', status:'ACTIVE' },
  { id:'ALT-0923-004', locationId:'janjehli', severity:'WATCH', event:'Landslide', probability:69, leadTimeMinutes:66, message:'Monitor rainfall and slope conditions.', issuedAt:'2026-09-23T17:38:00+05:30', status:'ACTIVE' },
];
const incidents = [];
const sensors = [
  { id:'KGS-044', name:'Karsog sensor cluster', type:'soil-moisture', locationId:'karsog', lastReadingAt:new Date(Date.now()-2*60000).toISOString(), status:'ONLINE' },
  { id:'THN-012', name:'Thunag rain gauge', type:'rainfall', locationId:'thunag', lastReadingAt:new Date(Date.now()-4*60000).toISOString(), status:'ONLINE' },
  { id:'RIV-009', name:'Beas tributary gauge', type:'water-level', locationId:'sundernagar', lastReadingAt:new Date(Date.now()-42*60000).toISOString(), status:'DELAYED' },
];
const users = [{ id:'usr-001', name:'Riya Pradhan', email:'riya@aegisterrain.in', password:'demo123', role:'OFFICER' }];

function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, { 'Content-Type':'application/json; charset=utf-8', 'Content-Length':Buffer.byteLength(body), 'Cache-Control':'no-store', 'Access-Control-Allow-Origin':'*' });
  res.end(body);
}
function error(res, status, message, code='BAD_REQUEST') { json(res, status, { error:{ code, message } }); }
function ok(res, value) { json(res, 200, { data:value, meta:{ generatedAt:now(), prototype:true } }); }
function body(req) {
  return new Promise((resolve, reject) => {
    let raw='';
    req.on('data', chunk => { raw += chunk; if (raw.length > 1024 * 1024) { reject(new Error('Payload too large')); req.destroy(); } });
    req.on('end', () => { if (!raw) return resolve({}); try { resolve(JSON.parse(raw)); } catch { reject(new Error('Invalid JSON')); } });
    req.on('error', reject);
  });
}
function auth(req) {
  const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  return token && sessions.get(token);
}
function rateLimit(req, res) {
  const ip = req.socket.remoteAddress || 'local';
  const entry = requests.get(ip) || { count:0, started:Date.now() };
  if (Date.now() - entry.started > 60000) { entry.count=0; entry.started=Date.now(); }
  entry.count += 1; requests.set(ip, entry);
  if (entry.count > 600) { error(res,429,'Rate limit exceeded','RATE_LIMITED'); return false; }
  return true;
}
function safeUser(u) { return { id:u.id, name:u.name, email:u.email, role:u.role }; }
function locationById(id) { return locations.find(x => x.id === id); }

async function api(req, res, url) {
  const parts = url.pathname.split('/').filter(Boolean);
  const method = req.method;
  if (parts[1] === 'health' && method === 'GET') return ok(res, { status:'operational', services:{ api:'ONLINE', riskEngine:'ONLINE', rainfall:'ONLINE', soilMoisture:'ONLINE', weather:'ONLINE' } });

  if (parts[1] === 'auth' && parts[2] === 'login' && method === 'POST') {
    let input; try { input=await body(req); } catch { return error(res,400,'Invalid request body'); }
    const user=users.find(u => u.email.toLowerCase() === String(input.email||'').toLowerCase());
    if (!user || String(input.password||'') !== user.password) return error(res,401,'Email or password is incorrect','UNAUTHORIZED');
    const token=crypto.randomBytes(24).toString('hex'); sessions.set(token,user.id);
    return ok(res,{ token, user:safeUser(user), expiresIn:3600 });
  }
  if (parts[1] === 'auth' && parts[2] === 'register' && method === 'POST') {
    let input; try { input=await body(req); } catch { return error(res,400,'Invalid request body'); }
    if (!input.name || !input.email || String(input.password||'').length < 6) return error(res,422,'Name, email and a password of at least 6 characters are required','VALIDATION_ERROR');
    if (users.some(u=>u.email.toLowerCase()===String(input.email).toLowerCase())) return error(res,409,'An account with this email already exists','CONFLICT');
    const user={id:`usr-${String(users.length+1).padStart(3,'0')}`,name:String(input.name),email:String(input.email),password:String(input.password),role:'CITIZEN'}; users.push(user);
    return json(res,201,{data:{user:safeUser(user),emailVerificationRequired:true},meta:{generatedAt:now(),prototype:true}});
  }
  if (parts[1] === 'auth' && parts[2] === 'logout' && method === 'POST') { const token=String(req.headers.authorization||'').replace(/^Bearer\s+/i,''); sessions.delete(token); return ok(res,{loggedOut:true}); }
  if (parts[1] === 'auth' && parts[2] === 'me' && method === 'GET') { const id=auth(req); if (!id) return error(res,401,'Authentication required','UNAUTHORIZED'); return ok(res,safeUser(users.find(u=>u.id===id))); }

  if (parts[1] === 'locations' && method === 'GET') {
    const q=String(url.searchParams.get('query')||'').toLowerCase(); return ok(res,q?locations.filter(x=>`${x.name} ${x.district} ${x.state}`.toLowerCase().includes(q)):locations);
  }
  if (parts[1] === 'locations' && parts[2] && method === 'GET') { const item=locationById(parts[2]); return item?ok(res,item):error(res,404,'Location not found','NOT_FOUND'); }
  if (parts[1] === 'risk' && parts[2] && method === 'GET') { const item=locationById(parts[2]); if (!item) return error(res,404,'Location not found','NOT_FOUND'); return ok(res,{locationId:item.id,current:item,forecast:[{horizon:'30m',risk:item.risk},{horizon:'1h',risk:Math.min(99,item.risk+4)},{horizon:'3h',risk:Math.min(99,item.risk+10)},{horizon:'6h',risk:Math.min(99,item.risk+16)}],factors:[{name:'Rainfall intensity',contribution:92},{name:'Soil moisture',contribution:84},{name:'Slope',contribution:78},{name:'Historical susceptibility',contribution:71}]}); }
  if (parts[1] === 'alerts' && method === 'GET') return ok(res,alerts);
  if (parts[1] === 'alerts' && method === 'POST') {
    if (!auth(req)) return error(res,401,'Authentication required','UNAUTHORIZED'); let input; try {input=await body(req);} catch {return error(res,400,'Invalid request body');}
    if (!input.locationId || !input.severity || !input.event) return error(res,422,'locationId, severity and event are required','VALIDATION_ERROR');
    const item=locationById(input.locationId); if (!item) return error(res,404,'Location not found','NOT_FOUND');
    const alert={id:`ALT-${Date.now()}`,locationId:item.id,severity:String(input.severity),event:String(input.event),probability:Number(input.probability||item.risk),leadTimeMinutes:Number(input.leadTimeMinutes||item.leadTimeMinutes||0),message:String(input.message||''),issuedAt:now(),status:'ACTIVE'}; alerts.unshift(alert); return json(res,201,{data:alert,meta:{generatedAt:now(),prototype:true}});
  }
  if (parts[1] === 'incidents' && method === 'GET') return ok(res,incidents);
  if (parts[1] === 'incidents' && method === 'POST') {
    let input; try {input=await body(req);} catch {return error(res,400,'Invalid request body');}
    if (!input.location || !input.type || !input.description) return error(res,422,'location, type and description are required','VALIDATION_ERROR');
    const item={id:`INC-${Date.now()}`,...input,status:'UNVERIFIED',createdAt:now()}; incidents.unshift(item); return json(res,201,{data:item,meta:{generatedAt:now(),prototype:true}});
  }
  if (parts[1] === 'shelters' && method === 'GET') return ok(res,[{id:'SH-001',name:'Karsog Community Hall',locationId:'karsog',capacity:280,occupied:211,status:'OPEN'},{id:'SH-002',name:'Thunag Sports Complex',locationId:'thunag',capacity:420,occupied:420,status:'FULL'},{id:'SH-003',name:'Janjehli Primary School',locationId:'janjehli',capacity:180,occupied:46,status:'OPEN'}]);
  if (parts[1] === 'data-health' && method === 'GET') return ok(res,{sources:[{name:'IMD rainfall feed',status:'ONLINE',freshnessMinutes:2},{name:'ISRO soil moisture',status:'ONLINE',freshnessMinutes:14},{name:'Weather forecast API',status:'ONLINE',freshnessMinutes:8},{name:'River gauge network',status:'DELAYED',freshnessMinutes:42}],pipeline:{lastRun:now(),validatedRecords:18227,quarantinedRecords:17}});
  if (parts[1] === 'models' && method === 'GET') return ok(res,{deployed:{version:'RF-2.4.1',f1:0.91,precision:0.93,recall:0.89,rocAuc:0.95,lastTrained:'2026-09-12'},registry:[{version:'RF-2.4.1',status:'DEPLOYED'},{version:'GB-2.4.0',status:'ARCHIVED'},{version:'LR-2.3.2',status:'ARCHIVED'}]});
  if (parts[1] === 'sensors' && parts[2] === 'data' && method === 'POST') {
    const id=auth(req); if (!id) return error(res,401,'Sensor API authentication required','UNAUTHORIZED'); let input; try {input=await body(req);} catch {return error(res,400,'Invalid JSON payload');}
    if (!input.sensorId || !input.timestamp || !input.location) return error(res,422,'sensorId, timestamp and location are required','VALIDATION_ERROR');
    if (input.soilMoisture != null && (Number(input.soilMoisture)<0 || Number(input.soilMoisture)>100)) return error(res,422,'soilMoisture must be between 0 and 100','VALIDATION_ERROR');
    const reading={id:`RD-${Date.now()}`,acceptedAt:now(),...input}; return json(res,202,{data:{accepted:true,reading},meta:{generatedAt:now(),pipeline:'queued-for-validation',prototype:true}});
  }
  if (parts[1] === 'sensors' && method === 'GET') return ok(res,sensors);
  if (parts[1] === 'reports' && method === 'GET') return ok(res,{availableFormats:['PDF','CSV'],reports:[{id:'RPT-001',name:'Monsoon situation report',format:'PDF',status:'READY'},{id:'RPT-002',name:'Village risk register',format:'CSV',status:'READY'}]});
  return error(res,404,'API route not found','NOT_FOUND');
}

function staticFile(req,res,url) {
  let pathname=decodeURIComponent(url.pathname); if (pathname==='/' || pathname==='') pathname='/index.html';
  const file=path.normalize(path.join(ROOT,pathname));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return error(res,404,'File not found','NOT_FOUND');
  const type={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.md':'text/plain; charset=utf-8'}[path.extname(file)]||'application/octet-stream';
  res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-cache'}); fs.createReadStream(file).pipe(res);
}
const server=http.createServer(async (req,res)=>{
  if (req.method==='OPTIONS') { res.writeHead(204,{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'GET,POST,PUT,PATCH,DELETE,OPTIONS'}); return res.end(); }
  if (!rateLimit(req,res)) return;
  const url=new URL(req.url,`http://${req.headers.host||'localhost'}`);
  try { if (url.pathname.startsWith('/api/')) return await api(req,res,url); return staticFile(req,res,url); }
  catch (e) { console.error(e); return error(res,500,'Unexpected server error','SERVER_ERROR'); }
});
server.listen(PORT,'0.0.0.0',()=>console.log(`Aegis Terrain API and web server listening on 0.0.0.0:${PORT}`));
