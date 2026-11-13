import test from 'node:test';import assert from 'node:assert/strict';import {buildPrompt,consentValid,clean,makeManifest,POSES} from './core.mjs';
const consent={adult:true,permission:true,rights:true};const data={pose:'front',outfit:'Un costume bleu',scene:'Studio blanc',garmentMode:'imagined'};
test('all three consents are required',()=>{assert.equal(consentValid(consent),true);for(const key of Object.keys(consent))assert.equal(consentValid({...consent,[key]:false}),false);assert.equal(consentValid(null),false);assert.equal(consentValid({...consent,adult:'yes'}),false);});
test('prompt generation rejects missing consent',()=>assert.throws(()=>buildPrompt(data,{})));
test('prompt covers identity pose outfit scene limitations',()=>{const prompt=buildPrompt(data,consent);for(const word of ['IDENTITÉ','POSE','TENUE','SCÈNE','proportions','costume bleu','Studio blanc','prévisualisation'])assert.ok(prompt.includes(word));});
test('all curated poses produce a brief',()=>{for(const pose of Object.keys(POSES))assert.ok(buildPrompt({...data,pose},consent).includes(POSES[pose]));});
test('unknown pose rejected',()=>assert.throws(()=>buildPrompt({...data,pose:'x'},consent)));
test('blank fields rejected',()=>{for(const key of ['scene','outfit'])assert.throws(()=>buildPrompt({...data,[key]:'  '},consent));});
test('free text bounded',()=>assert.equal(clean('x'.repeat(2000)).length,1200));
test('invalid clean values safe',()=>{assert.equal(clean(undefined),'');assert.equal(clean(5),'');});
test('reference garment has distinct caveat',()=>assert.ok(buildPrompt({...data,garmentMode:'reference'},consent).includes('tombé exact')));
test('manifest excludes identifying free text',()=>{const m=makeManifest({...data,outfit:'SECRET',scene:'SECRET',subjectName:'SECRET',photo:'SECRET'},{identity:'pass'});assert.ok(!JSON.stringify(m).includes('SECRET'));assert.equal(m.generatedByThisApp,false);});
test('manifest review sanitization',()=>{const m=makeManifest({pose:'x'}, {identity:'hack',proportions:'fail',anatomy:'pass'});assert.equal(m.pose,'unknown');assert.equal(m.review.identity,'uncertain');assert.equal(m.review.proportions,'fail');assert.equal(m.review.anatomy,'pass');});

test('prototype names cannot become poses',()=>{for(const pose of ['constructor','toString','__proto__']){assert.throws(()=>buildPrompt({...data,pose},consent));assert.equal(makeManifest({pose},{}).pose,'unknown');}});
