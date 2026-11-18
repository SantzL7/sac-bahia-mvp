function log(level, message, fields = {}) {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    service: process.env.SERVICE_NAME || 'unknown',
    instance: process.env.HOSTNAME || process.pid,
    message,
    ...fields
  };
  console.log(JSON.stringify(entry));
}
module.exports = { log };
