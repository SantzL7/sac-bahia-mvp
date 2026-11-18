const amqp = require('amqplib');
const {log}=require('../../shared/log');
function startSubscriber(onEvent){
  let stopped=false;
  let conn=null;
  async function loop(){
    if(stopped)return;
    try {
      conn=await amqp.connect(process.env.AMQP_URL, {timeout:3000});
      conn.on('error', e=>log('warn','rabbit_connection_error',{error:e.message}));
      conn.on('close',()=>{if(!stopped){log('warn','rabbit_disconnected');setTimeout(loop,3000)}});
      const ch=await conn.createChannel();
      await ch.assertExchange('sac.notifications','fanout',{durable:true});
      const q=await ch.assertQueue('',{exclusive:true,autoDelete:true});
      await ch.bindQueue(q.queue,'sac.notifications','');
      await ch.consume(q.queue,(msg)=>{
        if(!msg)return;
        try {const event=JSON.parse(msg.content.toString('utf8'));onEvent(event);ch.ack(msg);}
        catch(e){log('error','notification_invalid',{error:e.message});ch.ack(msg);}
      });
      log('info','rabbit_subscribed',{queue:q.queue});
    }catch(e){log('warn','rabbit_subscribe_retry',{error:e.message});try{await conn?.close()}catch{};setTimeout(loop,3000)}
  }
  loop();
  return ()=>{stopped=true;conn?.close().catch(()=>{});};
}
module.exports={startSubscriber};
