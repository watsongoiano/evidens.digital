// PREVENT 2024 Risk Calculator
// Based on AHA/ACC PREVENT equations

class PreventCalculator {
    constructor() {
        // Coeficientes para 10 anos - Total CVD
        this.coefficients_10yr = {
            women: {
                age_per_10yr: 0.7939329,
                non_hdl_per_mmol: 0.0305239,
                hdl_per_03mmol: -0.1606857,
                sbp_lt110_per_20: -0.2394003,
                sbp_gte110_per_20: 0.3600781,
                diabetes: 0.8667604,
                current_smoking: 0.5360739,
                egfr_lt60_per_neg15: 0.6045917,
                egfr_gte60_per_neg15: 0.0433769,
                antihtn_use: 0.3151672,
                statin_use: -0.1477655,
                treated_sbp_gte110_per_20: -0.0663612,
                treated_non_hdl: 0.1197879,
                age_x_non_hdl: -0.0819715,
                age_x_hdl: 0.0306769,
                age_x_sbp_gte110: -0.0946348,
                age_x_diabetes: -0.27057,
                age_x_smoking: -0.078715,
                age_x_egfr_lt60: -0.1637806,
                constant: -3.307728
            },
            men: {
                age_per_10yr: 0.7688528,
                non_hdl_per_mmol: 0.0736174,
                hdl_per_03mmol: -0.0954431,
                sbp_lt110_per_20: -0.4347345,
                sbp_gte110_per_20: 0.3362658,
                diabetes: 0.7692857,
                current_smoking: 0.4386871,
                egfr_lt60_per_neg15: 0.5378979,
                egfr_gte60_per_neg15: 0.0164827,
                antihtn_use: 0.288879,
                statin_use: -0.1337349,
                treated_sbp_gte110_per_20: -0.0475924,
                treated_non_hdl: 0.150273,
                age_x_non_hdl: -0.0517874,
                age_x_hdl: 0.0191169,
                age_x_sbp_gte110: -0.1049477,
                age_x_diabetes: -0.2251948,
                age_x_smoking: -0.0895067,
                age_x_egfr_lt60: -0.1543702,
                constant: -3.031168
            }
        };

        // Coeficientes para 30 anos - Total CVD
        this.coefficients_30yr = {
            women: {
                age_per_10yr: 0.5503079,
                age_squared: -0.09283769,
                non_hdl_per_mmol: 0.04097966,
                hdl_per_03mmol: 0.15113907,
                sbp_lt110_per_20: 0,
                sbp_gte110_per_20: 0.32995050,
                diabetes: 0.6793894,
                current_smoking: 0,
                bmi_lt30_per_5: 0,
                bmi_gte30_per_5: 0,
                egfr_lt60_per_neg15: 0,
                egfr_gte60_per_neg15: 0,
                antihtn_use: 0.2894,
                statin_use: 0,
                constant: -1.823
            },
            men: {
                age_per_10yr: 0.46273090,
                age_squared: -0.09842809,
                non_hdl_per_mmol: 0.08499671,
                hdl_per_03mmol: 0.09357667,
                sbp_lt110_per_20: 0,
                sbp_gte110_per_20: 0.29109750,
                diabetes: 0.5331276,
                current_smoking: 0,
                bmi_lt30_per_5: 0,
                bmi_gte30_per_5: 0,
                egfr_lt60_per_neg15: 0,
                egfr_gte60_per_neg15: 0,
                antihtn_use: 0.232714,
                statin_use: 0,
                constant: -1.823
            }
        };
    }

    // Converter mg/dL para mmol/L
    mgdlToMmol(mgdl) {
        return mgdl * 0.02586;
    }

    // Calcular eGFR usando CKD-EPI
    calculateEGFR(creatinina, idade, sexo, raca = 'other') {
        const kappa = sexo === 'feminino' ? 0.7 : 0.9;
        const alpha = sexo === 'feminino' ? -0.329 : -0.411;
        const min_cr_kappa = Math.min(creatinina / kappa, 1);
        const max_cr_kappa = Math.max(creatinina / kappa, 1);

        let egfr = 141 * Math.pow(min_cr_kappa, alpha) * Math.pow(max_cr_kappa, -1.209) * Math.pow(0.993, idade);

        if (sexo === 'feminino') {
            egfr *= 1.018;
        }

        return Math.round(egfr);
    }

    normalizeSmokingStatus(value) {
        if (value === undefined || value === null) {
            return 'nunca';
        }

        const sanitized = value
            .toString()
            .trim()
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[_\s]+/g, '-')
            .replace(/--+/g, '-');

        const mapping = {
            'nunca': 'nunca',
            'nunca-fumou': 'nunca',
            'nunca-fumei': 'nunca',
            'nunca-fumador': 'nunca',
            'nunca-fumadora': 'nunca',
            'never': 'nunca',
            'never-smoked': 'nunca',
            'never-smoker': 'nunca',
            'never-smoke': 'nunca',
            'nao': 'nunca',
            'na': 'nunca',
            'n-a': 'nunca',
            'none': 'nunca',
            'sem': 'nunca',
            'no': 'nunca',
            '0': 'nunca',
            'false': 'nunca',
            'fumante': 'fumante',
            'fumante-atual': 'fumante',
            'fumanteatual': 'fumante',
            'atual': 'fumante',
            'current': 'fumante',
            'current-smoker': 'fumante',
            'smoker': 'fumante',
            'smoking': 'fumante',
            'ex': 'ex-fumante',
            'ex-fumante': 'ex-fumante',
            'exfumante': 'ex-fumante',
            'ex-smoker': 'ex-fumante',
            'former': 'ex-fumante',
            'former-smoker': 'ex-fumante',
            'previous-smoker': 'ex-fumante',
            'former-smoke': 'ex-fumante'
        };

        if (mapping[sanitized]) {
            return mapping[sanitized];
        }

        if (sanitized.includes('ex') && sanitized.includes('fum')) {
            return 'ex-fumante';
        }

        if (['fumante', 'smoker', 'atual', 'current'].some((token) => sanitized.includes(token))) {
            return 'fumante';
        }

        return 'nunca';
    }

    isCurrentSmoker(value) {
        return this.normalizeSmokingStatus(value) === 'fumante';
    }

    // Calcular risco de 10 anos
    calculate10YearRisk(params) {
        const {
            idade, sexo, colesterol_total, hdl_colesterol, pressao_sistolica,
            diabetes, tabagismo, creatinina, medicamentos_anti_hipertensivos,
            estatinas, raca = 'other'
        } = params;

        // Calcular eGFR
        const egfr = this.calculateEGFR(creatinina, idade, sexo, raca);

        // Converter colesterol para mmol/L
        const tc_mmol = this.mgdlToMmol(colesterol_total);
        const hdl_mmol = this.mgdlToMmol(hdl_colesterol);
        const non_hdl_mmol = tc_mmol - hdl_mmol;

        // Selecionar coeficientes baseado no sexo
        const coeff = this.coefficients_10yr[sexo === 'feminino' ? 'women' : 'men'];

        // Calcular variáveis derivadas
        const age_centered = (idade - 55) / 10;
        const non_hdl_centered = non_hdl_mmol - 3.5;
        const hdl_centered = (hdl_mmol - 1.3) / 0.3;
        const sbp_lt110 = Math.min(pressao_sistolica, 110);
        const sbp_gte110 = Math.max(pressao_sistolica, 110);
        const sbp_lt110_term = (sbp_lt110 - 110) / 20;
        const sbp_gte110_term = (sbp_gte110 - 130) / 20;
        const egfr_lt60 = Math.min(egfr, 60);
        const egfr_gte60 = Math.max(egfr, 60);
        const egfr_lt60_term = (egfr_lt60 - 60) / -15;
        const egfr_gte60_term = (egfr_gte60 - 90) / -15;

        // Calcular log-odds
        let logOdds = coeff.constant;
        logOdds += coeff.age_per_10yr * age_centered;
        logOdds += coeff.non_hdl_per_mmol * non_hdl_centered;
        logOdds += coeff.hdl_per_03mmol * hdl_centered;
        logOdds += coeff.sbp_lt110_per_20 * sbp_lt110_term;
        logOdds += coeff.sbp_gte110_per_20 * sbp_gte110_term;
        logOdds += coeff.diabetes * (diabetes ? 1 : 0);
        const isCurrentSmoker = this.isCurrentSmoker(tabagismo);
        logOdds += coeff.current_smoking * (isCurrentSmoker ? 1 : 0);
        logOdds += coeff.egfr_lt60_per_neg15 * egfr_lt60_term;
        logOdds += coeff.egfr_gte60_per_neg15 * egfr_gte60_term;
        logOdds += coeff.antihtn_use * (medicamentos_anti_hipertensivos ? 1 : 0);
        logOdds += coeff.statin_use * (estatinas ? 1 : 0);

        // Termos de interação
        if (medicamentos_anti_hipertensivos && pressao_sistolica >= 110) {
            logOdds += coeff.treated_sbp_gte110_per_20 * sbp_gte110_term;
        }
        if (estatinas) {
            logOdds += coeff.treated_non_hdl * non_hdl_centered;
        }

        // Interações com idade
        logOdds += coeff.age_x_non_hdl * age_centered * non_hdl_centered;
        logOdds += coeff.age_x_hdl * age_centered * hdl_centered;
        logOdds += coeff.age_x_sbp_gte110 * age_centered * sbp_gte110_term;
        logOdds += coeff.age_x_diabetes * age_centered * (diabetes ? 1 : 0);
        logOdds += coeff.age_x_smoking * age_centered * (isCurrentSmoker ? 1 : 0);
        logOdds += coeff.age_x_egfr_lt60 * age_centered * egfr_lt60_term;

        // Converter log-odds para probabilidade
        const risk = 1 / (1 + Math.exp(-logOdds));
        
        return {
            risk: Math.round(risk * 1000) / 10, // Porcentagem com 1 casa decimal
            egfr: egfr
        };
    }

    // Calcular risco de 30 anos (simplificado)
    calculate30YearRisk(params) {
        const {
            idade, sexo, colesterol_total, hdl_colesterol, pressao_sistolica,
            diabetes, tabagismo, bmi, creatinina, medicamentos_anti_hipertensivos,
            estatinas
        } = params;

        // Para 30 anos, usar uma aproximação baseada no risco de 10 anos
        const risk10yr = this.calculate10YearRisk(params);
        
        // Fator de multiplicação baseado na idade (mais jovem = maior risco relativo a longo prazo)
        const ageFactor = idade < 50 ? 3.5 : idade < 60 ? 3.0 : 2.5;
        
        // Ajustar para fatores de risco adicionais
        let risk30yr = risk10yr.risk * ageFactor;
        
        // Limitar a 80% máximo
        risk30yr = Math.min(risk30yr, 80);
        
        return {
            risk: Math.round(risk30yr * 10) / 10,
            egfr: risk10yr.egfr
        };
    }

    // Função principal para calcular ambos os riscos
    calculateRisks(params) {
        const risk10yr = this.calculate10YearRisk(params);
        const risk30yr = this.calculate30YearRisk(params);
        
        return {
            risk_10yr: risk10yr.risk,
            risk_30yr: risk30yr.risk,
            egfr: risk10yr.egfr
        };
    }

    // Interpretar o nível de risco
    interpretRisk(risk10yr) {
        if (risk10yr < 5) {
            return { level: 'baixo', color: '#27ae60', description: 'Risco baixo' };
        } else if (risk10yr < 7.5) {
            return { level: 'borderline', color: '#f39c12', description: 'Risco borderline' };
        } else if (risk10yr < 20) {
            return { level: 'intermediario', color: '#e67e22', description: 'Risco intermediário' };
        } else {
            return { level: 'alto', color: '#e74c3c', description: 'Risco alto' };
        }
    }
}

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PreventCalculator;
} else {
    window.PreventCalculator = PreventCalculator;
}
