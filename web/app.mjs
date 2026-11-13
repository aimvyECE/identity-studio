import {buildPrompt,consentValid,makeManifest} from './core.mjs';
const $=id=>document.getElementById(id), urls=new Map(), versions=new Map(), loaded=new Set();
const consent=()=>Object.fromEntries(['adult','permission','rights'].map(k=>[k,$(k).checked]));
const input=()=>Object.fromEntries(['pose','garmentMode','outfit','scene'].map(k=>[k,$(k).value]));
function status(text){$('status').textContent=text;}
function resetReview(){for(const el of document.querySelectorAll('[data-review]'))el.value='uncertain';}
function invalidate(){ $('prompt').value=''; $('copy').disabled=true; }
function controls(){ $('export').disabled=!(consentValid(consent())&&loaded.has('subject')&&loaded.has('result')); }
function clearImage(key, targets){loaded.delete(key); if(urls.has(key)){URL.revokeObjectURL(urls.get(key));urls.delete(key);} for(const id of targets){const node=$(id);node.replaceChildren();node.classList.add('empty');node.textContent=key==='result'?'Aucun résultat':'Aucune référence';} controls();}
async function loadFile(file,key,targets){
 const version=(versions.get(key)||0)+1;versions.set(key,version);clearImage(key,targets);invalidate();resetReview();
 if(!file){status('Image retirée.');return;}
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>15*1024*1024){status('Choisis un JPG, PNG ou WebP de 15 Mo maximum.');return;}
 const url=URL.createObjectURL(file);const img=new Image();img.src=url;
 try{await img.decode(); if(versions.get(key)!==version){URL.revokeObjectURL(url);return;} if(img.naturalWidth*img.naturalHeight>40_000_000)throw new Error('Image trop grande');
 urls.set(key,url);loaded.add(key);for(const id of targets){const copy=new Image();copy.src=url;copy.alt=key==='result'?'Résultat importé à vérifier':key==='garment'?'Vêtement de référence':'Sujet de référence';$(id).replaceChildren(copy);$(id).classList.remove('empty');}status('Image chargée localement, sans envoi.');controls();
 }catch{URL.revokeObjectURL(url);if(versions.get(key)===version)status('Image illisible ou trop grande (maximum 40 mégapixels).');}
}
$('subjectFile').addEventListener('change',e=>loadFile(e.target.files[0],'subject',['subjectThumb','referenceView']));
$('resultFile').addEventListener('change',e=>loadFile(e.target.files[0],'result',['resultView']));
$('garmentFile').addEventListener('change',e=>loadFile(e.target.files[0],'garment',['garmentThumb']));
for(const id of ['pose','garmentMode','outfit','scene']) $(id).addEventListener('input',()=>{invalidate();resetReview(); if(id==='garmentMode'){const enabled=$(id).value==='reference';$('garmentUpload').hidden=!enabled;$('garmentThumb').hidden=!enabled;}});
$('consents').addEventListener('change',()=>{invalidate();resetReview();controls();});
$('build').addEventListener('click',()=>{try{if(!loaded.has('subject'))throw new Error('Ajoute d’abord une photo de référence.');if($('garmentMode').value==='reference'&&!loaded.has('garment'))throw new Error('Ajoute la photo du vêtement ou choisis une tenue imaginée.');$('prompt').value=buildPrompt(input(),consent());$('copy').disabled=false;status('Brief préparé. Vérifie-le avant de le transmettre à un autre service.');}catch(e){invalidate();status(e.message);}});
$('copy').addEventListener('click',async()=>{if(!consentValid(consent())||!$('prompt').value)return;try{await navigator.clipboard.writeText($('prompt').value);status('Brief copié. Les photos ne sont pas copiées : joins-les seulement si tu le souhaites.');}catch{$('prompt').focus();$('prompt').select();status('Copie automatique indisponible : le texte est sélectionné, copie-le manuellement.');}});
$('export').addEventListener('click',()=>{if(!consentValid(consent())||!loaded.has('subject')||!loaded.has('result'))return;const review=Object.fromEntries([...document.querySelectorAll('[data-review]')].map(el=>[el.dataset.review,el.value]));const blob=new Blob([JSON.stringify(makeManifest(input(),review),null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='identity-studio-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('Bilan exporté sans photos, noms de fichiers ni textes libres.');});
$('reset').addEventListener('click',()=>{for(const key of ['subject','garment','result'])versions.set(key,(versions.get(key)||0)+1);for(const url of urls.values())URL.revokeObjectURL(url);urls.clear();loaded.clear();for(const el of document.querySelectorAll('input')){if(el.type==='checkbox')el.checked=false;else el.value='';}for(const el of document.querySelectorAll('select'))el.selectedIndex=0;$('outfit').value='';$('scene').value='Studio gris clair, lumière diffuse latérale, cadrage plein pied, perspective naturelle.';clearImage('subject',['subjectThumb','referenceView']);clearImage('garment',['garmentThumb']);clearImage('result',['resultView']);$('garmentUpload').hidden=true;$('garmentThumb').hidden=true;invalidate();status('Session effacée de cet onglet. Les fichiers téléchargés auparavant restent sur ton ordinateur.');});
window.addEventListener('pagehide',event=>{if(!event.persisted)for(const url of urls.values())URL.revokeObjectURL(url);});
