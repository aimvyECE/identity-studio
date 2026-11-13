export const POSES = { front: 'Debout de face, posture naturelle, bras relâchés, corps entier visible.', quarter: 'Debout de trois-quarts, tête vers la caméra, mains visibles.', profile: 'Debout de profil, silhouette complète, tête dans le même axe.', seated: 'Assis sur un tabouret, pieds au sol, mains sur les genoux.' };
export function clean(value, max=1200) { return typeof value === 'string' ? value.trim().slice(0,max) : ''; }
export function consentValid(consent) { return !!consent && ['adult','permission','rights'].every(k=>consent[k] === true); }
export function buildPrompt(input, consent) {
  if (!consentValid(consent)) throw new Error('Valide les trois engagements avant de préparer le brief.');
  const pose = Object.hasOwn(POSES,input.pose) ? POSES[input.pose] : null;
  if (!pose) throw new Error('Pose non reconnue.');
  const outfit=clean(input.outfit), scene=clean(input.scene);
  if (!outfit || !scene) throw new Error('Décris une tenue et une scène.');
  return `Créer un visuel de mode non explicite à partir de la photographie de référence jointe. Le sujet est adulte et son utilisation est autorisée.\n\nIDENTITÉ À PRÉSERVER\nPréserver au mieux le visage, les proportions corporelles et les caractéristiques visibles du sujet de référence. Ne pas embellir, amincir, rajeunir ou modifier volontairement sa morphologie. Ne pas inventer une fidélité parfaite pour les parties non visibles.\n\nPOSE\n${pose}\n\nTENUE\n${outfit}\n${input.garmentMode === 'reference' ? 'Un vêtement de référence est fourni séparément : préserver autant que possible coupe, couleurs et motifs. Signaler les écarts ; ce rendu ne prouve ni la taille réelle ni le tombé exact.' : 'Tenue imaginée : ne pas présenter le résultat comme la reproduction fidèle d’un produit commercial.'}\n\nSCÈNE\n${scene}\n\nQUALITÉ\nAnatomie plausible, mains et articulations cohérentes, ombres compatibles avec la scène. Sans texte ajouté ni signature. Produire une image de prévisualisation, à contrôler humainement ; ne pas affirmer qu’il s’agit d’une photographie réelle.`;
}
export function makeManifest(input, review) {
  return {schema:'identity-studio.review.v1',mode:'manual-review',generatedByThisApp:false,pose: Object.hasOwn(POSES,input.pose) ? input.pose : 'unknown',garmentMode:input.garmentMode==='reference'?'reference':'imagined',review:Object.fromEntries(['identity','proportions','anatomy','garment','scene','pose'].map(k=>[k,['pass','uncertain','fail'].includes(review[k])?review[k]:'uncertain'])),limitations:['Human visual review, not biometric verification.','No guarantee of identity fidelity or garment fit.'],privacy:'No photos, filenames, free-text brief, subject identity or image metadata included.'};
}
