// Republica um evento ja persistido para testar a deduplicacao do consumidor.
const {Pool}=require('pg');
const amqp=require('amqplib');
(async()=>{
  const id=process.argv[2];
  if(!id)throw new Error('Informe o event_id');
  const pool=new Pool({connectionString:process.env.DATABASE_URL});
  try{
    const r=await pool.query('SELECT id,posto_id,senha_id,tipo,payload,correlation_id FROM eventos WHERE id=$1',[id]);
    if(!r.rowCount)throw new Error('Evento inexistente');
    const e=r.rows[0];
    const conn=await amqp.connect(process.env.AMQP_URL);
    const ch=await conn.createConfirmChannel();
    await ch.assertExchange('sac.events','topic',{durable:true});
    const payload=JSON.stringify({event_id:e.id,posto_id:e.posto_id,senha_id:e.senha_id,
      tipo:e.tipo,correlation_id:e.correlation_id,payload:e.payload});
    ch.publish('sac.events','senha.'+e.tipo.toLowerCase(),Buffer.from(payload),
      {persistent:true,contentType:'application/json',messageId:e.id,correlationId:e.correlation_id});
    await ch.waitForConfirms();
    console.log('Evento republicado: '+e.id+' tipo='+e.tipo);
    await ch.close();
    await conn.close();
  }finally{await pool.end();}
})().catch(e=>{console.error(e.message);process.exit(1)});
