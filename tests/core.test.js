const test = require('node:test');
const assert = require('node:assert/strict');
const {validCategory,requestHash,estimateMinutes,samePosto}=require('../shared/core');
test('categorias aceitas exatamente',()=>{assert.equal(validCategory('NORMAL'),true);assert.equal(validCategory('PRIORITARIA'),true);assert.equal(validCategory('VIP'),false)});
test('hash de idempotência distingue categoria',()=>{assert.equal(requestHash(1,'NORMAL'),requestHash('1','NORMAL'));assert.notEqual(requestHash(1,'NORMAL'),requestHash(1,'PRIORITARIA'))});
test('ETA não inventa estimativa sem guichê',()=>{assert.equal(estimateMinutes(5,0,8),null);assert.equal(estimateMinutes(5,2,8),20);assert.equal(estimateMinutes(0,1,7),0)});
test('atendente só opera posto autorizado',()=>{assert.equal(samePosto({role:'ATENDENTE',posto_id:2},2),true);assert.equal(samePosto({role:'ATENDENTE',posto_id:2},1),false);assert.equal(samePosto({role:'CIDADAO',posto_id:2},2),false)});
