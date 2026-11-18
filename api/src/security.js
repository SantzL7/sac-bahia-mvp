const crypto = require('node:crypto');
const jwt = require('jsonwebtoken');
function signingOptions() { return {algorithm:'HS256', issuer:'sac-bahia-mvp', audience:'sac-bahia-mvp', expiresIn:'2h'}; }
function issueToken(payload) { return jwt.sign(payload, process.env.JWT_SECRET, signingOptions()); }
function verifyToken(token) {
  return jwt.verify(token, process.env.JWT_SECRET, {algorithms:['HS256'],issuer:'sac-bahia-mvp',audience:'sac-bahia-mvp'});
}
function bearer(req) { const match=/^Bearer\s+(.+)$/i.exec(req.headers.authorization || '');return match?.[1] || null; }
function equalSecret(a,b) {
  const ab=Buffer.from(String(a ?? ''));const bb=Buffer.from(String(b ?? ''));
  return ab.length===bb.length && crypto.timingSafeEqual(ab,bb);
}
function authenticate(req,res,next) {
  try { const token=bearer(req);if(!token) return res.status(401).json({erro:'Autenticação necessária'});req.auth=verifyToken(token);next(); }
  catch { return res.status(401).json({erro:'Token inválido ou expirado'}); }
}
module.exports = {issueToken,verifyToken,bearer,equalSecret,authenticate};
