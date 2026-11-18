// Injeção de mensagem malformada para demonstrar retries e DLQ.
const amqp=require('amqplib');
(async()=>{
  const conn=await amqp.connect(process.env.AMQP_URL);
  const ch=await conn.createConfirmChannel();
  await ch.assertExchange('sac.events','topic',{durable:true});
  await ch.assertQueue('sac.events.processing',{durable:true});
  await ch.bindQueue('sac.events.processing','sac.events','senha.*');
  ch.publish('sac.events','senha.teste',Buffer.from('{mensagem invalida'),{persistent:true,contentType:'application/json'});
  await ch.waitForConfirms();
  console.log('Mensagem inválida publicada. Aguarde retentativas e consulte sac.events.dlq no RabbitMQ.');
  await conn.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
