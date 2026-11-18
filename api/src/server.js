const express = require('express');
const { Pool } = require('pg');
const http = require('node:http');
const crypto = require('node:crypto');
const { WebSocketServer, WebSocket } = require('ws');
const { log } = require('../../shared/log');
const { validCategory, requestHash, estimateMinutes, samePosto } = require('../../shared/core');
const {issueToken,verifyToken,bearer,equalSecret,authenticate}=require('./security');
const {startSubscriber}=require('./rabbit');

const app=express();
app.disable('x-powered-by');
app.set('trust proxy',1);
const pool=new Pool({connectionString:process.env.DATABASE_URL, max:8,connectionTimeoutMillis:8000,idleTimeoutMillis:10000});
pool.on('error',e=>log('error','postgres_idle_error',{error:e.message}));
const route=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
const isUuid=x=>typeof x==='string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x);
const intId=x=>{const n=Number(x);return Number.isInteger(n)&&n>0&&String(n)===String(x)?n:null;};
const httpError=(status,message)=>Object.assign(new Error(message),{status});

async function loadAwsSecrets(){
  if(!process.env.AWS_SECRET_ID)return;
  const {SecretsManagerClient,GetSecretValueCommand}=require('@aws-sdk/client-secrets-manager');
  const aws=new SecretsManagerClient({region:process.env.AWS_REGION||'sa-east-1'});
  const r=await aws.send(new GetSecretValueCommand({SecretId:process.env.AWS_SECRET_ID}));
  if(!r.SecretString)throw new Error('O segredo AWS precisa ser JSON texto');
  const secret=JSON.parse(r.SecretString);
  if(!secret.JWT_SECRET || !secret.STAFF_PASSWORD)throw new Error('Segredo AWS exige JWT_SECRET e STAFF_PASSWORD');
  process.env.JWT_SECRET=secret.JWT_SECRET;
  process.env.STAFF_PASSWORD=secret.STAFF_PASSWORD;
  log('info','aws_secrets_loaded',{secret_id:process.env.AWS_SECRET_ID});
}

async function tx(fn){
  const client=await pool.connect();
  try {await client.query('BEGIN');const data=await fn(client);await client.query('COMMIT');return data;}
  catch(e){await client.query('ROLLBACK').catch(()=>{});throw e;}
  finally{client.release();}
}
async function addEvent(db,postoId,senhaId,tipo,req,numero){
  const id=crypto.randomUUID();
  await db.query(`INSERT INTO eventos(id,posto_id,senha_id,tipo,payload,correlation_id)
    VALUES($1,$2,$3,$4,$5,$6)`,
    [id,postoId,senhaId,tipo,JSON.stringify({event_id:id,posto_id:postoId,senha_id:senhaId,tipo,numero}),req.correlationId]);
  log('info','event_persisted',{event_id:id,event_type:tipo,correlation_id:req.correlationId});
}
app.use((req,res,next)=>{
  const provided=req.get('X-Correlation-ID');
  req.correlationId=isUuid(provided)?provided:crypto.randomUUID();
  res.setHeader('X-Correlation-ID',req.correlationId);
  const start=Date.now();
  res.once('finish',()=>log('info','http_request',{method:req.method,path:req.path,status:res.statusCode,duration_ms:Date.now()-start,correlation_id:req.correlationId}));
  next();
});
app.use(express.json({limit:'20kb'}));

app.get('/health/live',(_req,res)=>res.json({status:'alive',node:process.env.HOSTNAME||'local'}));
app.get('/health/ready',route(async(_req,res)=>{
  await pool.query('SELECT 1');
  res.json({status:'ready',database:'ok',node:process.env.HOSTNAME||'local',notification_mode:'best_effort'});
}));

app.get('/api/v1/postos',route(async (_req,res)=>{
  const r=await pool.query('SELECT id,nome,cidade FROM postos ORDER BY id');res.json({postos:r.rows});
}));
app.get('/api/v1/postos/:id/fila',route(async(req,res)=>{
  const id=intId(req.params.id);if(!id)throw httpError(400,'ID inválido');
  const r=await pool.query(`SELECT p.id,p.nome,p.media_atendimento_minutos,
    (SELECT COUNT(*)::int FROM guiches g WHERE g.posto_id=p.id AND g.ativo) AS guiches_ativos,
    (SELECT COUNT(*)::int FROM senhas s WHERE s.posto_id=p.id AND s.status='AGUARDANDO') AS total,
    (SELECT COUNT(*)::int FROM senhas s WHERE s.posto_id=p.id AND s.status='AGUARDANDO' AND s.categoria='PRIORITARIA') AS prioritarias
    FROM postos p WHERE p.id=$1`,[id]);
  if(!r.rowCount)throw httpError(404,'Posto inexistente');
  const p=r.rows[0];const tempo=estimateMinutes(p.total,p.guiches_ativos,p.media_atendimento_minutos);
  res.json({posto:p.nome,posto_id:p.id,tempo_espera_minutos:tempo,quantidade_aguardando:p.total,
    prioritarias:p.prioritarias,normais:p.total-p.prioritarias,guiches_ativos:p.guiches_ativos,
    atualizado_em:new Date().toISOString(),estimativa:'SIMULADA'});
}));

// Login de demonstração; credenciais somente do ambiente ou Secrets Manager.
app.post('/api/v1/auth/atendente',route(async(req,res)=>{
  const {usuario,senha,posto_id}=req.body||{};
  const id=Number(posto_id);
  if(!Number.isInteger(id)||id<1||!equalSecret(usuario,process.env.STAFF_USERNAME||'atendente')||!equalSecret(senha,process.env.STAFF_PASSWORD))
    throw httpError(401,'Credenciais inválidas');
  const {rowCount}=await pool.query('SELECT id FROM postos WHERE id=$1',[id]);
  if(!rowCount)throw httpError(403,'Posto não habilitado');
  return res.json({token:issueToken({role:'ATENDENTE',posto_id:id}),expira_em_segundos:7200});
}));

app.post('/api/v1/postos/:id/senhas',route(async(req,res)=>{
  const id=intId(req.params.id);const cat=req.body?.categoria;
  const key=req.get('Idempotency-Key');
  if(!id||!validCategory(cat)||typeof key!=='string'||key.length<8||key.length>128||!/^[a-zA-Z0-9_-]+$/.test(key))
    throw httpError(400,'Posto, categoria ou Idempotency-Key inválidos (8–128 caracteres alfanuméricos, _ ou -)');
  const hash=requestHash(id,cat);
  const outcome=await tx(async db=>{
    const fila=await db.query('SELECT id,proximo_numero FROM filas WHERE posto_id=$1 FOR UPDATE',[id]);
    if(!fila.rowCount)throw httpError(404,'Posto inexistente');
    const f=fila.rows[0];
    const old=await db.query('SELECT id,numero,categoria,status,request_hash FROM senhas WHERE fila_id=$1 AND idempotency_key=$2',[f.id,key]);
    if(old.rowCount){if(old.rows[0].request_hash!==hash)throw httpError(409,'Chave de idempotência já usada com outros dados');
      return {row:old.rows[0],created:false};}
    const ticket=crypto.randomUUID();
    await db.query(`INSERT INTO senhas(id,fila_id,posto_id,numero,categoria,idempotency_key,request_hash)
      VALUES($1,$2,$3,$4,$5,$6,$7)`,[ticket,f.id,id,f.proximo_numero,cat,key,hash]);
    await db.query('UPDATE filas SET proximo_numero=proximo_numero+1 WHERE id=$1',[f.id]);
    await addEvent(db,id,ticket,'SENHA_EMITIDA',req,f.proximo_numero);
    return {row:{id:ticket,numero:f.proximo_numero,categoria:cat,status:'AGUARDANDO'},created:true};
  });
  const {row,created}=outcome;
  res.status(created?201:200).json({senha_id:row.id,numero:row.numero,categoria:row.categoria,status:row.status,
    token:issueToken({role:'CIDADAO',ticket_id:row.id,posto_id:id}),reutilizada:!created});
}));

app.get('/api/v1/senhas/:id',authenticate,route(async(req,res)=>{
  if(!isUuid(req.params.id))throw httpError(400,'UUID inválido');
  const r=await pool.query(`SELECT s.id,s.numero,s.categoria,s.status,s.posto_id,s.fila_id,s.guiche_id,
    p.media_atendimento_minutos,
    (SELECT COUNT(*)::int FROM guiches g WHERE g.posto_id=s.posto_id AND g.ativo) AS guiches_ativos
    FROM senhas s JOIN postos p ON p.id=s.posto_id WHERE s.id=$1`,[req.params.id]);
  if(!r.rowCount)throw httpError(404,'Senha inexistente');
  const s=r.rows[0],auth=req.auth;
  const canSee=(auth.role==='CIDADAO'&&auth.ticket_id===s.id)||(samePosto(auth,s.posto_id));
  if(!canSee)throw httpError(403,'Acesso negado à senha');
  let ahead=0;
  if(s.status==='AGUARDANDO'){
    const q=await pool.query(`SELECT COUNT(*)::int AS total FROM senhas WHERE fila_id=$1 AND status='AGUARDANDO'
      AND ( (categoria='PRIORITARIA' AND $2='NORMAL')
         OR (categoria=$2 AND numero<$3) )`,[s.fila_id,s.categoria,s.numero]);
    ahead=q.rows[0].total;
  }
  res.json({senha_id:s.id,numero:s.numero,categoria:s.categoria,status:s.status,posto_id:s.posto_id,
    guiche_id:s.guiche_id,posicao:s.status==='AGUARDANDO'?ahead+1:0,
    tempo_espera_minutos:s.status==='AGUARDANDO'?estimateMinutes(ahead,s.guiches_ativos,s.media_atendimento_minutos):0});
}));

app.post('/api/v1/guiches/:id/chamar',authenticate,route(async(req,res)=>{
  const id=intId(req.params.id);if(!id)throw httpError(400,'ID do guichê inválido');
  const result=await tx(async db=>{
    const desk=await db.query('SELECT id,posto_id FROM guiches WHERE id=$1 AND ativo=TRUE',[id]);
    if(!desk.rowCount)throw httpError(404,'Guichê inexistente ou inativo');
    const postoId=desk.rows[0].posto_id;
    if(!samePosto(req.auth,postoId))throw httpError(403,'Guichê fora do posto autorizado');
    const fila=await db.query('SELECT id FROM filas WHERE posto_id=$1 FOR UPDATE',[postoId]);
    const chosen=await db.query(`SELECT id,numero,categoria FROM senhas
      WHERE fila_id=$1 AND status='AGUARDANDO'
      ORDER BY CASE WHEN categoria='PRIORITARIA' THEN 0 ELSE 1 END,numero LIMIT 1`,[fila.rows[0].id]);
    if(!chosen.rowCount)throw httpError(409,'Fila vazia');
    const senha=chosen.rows[0];
    await db.query(`UPDATE senhas SET status='CHAMADA',guiche_id=$2,chamada_em=NOW() WHERE id=$1`,[senha.id,id]);
    await addEvent(db,postoId,senha.id,'SENHA_CHAMADA',req,senha.numero);
    return {...senha,status:'CHAMADA',guiche_id:id};
  });
  res.json(result);
}));

app.post('/api/v1/senhas/:id/finalizar',authenticate,route(async(req,res)=>{
  const id=req.params.id;if(!isUuid(id))throw httpError(400,'UUID inválido');
  const result=await tx(async db=>{
    const basic=await db.query('SELECT posto_id FROM senhas WHERE id=$1',[id]);
    if(!basic.rowCount)throw httpError(404,'Senha inexistente');
    const postoId=basic.rows[0].posto_id;
    if(!samePosto(req.auth,postoId))throw httpError(403,'Posto não autorizado');
    await db.query('SELECT id FROM filas WHERE posto_id=$1 FOR UPDATE',[postoId]);
    const current=await db.query('SELECT numero,status FROM senhas WHERE id=$1 FOR UPDATE',[id]);
    if(current.rows[0].status!=='CHAMADA')throw httpError(409,'Apenas senhas CHAMADA podem ser finalizadas');
    await db.query("UPDATE senhas SET status='FINALIZADA',finalizada_em=NOW() WHERE id=$1",[id]);
    await addEvent(db,postoId,id,'SENHA_FINALIZADA',req,current.rows[0].numero);
    return {senha_id:id,numero:current.rows[0].numero,status:'FINALIZADA'};
  });
  res.json(result);
}));

app.use((req,res)=>res.status(404).json({erro:'Rota não encontrada',correlation_id:req.correlationId}));
app.use((error,req,res,_next)=>{
  const status=error.status||(error.code==='23505'?409:503);
  log('error','request_failed',{status,error:error.message,correlation_id:req.correlationId});
  res.status(status).json({erro:error.status?error.message:'Falha no serviço',correlation_id:req.correlationId});
});

const server=http.createServer(app);
const wss=new WebSocketServer({noServer:true});
const clients=new Set();
server.on('upgrade',(req,socket,head)=>{
  try{
    if(new URL(req.url,'http://localhost').pathname!=='/ws')throw new Error('wrong_path');
    const token=bearer(req);
    const auth=verifyToken(token||'');
    if(!['CIDADAO','ATENDENTE'].includes(auth.role)||!Number.isInteger(auth.posto_id))throw new Error('wrong_role');
    wss.handleUpgrade(req,socket,head,ws=>wss.emit('connection',ws,auth));
  }catch{
    socket.write('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n');socket.destroy();
  }
});
wss.on('connection',(ws,auth)=>{
  const entry={ws,auth};clients.add(entry);
  ws.send(JSON.stringify({tipo:'CONECTADO',posto_id:auth.posto_id,node:process.env.HOSTNAME||'local'}));
  ws.on('close',()=>clients.delete(entry));
  ws.on('error',e=>log('warn','websocket_error',{error:e.message}));
});
function notify(event){
  if(!Number.isInteger(Number(event.posto_id)))return;
  for(const c of clients){
    if(c.ws.readyState===WebSocket.OPEN && c.auth.posto_id===Number(event.posto_id)){
      // Evento agregado: não expõe token nem identifica outros cidadãos.
      c.ws.send(JSON.stringify({tipo:'FILA_ATUALIZADA',posto_id:event.posto_id,
        evento:event.tipo,correlation_id:event.correlation_id,em:new Date().toISOString()}));
    }
  }
  log('info','websocket_forwarded',{event_id:event.event_id,correlation_id:event.correlation_id,recipients:clients.size});
}

async function start(){
  await loadAwsSecrets();
  if(!process.env.JWT_SECRET||process.env.JWT_SECRET.length<32||!process.env.STAFF_PASSWORD||process.env.STAFF_PASSWORD.length<12)
    throw new Error('JWT_SECRET (mínimo 32 caracteres) e STAFF_PASSWORD (mínimo 12) são obrigatórios');
  await pool.query('SELECT 1');
  const stopSubscriber=startSubscriber(notify);
  server.listen(3000,'0.0.0.0',()=>log('info','api_listening',{port:3000,node:process.env.HOSTNAME||'local'}));
  const stop=()=>{stopSubscriber();server.close(()=>pool.end().finally(()=>process.exit(0)))};
  process.on('SIGTERM',stop);process.on('SIGINT',stop);
}
start().catch(e=>{log('error','api_startup_failed',{error:e.message});process.exit(1)});
