// Verificação opcional da leitura real de Secrets Manager com credenciais AWS locais.
const {SecretsManagerClient,GetSecretValueCommand}=require('@aws-sdk/client-secrets-manager');
(async()=>{
  if(!process.env.AWS_SECRET_ID)throw new Error('Defina AWS_SECRET_ID');
  const client=new SecretsManagerClient({region:process.env.AWS_REGION||'sa-east-1'});
  const result=await client.send(new GetSecretValueCommand({SecretId:process.env.AWS_SECRET_ID}));
  const parsed=JSON.parse(result.SecretString||'{}');
  if(!parsed.JWT_SECRET||!parsed.STAFF_PASSWORD)throw new Error('Segredo incompleto');
  console.log('OK: Secrets Manager acessível; chaves JWT_SECRET e STAFF_PASSWORD presentes.');
})().catch(e=>{console.error('Erro ao acessar o segredo:',e.message);process.exit(1)});
