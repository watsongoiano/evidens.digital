# Plan d'Adaptation des Équations PREVENT

## Analyse des Données Actuelles vs Requises

### ✅ Données déjà disponibles dans notre système :
1. **Âge** - `id="idade"` ✅
2. **Sexe** - `id="sexo"` ✅
3. **Diabète** - `id="diabetes"` ✅
4. **Tabagisme** - `id="tabagismo"` ✅
5. **Médicaments** - `id="medicacoes_uso_continuo"` (texte libre) ⚠️

### ❌ Données manquantes à ajouter :
1. **Cholestérol total** (130-320 mg/dL)
2. **HDL cholestérol** (20-100 mg/dL)
3. **Pression artérielle systolique** (90-200 mmHg)
4. **IMC** ou Poids/Taille (18.5-40 kg/m²)
5. **Créatinine sérique** (pour calculer eGFR)
6. **Médicaments antihypertenseurs** (structure)
7. **Statines** (structure)

## Modifications à apporter au formulaire

### 1. Nouvelle section "Données Cliniques" à ajouter après l'âge/sexe :

```html
<div class="form-group">
    <h4>📊 Dados Clínicos</h4>
    
    <div class="form-row">
        <div>
            <label for="peso">Peso (kg)</label>
            <input type="number" id="peso" name="peso" min="30" max="300" step="0.1">
        </div>
        <div>
            <label for="altura">Altura (cm)</label>
            <input type="number" id="altura" name="altura" min="100" max="250" step="1">
        </div>
    </div>
    
    <div class="form-row">
        <div>
            <label for="pressao_sistolica">Pressão Arterial Sistólica (mmHg)</label>
            <input type="number" id="pressao_sistolica" name="pressao_sistolica" min="90" max="200">
        </div>
        <div>
            <label for="pressao_diastolica">Pressão Arterial Diastólica (mmHg)</label>
            <input type="number" id="pressao_diastolica" name="pressao_diastolica" min="50" max="120">
        </div>
    </div>
    
    <div class="form-row">
        <div>
            <label for="colesterol_total">Colesterol Total (mg/dL)</label>
            <input type="number" id="colesterol_total" name="colesterol_total" min="130" max="320">
        </div>
        <div>
            <label for="hdl_colesterol">HDL Colesterol (mg/dL)</label>
            <input type="number" id="hdl_colesterol" name="hdl_colesterol" min="20" max="100">
        </div>
    </div>
    
    <div class="form-row">
        <div>
            <label for="creatinina">Creatinina Sérica (mg/dL)</label>
            <input type="number" id="creatinina" name="creatinina" min="0.5" max="10" step="0.01">
        </div>
        <div>
            <label for="hemoglobina_glicada">HbA1c (%)</label>
            <input type="number" id="hemoglobina_glicada" name="hemoglobina_glicada" min="4" max="15" step="0.1">
        </div>
    </div>
</div>
```

### 2. Améliorer la section médicaments :

```html
<div class="form-group">
    <h4>💊 Medicações Específicas</h4>
    
    <div class="checkbox-group">
        <div class="checkbox-item">
            <input type="checkbox" id="medicamento_hipertensao" name="medicamentos_estruturados" value="anti_hipertensivo">
            <label for="medicamento_hipertensao">Medicamentos Anti-hipertensivos</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="medicamento_estatina" name="medicamentos_estruturados" value="estatina">
            <label for="medicamento_estatina">Estatinas</label>
        </div>
    </div>
</div>
```

## Algorithme de calcul PREVENT

### 1. Fonction de calcul eGFR (CKD-EPI 2021) :
```javascript
function calculateEGFR(creatinine, age, sex) {
    // Équation CKD-EPI 2021 sans race
    const isFemale = sex === 'feminino';
    const kappa = isFemale ? 0.7 : 0.9;
    const alpha = isFemale ? -0.241 : -0.302;
    const minCr = Math.min(creatinine / kappa, 1);
    const maxCr = Math.max(creatinine / kappa, 1);
    
    return 142 * Math.pow(minCr, alpha) * Math.pow(maxCr, -1.200) * Math.pow(0.9938, age) * (isFemale ? 1.012 : 1);
}
```

### 2. Fonction de calcul IMC :
```javascript
function calculateBMI(weight, height) {
    const heightM = height / 100;
    return weight / (heightM * heightM);
}
```

### 3. Fonction principale PREVENT :
```javascript
function calculatePREVENTRisk(patientData) {
    const {
        age, sex, totalCholesterol, hdlCholesterol, 
        systolicBP, diabetes, smoking, weight, height,
        creatinine, antihypertensiveMeds, statins
    } = patientData;
    
    // Calculs dérivés
    const bmi = calculateBMI(weight, height);
    const egfr = calculateEGFR(creatinine, age, sex);
    
    // Transformations des variables
    const ageTransformed = (age - 55) / 10;
    const nonHDLTransformed = (totalCholesterol - hdlCholesterol) * 0.02586 - 3.5;
    const hdlTransformed = (hdlCholesterol * 0.02586 - 1.3) / 0.3;
    const sbpLowTransformed = (Math.min(systolicBP, 110) - 110) / 20;
    const sbpHighTransformed = (Math.max(systolicBP, 110) - 130) / 20;
    const egfrLowTransformed = (Math.min(egfr, 60) - 60) / -15;
    const egfrHighTransformed = (Math.max(egfr, 60) - 90) / -15;
    
    // Calcul pour femmes et hommes
    const coefficients = getCoefficients(sex);
    
    let logOdds = coefficients.constant;
    logOdds += coefficients.age * ageTransformed;
    logOdds += coefficients.nonHDL * nonHDLTransformed;
    logOdds += coefficients.hdl * hdlTransformed;
    logOdds += coefficients.sbpLow * sbpLowTransformed;
    logOdds += coefficients.sbpHigh * sbpHighTransformed;
    logOdds += coefficients.diabetes * (diabetes ? 1 : 0);
    logOdds += coefficients.smoking * (smoking ? 1 : 0);
    logOdds += coefficients.egfrLow * egfrLowTransformed;
    logOdds += coefficients.egfrHigh * egfrHighTransformed;
    logOdds += coefficients.antihtn * (antihypertensiveMeds ? 1 : 0);
    logOdds += coefficients.statin * (statins ? 1 : 0);
    
    // Interactions
    logOdds += coefficients.ageNonHDL * ageTransformed * nonHDLTransformed;
    logOdds += coefficients.ageHDL * ageTransformed * hdlTransformed;
    logOdds += coefficients.ageSBP * ageTransformed * sbpHighTransformed;
    logOdds += coefficients.ageDiabetes * ageTransformed * (diabetes ? 1 : 0);
    logOdds += coefficients.ageSmoking * ageTransformed * (smoking ? 1 : 0);
    logOdds += coefficients.antihtnSBP * (antihypertensiveMeds ? 1 : 0) * sbpHighTransformed;
    logOdds += coefficients.statinNonHDL * (statins ? 1 : 0) * nonHDLTransformed;
    
    // Calcul du risque
    const risk = Math.exp(logOdds) / (1 + Math.exp(logOdds));
    
    return {
        risk10Year: risk * 100,
        risk30Year: calculateRisk30Year(patientData) // À implémenter
    };
}
```

## Interface visuelle

### Design des cartes de risque (basé sur le screenshot) :
```html
<div class="risk-cards">
    <div class="risk-card">
        <h3>Estimated 10-year<br>risk of CVD</h3>
        <div class="risk-percentage" id="risk-10-year">5.4%</div>
    </div>
    <div class="risk-card">
        <h3>Estimated 30-year<br>risk of CVD</h3>
        <div class="risk-percentage" id="risk-30-year">32.3%</div>
    </div>
</div>
```

### CSS pour le design :
```css
.risk-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 20px 0;
}

.risk-card {
    background: white;
    border-radius: 15px;
    padding: 25px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    border: 1px solid #e9ecef;
}

.risk-card h3 {
    font-size: 1.1rem;
    color: #2c3e50;
    margin-bottom: 15px;
    line-height: 1.3;
}

.risk-percentage {
    font-size: 3rem;
    font-weight: bold;
    color: #dc3545;
    margin: 10px 0;
}
```

## Prochaines étapes
1. ✅ Analyser les équations PREVENT
2. ✅ Identifier les données manquantes
3. 🔄 Modifier le formulaire HTML
4. 🔄 Implémenter l'algorithme JavaScript
5. 🔄 Créer l'interface visuelle
6. 🔄 Intégrer dans le flux de recommandations
7. 🔄 Tester et valider
8. 🔄 Déployer

