import json
import sys

try:
    from src.main import app
except Exception as e:
    print(f"[SMOKE] Failed to import app from src.main: {e}")
    sys.exit(1)


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def run_smoke_tests():
    failures = 0
    with app.test_client() as client:
        # 1) /api/checkup
        payload_checkup = {
            "idade": 50,
            "sexo": "masculino",
            "comorbidades": ["hipertensao"],
        }
        resp = post_json(client, "/api/checkup", payload_checkup)
        if resp.status_code != 200:
            print(f"[SMOKE] /api/checkup status {resp.status_code}: {resp.data.decode('utf-8', 'ignore')}")
            failures += 1
        else:
            try:
                data = resp.get_json()
                assert isinstance(data, list)
                print(f"[SMOKE] /api/checkup OK - {len(data)} recomendações")
            except Exception as e:
                print(f"[SMOKE] /api/checkup invalid response: {e}")
                failures += 1

        # 2) /checkup-intelligent
        payload_intelligent = {
            "idade": 55,
            "sexo": "masculino",
            "pais": "BR",
            "comorbidades": ["hipertensao"],
            "historia_familiar": [],
            "tabagismo": "nunca_fumou",
            "macos_ano": 0,
            "outras_comorbidades": "",
            "outras_condicoes_familiares": "",
            "medicacoes_uso_continuo": "",
            "exames_anteriores": [],
        }
        resp = post_json(client, "/checkup-intelligent", payload_intelligent)
        if resp.status_code != 200:
            print(f"[SMOKE] /checkup-intelligent status {resp.status_code}: {resp.data.decode('utf-8', 'ignore')}")
            failures += 1
        else:
            try:
                data = resp.get_json()
                assert isinstance(data, dict)
                assert "recommendations" in data and isinstance(data["recommendations"], list)
                assert "alerts" in data and isinstance(data["alerts"], list)
                print(f"[SMOKE] /checkup-intelligent OK - {len(data['recommendations'])} recomendações, {len(data['alerts'])} alertas")
            except Exception as e:
                print(f"[SMOKE] /checkup-intelligent invalid response: {e}")
                failures += 1

        # 3) /analytics/stats
        resp = client.get("/analytics/stats")
        if resp.status_code != 200:
            print(f"[SMOKE] /analytics/stats status {resp.status_code}: {resp.data.decode('utf-8', 'ignore')}")
            failures += 1
        else:
            try:
                data = resp.get_json()
                assert isinstance(data, dict)
                # Accept either full keys or minimal mock
                if {"total", "today", "this_month"}.issubset(set(data.keys())):
                    print("[SMOKE] /analytics/stats OK - summary keys present")
                else:
                    print("[SMOKE] /analytics/stats OK - mock data")
            except Exception as e:
                print(f"[SMOKE] /analytics/stats invalid response: {e}")
                failures += 1

    if failures:
        print(f"[SMOKE] Completed with {failures} failure(s)")
        return 1
    print("[SMOKE] All checks passed ✔")
    return 0


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
