const {Pool}=require('pg');
const amqp=require('amqplib');
const {log}=require('../../shared/log');
process.env.SERVICE_NAME='worker';
const pool=new Pool({connectionString:process.env.DATABASE_URL,max:4,connectionTimeoutMillis:2500});
pool.on('error',e=>log('error','postgres_idle_error',{error:e.message}));
let conn=null, pub=null, sub=null, active=false, shutdown=false;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

class CircuitBreaker {
  constructor(){this.state='CLOSED';this.failures=0;this.openedAt=0;}
  check(){
    if(this.state==='OPEN'){
      if(Date.now()-this.openedAt<6000)throw Error('circuit_open');
      this.state='HALF_OPEN';log('warn','circuit_half_open');
    }
  }
  success(){if(this.state!=='CLOSED')log('info','circuit_closed');this.state='CLOSED';this.failures=0;}
  failure(){this.failures++;
    if(this.failures>=3||this.state==='HALF_OPEN'){
      if(this.state!=='OPEN')log('error','circuit_opened',{failures:this.failures});
      this.state='OPEN';this.openedAt=Date.now();
    }
  }
}
const breaker=new CircuitBreaker();

async function disconnect(){
  active=false;
  try{await pub?.close()}catch{}
  try{await sub?.close()}catch{}
  try{await conn?.close()}catch{}
  pub=null;sub=null;conn=null;
}
async function connect(){
  if(active)return;
  await disconnect();
  const connection=await amqp.connect(process.env.AMQP_URL,{timeout:3000});
  conn=connection;
  conn.on('error',e=>log('warn','rabbit_connection_error',{error:e.message}));
  conn.on('close',()=>{active=false;pub=null;sub=null;if(!shutdown)log('warn','rabbit_disconnected')});
  const publishing=await conn.createConfirmChannel();
  const consuming=await conn.createConfirmChannel();
  await publishing.assertExchange('sac.events','topic',{durable:true});
  await publishing.assertExchange('sac.notifications','fanout',{durable:true});
  await publishing.assertExchange('sac.dead','direct',{durable:true});
  await publishing.assertQueue('sac.events.processing',{durable:true});
  await publishing.bindQueue('sac.events.processing','sac.events','senha.*');
  await publishing.bindQueue('sac.events.processing','sac.events','retry');
  await publishing.assertQueue('sac.events.retry',{durable:true,
    arguments:{'x-message-ttl':3000,'x-dead-letter-exchange':'sac.events','x-dead-letter-routing-key':'retry'}});
  await publishing.assertQueue('sac.events.dlq',{durable:true});
  await publishing.bindQueue('sac.events.dlq','sac.dead','dead');
  await consuming.prefetch(5);
  pub=publishing;sub=consuming;active=true;
  await consuming.consume('sac.events.processing',msg=>{
    if(!msg)return;
    processMessage(msg).catch(e=>log('error','consumer_unexpected',{error:e.message}));
  },{noAck:false});
  log('info','rabbit_worker_connected');
}
function confirmPublish(channel,exchange,routingKey,payload,props={}){
  return new Promise((resolve,reject)=>{
    if(!channel) return reject(new Error('rabbit_channel_unavailable'));
    let settled=false;
    const timer=setTimeout(()=>{if(!settled){settled=true;reject(new Error('rabbit_publish_timeout'))}},2500);
    channel.publish(exchange,routingKey,Buffer.from(payload),{persistent:true,contentType:'application/json',...props},err=>{
      if(settled)return;
      settled=true;clearTimeout(timer);err?reject(err):resolve();
    });
  });
}
function confirmSend(channel,queue,payload,props={}){
  return new Promise((resolve,reject)=>{
    if(!channel)return reject(new Error('rabbit_channel_unavailable'));
    let settled=false;
    const timer=setTimeout(()=>{if(!settled){settled=true;reject(new Error('rabbit_publish_timeout'))}},2500);
    channel.sendToQueue(queue,Buffer.from(payload),{persistent:true,contentType:'application/json',...props},err=>{
      if(settled)return;settled=true;clearTimeout(timer);err?reject(err):resolve();
    });
  });
}

// Relay da outbox dentro do mesmo Worker. Uma transação por evento mantém o
// evento pendente se a publicação falhar; publisher confirm antes do commit.
async function relayOutbox(){
  breaker.check();
  let db=null;
  try{
    if(!active)await connect();
    db=await pool.connect();
    await db.query('BEGIN');
    const r=await db.query(`SELECT id,posto_id,senha_id,tipo,payload,correlation_id
      FROM eventos WHERE publicado_em IS NULL ORDER BY criado_em,id
      LIMIT 1 FOR UPDATE SKIP LOCKED`);
    if(!r.rowCount){await db.query('COMMIT');breaker.success();return false;}
    const e=r.rows[0];
    const payload=JSON.stringify({event_id:e.id,posto_id:e.posto_id,senha_id:e.senha_id,tipo:e.tipo,
      correlation_id:e.correlation_id,payload:e.payload});
    await confirmPublish(pub,'sac.events','senha.'+e.tipo.toLowerCase(),payload,
      {messageId:e.id,correlationId:e.correlation_id});
    await db.query('UPDATE eventos SET publicado_em=NOW(),tentativas=tentativas+1 WHERE id=$1',[e.id]);
    await db.query('COMMIT');
    breaker.success();
    log('info','event_published',{event_id:e.id,event_type:e.tipo,correlation_id:e.correlation_id});
    return true;
  }catch(e){if(db)await db.query('ROLLBACK').catch(()=>{});breaker.failure();throw e;}
  finally{db?.release();}
}
async function processMessage(msg){
  let event, correlationId=msg.properties.correlationId||null;
  try{
    event=JSON.parse(msg.content.toString('utf8'));
    if(!event.event_id||!event.correlation_id||!event.posto_id||!event.tipo)throw new Error('message_invalid');
    correlationId=event.correlation_id;
    // Transação de deduplicação: confirmar no banco somente depois da publicação.
    // Uma repetição pode gerar notificação duplicada se o commit falhar; cliente
    // reconcilia com REST, e a operação de negócio nunca é duplicada.
    const db=await pool.connect();
    let firstDelivery=false;
    try{
      await db.query('BEGIN');
      const r=await db.query(`INSERT INTO eventos_processados(evento_id)
        VALUES ($1) ON CONFLICT DO NOTHING RETURNING evento_id`,[event.event_id]);
      firstDelivery=Boolean(r.rowCount);
      if(firstDelivery){
        await confirmPublish(sub,'sac.notifications','',JSON.stringify({
          event_id:event.event_id,posto_id:event.posto_id,tipo:event.tipo,correlation_id:event.correlation_id,
        }),{messageId:event.event_id,correlationId:event.correlation_id});
      }
      await db.query('COMMIT');
    }catch(err){await db.query('ROLLBACK').catch(()=>{});throw err}
    finally{db.release()}
    sub.ack(msg);
    log('info',firstDelivery?'event_processed':'duplicate_ignored',{
      event_id:event.event_id,correlation_id:correlationId});
  }catch(e){
    const attempts=Number(msg.properties.headers?.attempts||0);
    try{
      if(attempts>=2){
        await confirmPublish(sub,'sac.dead','dead',msg.content.toString('utf8'),
          {headers:{attempts:attempts+1,reason:e.message},correlationId:correlationId||undefined});
        log('error','event_dead_letter',{error:e.message,attempts:attempts+1,correlation_id:correlationId});
      }else{
        await confirmSend(sub,'sac.events.retry',msg.content.toString('utf8'),
          {headers:{attempts:attempts+1},correlationId:correlationId||undefined});
        log('warn','event_retry_scheduled',{error:e.message,attempts:attempts+1,correlation_id:correlationId});
      }
      sub.ack(msg);
    }catch(republishError){
      log('error','retry_publish_failed',{error:republishError.message,correlation_id:correlationId});
      try{sub.nack(msg,false,true)}catch{}
    }
  }
}
async function run(){
  if(!process.env.DATABASE_URL||!process.env.AMQP_URL)throw new Error('DATABASE_URL e AMQP_URL obrigatórios');
  while(!shutdown){
    try{
      // Escoar eventos em lotes para não criar atrasos durante o teste de carga.
      for(let i=0;i<20&&!shutdown;i++){
        const wasPublished=await relayOutbox();
        if(!wasPublished)break;
      }
    }
    catch(e){log('warn','outbox_relay_retry',{error:e.message,breaker:breaker.state});}
    await sleep(750);
  }
}
async function stop(){shutdown=true;await disconnect();await pool.end();process.exit(0)}
process.on('SIGTERM',()=>stop().catch(()=>process.exit(1)));
process.on('SIGINT',()=>stop().catch(()=>process.exit(1)));
run().catch(e=>{log('error','worker_crashed',{error:e.message});process.exit(1)});
