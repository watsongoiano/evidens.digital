# Analyse des Équations PREVENT pour Calcul de Risque Cardiovasculaire

## Vue d'ensemble
Les équations PREVENT permettent de calculer le risque cardiovasculaire à 10 et 30 ans pour différents types d'événements :
- **Total CVD** : Risque cardiovasculaire total
- **ASCVD** : Maladie cardiovasculaire athérosclérotique
- **Heart Failure** : Insuffisance cardiaque

## Variables d'entrée requises
1. **Âge** (30-79 ans)
2. **Sexe** (Masculin/Féminin)
3. **Cholestérol total** (130-320 mg/dL)
4. **HDL cholestérol** (20-100 mg/dL)
5. **Pression artérielle systolique** (90-200 mmHg)
6. **Diabète** (Oui/Non)
7. **Tabagisme actuel** (Oui/Non)
8. **IMC** (18.5-40 kg/m²)
9. **eGFR** (15-150 mL/min/1.73m²)
10. **Médicaments antihypertenseurs** (Oui/Non)
11. **Statines** (Oui/Non)

## Formule générale
```
log-Odds = Constante + Σ(Coefficient × Variable transformée)
Risk = exp(log-Odds) / (1 + exp(log-Odds))
```

## Coefficients pour Total CVD 10 ans

### Femmes
- Constante : -3.307728
- Âge (par 10 ans) : 0.7939329
- non-HDL-C (par 1 mmol/L) : 0.0305239
- HDL-C (par 0.3 mmol/L) : -0.1606857
- SBP <110 (par 20 mmHg) : -0.2394003
- SBP ≥110 (par 20 mmHg) : 0.360078
- Diabète : 0.8667604
- Tabagisme : 0.5360739
- eGFR <60 : 0.6045917
- eGFR ≥60 : 0.0433769
- Médicaments HTA : 0.3151672
- Statines : -0.1477655

### Hommes
- Constante : -3.031168
- Âge (par 10 ans) : 0.7688528
- non-HDL-C (par 1 mmol/L) : 0.0736174
- HDL-C (par 0.3 mmol/L) : -0.0954431
- SBP <110 (par 20 mmHg) : -0.4347345
- SBP ≥110 (par 20 mmHg) : 0.3362658
- Diabète : 0.7692857
- Tabagisme : 0.4386871
- eGFR <60 : 0.5378979
- eGFR ≥60 : 0.0164827
- Médicaments HTA : 0.288879
- Statines : -0.1337349

## Transformations des variables
1. **Âge** : (âge - 55) / 10
2. **non-HDL-C** : (TC - HDL) × 0.02586 - 3.5
3. **HDL-C** : (HDL × 0.02586 - 1.3) / 0.3
4. **SBP <110** : (min(SBP, 110) - 110) / 20
5. **SBP ≥110** : (max(SBP, 110) - 130) / 20
6. **eGFR <60** : (min(eGFR, 60) - 60) / -15
7. **eGFR ≥60** : (max(eGFR, 60) - 90) / -15

## Interactions importantes
- Âge × non-HDL-C
- Âge × HDL-C
- Âge × SBP
- Âge × Diabète
- Âge × Tabagisme
- Médicaments HTA × SBP
- Statines × non-HDL-C

## Exemple de calcul
Pour une femme de 50 ans :
- TC: 200 mg/dL, HDL: 45 mg/dL
- SBP: 160 mmHg (traitée)
- Diabète: Oui
- Tabagisme: Non
- eGFR: 90 mL/min/1.73m²

**Résultat : 14.68% de risque CVD à 10 ans**

## Données disponibles dans notre système
Notre système de check-up médical collecte déjà :
- ✅ Âge
- ✅ Sexe
- ❌ Cholestérol total (à ajouter)
- ❌ HDL cholestérol (à ajouter)
- ❌ Pression artérielle (à ajouter)
- ✅ Diabète
- ❌ Tabagisme (à ajouter)
- ❌ IMC (à ajouter)
- ❌ eGFR (calculable à partir de la créatinine)
- ❌ Médicaments (partiellement disponible)

## Prochaines étapes
1. Ajouter les champs manquants au formulaire
2. Implémenter l'algorithme de calcul
3. Créer l'interface visuelle pour afficher les résultats
4. Intégrer dans le flux de recommandations

