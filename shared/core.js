const { createHash } = require('node:crypto');
function validCategory(value) { return value === 'NORMAL' || value === 'PRIORITARIA'; }
function requestHash(postoId, categoria) {
  return createHash('sha256').update(JSON.stringify({posto_id: Number(postoId), categoria})).digest('hex');
}
function estimateMinutes(ahead, activeDesks, avgMinutes) {
  if (!Number.isInteger(activeDesks) || activeDesks < 1) return null;
  return Math.ceil((Math.max(0, ahead) * avgMinutes) / activeDesks);
}
function samePosto(token, postoId) { return token && token.role === 'ATENDENTE' && token.posto_id === Number(postoId); }
module.exports = { validCategory, requestHash, estimateMinutes, samePosto };
