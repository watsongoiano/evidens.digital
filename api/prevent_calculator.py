#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PREVENT 2024 Cardiovascular Risk Calculator utilities."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class PreventCalculator:
    """Calculadora de risco cardiovascular baseada no modelo PREVENT 2024."""

    def __init__(self) -> None:
        # Coeficientes oficiais do modelo de 10 anos (Total CVD)
        self.coefficients_10yr: Dict[str, Dict[str, float]] = {
            "women": {
                "age_per_10yr": 0.7939329,
                "non_hdl_per_mmol": 0.0305239,
                "hdl_per_03mmol": -0.1606857,
                "sbp_lt110_per_20": -0.2394003,
                "sbp_gte110_per_20": 0.3600781,
                "diabetes": 0.8667604,
                "current_smoking": 0.5360739,
                "egfr_lt60_per_neg15": 0.6045917,
                "egfr_gte60_per_neg15": 0.0433769,
                "antihtn_use": 0.3151672,
                "statin_use": -0.1477655,
                "treated_sbp_gte110_per_20": -0.0663612,
                "treated_non_hdl": 0.1197879,
                "age_x_non_hdl": -0.0819715,
                "age_x_hdl": 0.0306769,
                "age_x_sbp_gte110": -0.0946348,
                "age_x_diabetes": -0.27057,
                "age_x_smoking": -0.078715,
                "age_x_egfr_lt60": -0.1637806,
                "constant": -3.307728,
            },
            "men": {
                "age_per_10yr": 0.7688528,
                "non_hdl_per_mmol": 0.0736174,
                "hdl_per_03mmol": -0.0954431,
                "sbp_lt110_per_20": -0.4347345,
                "sbp_gte110_per_20": 0.3362658,
                "diabetes": 0.7692857,
                "current_smoking": 0.4386871,
                "egfr_lt60_per_neg15": 0.5378979,
                "egfr_gte60_per_neg15": 0.0164827,
                "antihtn_use": 0.288879,
                "statin_use": -0.1337349,
                "treated_sbp_gte110_per_20": -0.0475924,
                "treated_non_hdl": 0.150273,
                "age_x_non_hdl": -0.0517874,
                "age_x_hdl": 0.0191169,
                "age_x_sbp_gte110": -0.1049477,
                "age_x_diabetes": -0.2251948,
                "age_x_smoking": -0.0895067,
                "age_x_egfr_lt60": -0.1543702,
                "constant": -3.031168,
            },
        }

        self.color_map = {
            "Baixo": "#27ae60",
            "Borderline": "#f1c40f",
            "Intermediário": "#e67e22",
            "Alto": "#e74c3c",
        }

    # ------------------------------------------------------------------
    # Helpers de parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(float(text.replace(",", ".")))
        except ValueError:
            return None

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    # ------------------------------------------------------------------
    # Utilidades do modelo
    # ------------------------------------------------------------------
    @staticmethod
    def mgdl_to_mmol(mgdl: float) -> float:
        return float(mgdl) * 0.02586

    @staticmethod
    def calculate_egfr(creatinine: float, idade: int, sexo: str, raca: str = "other") -> int:
        kappa = 0.7 if sexo == "feminino" else 0.9
        alpha = -0.329 if sexo == "feminino" else -0.411

        ratio = creatinine / kappa if kappa else 0
        min_ratio = min(ratio, 1)
        max_ratio = max(ratio, 1)

        egfr = 141 * (min_ratio ** alpha) * (max_ratio ** -1.209) * (0.993 ** idade)
        if sexo == "feminino":
            egfr *= 1.018

        return int(round(egfr))

    @staticmethod
    def normalize_smoking_status(value: Any) -> str:
        if value is None:
            return "nunca"

        sanitized = (
            str(value)
            .strip()
            .lower()
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("ú", "u")
            .replace("ü", "u")
            .replace(" ", "-")
            .replace("_", "-")
        )

        mapping = {
            "nunca": "nunca",
            "nunca-fumou": "nunca",
            "nunca-fumei": "nunca",
            "nunca-fumador": "nunca",
            "nunca-fumadora": "nunca",
            "never": "nunca",
            "never-smoker": "nunca",
            "never-smoked": "nunca",
            "nao": "nunca",
            "no": "nunca",
            "0": "nunca",
            "false": "nunca",
            "fumante": "fumante",
            "fumante-atual": "fumante",
            "fumanteatual": "fumante",
            "atual": "fumante",
            "current": "fumante",
            "current-smoker": "fumante",
            "smoker": "fumante",
            "smoking": "fumante",
            "ex": "ex-fumante",
            "ex-fumante": "ex-fumante",
            "exfumante": "ex-fumante",
            "ex-smoker": "ex-fumante",
            "former": "ex-fumante",
            "former-smoker": "ex-fumante",
            "former-smoke": "ex-fumante",
        }

        if sanitized in mapping:
            return mapping[sanitized]

        if "ex" in sanitized and "fum" in sanitized:
            return "ex-fumante"

        if any(token in sanitized for token in ("fumante", "smoker", "current", "atual")):
            return "fumante"

        return "nunca"

    def is_current_smoker(self, value: Any) -> bool:
        return self.normalize_smoking_status(value) == "fumante"

    # ------------------------------------------------------------------
    # Cálculo dos riscos
    # ------------------------------------------------------------------
    def calculate_10_year_risk(self, params: Dict[str, Any]) -> Dict[str, float]:
        idade = float(params.get("idade", 0))
        sexo = params.get("sexo", "masculino")
        colesterol_total = float(params.get("colesterol_total", 0))
        hdl_colesterol = float(params.get("hdl_colesterol", 0))
        pressao_sistolica = float(params.get("pressao_sistolica", 0))
        diabetes = bool(params.get("diabetes", False))
        tabagismo = params.get("tabagismo")
        creatinina = float(params.get("creatinina", 0))
        antihtn = bool(params.get("medicamentos_anti_hipertensivos", False))
        estatinas = bool(params.get("estatinas", False))

        egfr = self.calculate_egfr(creatinina, int(idade), sexo)

        total_mmol = self.mgdl_to_mmol(colesterol_total)
        hdl_mmol = self.mgdl_to_mmol(hdl_colesterol)
        non_hdl_mmol = total_mmol - hdl_mmol

        coeff = self.coefficients_10yr["women" if sexo == "feminino" else "men"]

        age_centered = (idade - 55) / 10
        non_hdl_centered = non_hdl_mmol - 3.5
        hdl_centered = (hdl_mmol - 1.3) / 0.3

        sbp_lt110 = min(pressao_sistolica, 110)
        sbp_gte110 = max(pressao_sistolica, 110)
        sbp_lt110_term = (sbp_lt110 - 110) / 20
        sbp_gte110_term = (sbp_gte110 - 130) / 20

        egfr_lt60 = min(egfr, 60)
        egfr_gte60 = max(egfr, 60)
        egfr_lt60_term = (egfr_lt60 - 60) / -15
        egfr_gte60_term = (egfr_gte60 - 90) / -15

        log_odds = coeff["constant"]
        log_odds += coeff["age_per_10yr"] * age_centered
        log_odds += coeff["non_hdl_per_mmol"] * non_hdl_centered
        log_odds += coeff["hdl_per_03mmol"] * hdl_centered
        log_odds += coeff["sbp_lt110_per_20"] * sbp_lt110_term
        log_odds += coeff["sbp_gte110_per_20"] * sbp_gte110_term
        log_odds += coeff["diabetes"] * (1 if diabetes else 0)

        is_smoker = self.is_current_smoker(tabagismo)
        log_odds += coeff["current_smoking"] * (1 if is_smoker else 0)
        log_odds += coeff["egfr_lt60_per_neg15"] * egfr_lt60_term
        log_odds += coeff["egfr_gte60_per_neg15"] * egfr_gte60_term
        log_odds += coeff["antihtn_use"] * (1 if antihtn else 0)
        log_odds += coeff["statin_use"] * (1 if estatinas else 0)

        if antihtn and pressao_sistolica >= 110:
            log_odds += coeff["treated_sbp_gte110_per_20"] * sbp_gte110_term
        if estatinas:
            log_odds += coeff["treated_non_hdl"] * non_hdl_centered

        log_odds += coeff["age_x_non_hdl"] * age_centered * non_hdl_centered
        log_odds += coeff["age_x_hdl"] * age_centered * hdl_centered
        log_odds += coeff["age_x_sbp_gte110"] * age_centered * sbp_gte110_term
        log_odds += coeff["age_x_diabetes"] * age_centered * (1 if diabetes else 0)
        log_odds += coeff["age_x_smoking"] * age_centered * (1 if is_smoker else 0)
        log_odds += coeff["age_x_egfr_lt60"] * age_centered * egfr_lt60_term

        risk = 1 / (1 + math.exp(-log_odds))
        return {
            "risk": round(risk * 1000) / 10,
            "egfr": egfr,
            "non_hdl_mmol": non_hdl_mmol,
        }

    def calculate_30_year_risk(
        self, params: Dict[str, Any], risk_10yr: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        if risk_10yr is None:
            risk_10yr = self.calculate_10_year_risk(params)

        idade = float(params.get("idade", 0))
        age_factor = 3.5 if idade < 50 else 3.0 if idade < 60 else 2.5

        risk30 = min(risk_10yr["risk"] * age_factor, 80)
        return {
            "risk": round(risk30 * 10) / 10,
            "egfr": risk_10yr["egfr"],
        }

    def calculate_risks(self, params: Dict[str, Any]) -> Dict[str, float]:
        risk_10 = self.calculate_10_year_risk(params)
        risk_30 = self.calculate_30_year_risk(params, risk_10)
        return {
            "risk_10yr": risk_10["risk"],
            "risk_30yr": risk_30["risk"],
            "egfr": risk_10["egfr"],
            "non_hdl_mmol": risk_10["non_hdl_mmol"],
        }

    # ------------------------------------------------------------------
    # Classificação e recomendações
    # ------------------------------------------------------------------
    def classify_risk(self, risk_10yr: float, risk_30yr: float, idade: int) -> Dict[str, str]:
        if idade < 40:
            if risk_30yr < 15:
                category = "Baixo"
            elif risk_30yr < 30:
                category = "Borderline"
            elif risk_30yr < 45:
                category = "Intermediário"
            else:
                category = "Alto"
        else:
            if risk_10yr < 5:
                category = "Baixo"
            elif risk_10yr < 7.5:
                category = "Borderline"
            elif risk_10yr < 20:
                category = "Intermediário"
            else:
                category = "Alto"

        return {
            "category": category,
            "color": self.color_map.get(category, "#95a5a6"),
            "description": self._get_risk_description(category),
        }

    @staticmethod
    def _get_risk_description(category: str) -> str:
        descriptions = {
            "Baixo": "Risco cardiovascular baixo. Manter estilo de vida saudável.",
            "Borderline": "Risco cardiovascular limítrofe. Considerar intervenções preventivas.",
            "Intermediário": "Risco cardiovascular intermediário. Recomendadas medidas preventivas.",
            "Alto": "Risco cardiovascular alto. Intervenção médica intensiva recomendada.",
        }
        return descriptions.get(category, "")

    def _get_risk_based_recommendations(self, risk_category: str) -> List[str]:
        recommendations = {
            "Baixo": [
                "Manter estilo de vida saudável",
                "Atividade física regular",
                "Dieta balanceada",
                "Controle do peso",
            ],
            "Borderline": [
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Índice tornozelo-braquial (ITB)",
                "Modificações do estilo de vida intensivas",
            ],
            "Intermediário": [
                "Score de Cálcio Coronariano (Angio-TC)",
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Índice tornozelo-braquial (ITB)",
                "Considerar estatina",
            ],
            "Alto": [
                "Score de Cálcio Coronariano (Angio-TC)",
                "Strain longitudinal global (Ecocardiograma)",
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Estatina de alta intensidade",
                "Controle rigoroso da pressão arterial",
            ],
        }
        return recommendations.get(risk_category, [])

    # ------------------------------------------------------------------
    # Interface principal
    # ------------------------------------------------------------------
    def calculate_prevent_score(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        idade = self._parse_int(patient_data.get("idade"))
        sexo_raw = (patient_data.get("sexo") or "masculino").strip().lower()
        sexo = "feminino" if sexo_raw.startswith("f") else "masculino"

        colesterol_total = self._parse_float(
            patient_data.get("colesterol_total") or patient_data.get("colesterol")
        )
        hdl_colesterol = self._parse_float(
            patient_data.get("hdl_colesterol") or patient_data.get("hdl")
        )
        pressao_sistolica = self._parse_float(
            patient_data.get("pressao_sistolica")
            or patient_data.get("pas")
            or patient_data.get("pressao")
        )
        creatinina = self._parse_float(patient_data.get("creatinina"))

        if None in (idade, sexo, colesterol_total, hdl_colesterol, pressao_sistolica, creatinina):
            return {
                "success": False,
                "error": "Dados insuficientes para calcular o risco PREVENT.",
            }

        peso = self._parse_float(patient_data.get("peso"))
        altura = self._parse_float(patient_data.get("altura"))
        bmi = None
        if peso and altura:
            altura_m = altura / 100
            if altura_m > 0:
                bmi = round(peso / (altura_m**2), 1)

        tabagismo = self.normalize_smoking_status(patient_data.get("tabagismo"))

        comorbidades = [c.lower() for c in self._ensure_list(patient_data.get("comorbidades"))]
        diabetes_flag = "diabetes" in comorbidades
        diabetes_flag = diabetes_flag or str(patient_data.get("diabetes_tipo2") or "").lower() in {
            "on",
            "true",
            "1",
            "sim",
            "yes",
        }
        diabetes_flag = diabetes_flag or str(patient_data.get("diabetes") or "").lower() in {
            "on",
            "true",
            "1",
            "sim",
            "yes",
        }

        medicacoes_raw: List[str] = []
        medicacoes_raw.extend(self._ensure_list(patient_data.get("medicacoes")))
        medicacoes_raw.extend(self._ensure_list(patient_data.get("medicacoes_especificas")))

        medicacoes = [m.lower() for m in medicacoes_raw]
        antihtn_use = any("anti" in m and "hipertens" in m for m in medicacoes)
        statin_use = any("estat" in m or "statin" in m for m in medicacoes)

        risk_params: Dict[str, Any] = {
            "idade": idade,
            "sexo": sexo,
            "colesterol_total": colesterol_total,
            "hdl_colesterol": hdl_colesterol,
            "pressao_sistolica": pressao_sistolica,
            "diabetes": diabetes_flag,
            "tabagismo": tabagismo,
            "creatinina": creatinina,
            "medicamentos_anti_hipertensivos": antihtn_use,
            "estatinas": statin_use,
        }

        risks = self.calculate_risks(risk_params)
        risk_10yr = risks["risk_10yr"]
        risk_30yr = risks["risk_30yr"]

        classification = self.classify_risk(risk_10yr, risk_30yr, idade)

        non_hdl = None
        if colesterol_total is not None and hdl_colesterol is not None:
            non_hdl = round(colesterol_total - hdl_colesterol, 1)

        clinical_data = {
            "egfr": risks["egfr"],
            "bmi": bmi,
            "non_hdl": non_hdl,
            "pressao_sistolica": pressao_sistolica,
            "tabagismo": tabagismo,
        }

        return {
            "success": True,
            "risk_10yr": risk_10yr,
            "risk_30yr": risk_30yr,
            "classification": classification,
            "clinical_data": clinical_data,
            "recommendations": self._get_risk_based_recommendations(classification["category"]),
        }


def calculate_prevent_risk(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    calculator = PreventCalculator()
    return calculator.calculate_prevent_score(patient_data)


if __name__ == "__main__":
    import json

    example = {
        "idade": 55,
        "sexo": "masculino",
        "peso": 82,
        "altura": 178,
        "pressao_sistolica": 140,
        "colesterol_total": 220,
        "hdl_colesterol": 45,
        "creatinina": 1.0,
        "comorbidades": ["hipertensao"],
        "tabagismo": "fumante",
        "medicacoes": ["anti_hipertensivos"],
    }

    print(json.dumps(calculate_prevent_risk(example), indent=2, ensure_ascii=False))
