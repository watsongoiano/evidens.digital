# Test Plan: HTTP 500 Error Fixes for Checkup Endpoints

## Overview
This test plan validates that the HTTP 500 errors in `/api/checkup` and `/checkup-intelligent` endpoints have been resolved through robust input parsing and error handling.

## Test Scenarios

### 1. Tabagismo Format Testing

#### 1.1 Object Format (Original)
**Input:**
```json
{
  "idade": 55,
  "sexo": "masculino", 
  "tabagismo": {"status": "fumante", "macos_ano": 25},
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 200 OK, tabagismo normalized to `fumante_atual` with `macos_ano=25`

#### 1.2 String Format 
**Input:**
```json
{
  "idade": 60,
  "sexo": "feminino",
  "tabagismo": "ex-fumante",
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 200 OK, tabagismo normalized to `ex_fumante` with `macos_ano=0`

#### 1.3 Flattened Fields Format
**Input:**
```json
{
  "idade": 45,
  "sexo": "masculino",
  "tabagismo_status": "fumante",
  "tabagismo_macos_ano": "30",
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 200 OK, tabagismo normalized to `fumante_atual` with `macos_ano=30`

#### 1.4 Mixed Format (Flattened Override)
**Input:**
```json
{
  "idade": 50,
  "sexo": "feminino",
  "tabagismo": {"status": "nunca_fumou"},
  "tabagismo_status": "ex-fumante",
  "tabagismo_macos_ano": "20",
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 200 OK, flattened fields override object (`ex_fumante`, `macos_ano=20`)

### 2. Date Format Testing

#### 2.1 Multiple Date Formats
**Input:**
```json
{
  "idade": 55,
  "sexo": "masculino",
  "tabagismo": "fumante_atual",
  "macos_ano": 25,
  "comorbidades": [],
  "historia_familiar": [],
  "exames_anteriores": [
    {"name": "HbA1c", "date": "2024-01-15"},      // YYYY-MM-DD
    {"name": "Mamografia", "date": "15/01/2024"}, // DD/MM/YYYY  
    {"name": "TC Tórax", "date": "2024/01/15"},   // YYYY/MM/DD
    {"name": "PSA", "date": "invalid_date"},      // Invalid
    {"name": "Colonoscopia"}                      // Missing date
  ]
}
```
**Expected:** 200 OK, all date formats parsed correctly, invalid dates handled gracefully

### 3. Edge Case Testing

#### 3.1 Null/Empty Data
**Input:**
```json
{
  "idade": 45,
  "sexo": "masculino", 
  "tabagismo": null,
  "macos_ano": null,
  "comorbidades": null,
  "historia_familiar": null,
  "exames_anteriores": null
}
```
**Expected:** 200 OK, safe defaults applied

#### 3.2 Invalid Data Types
**Input:**
```json
{
  "idade": "45",  // String instead of int
  "sexo": "masculino",
  "tabagismo": {"status": 123, "macos_ano": "invalid"},
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 200 OK, types converted safely

#### 3.3 Malformed Exam Data
**Input:**
```json
{
  "idade": 50,
  "sexo": "feminino",
  "tabagismo": "fumante",
  "comorbidades": [],
  "historia_familiar": [],
  "exames_anteriores": [
    "invalid_exam",  // String instead of dict
    {"name": "HbA1c"},  // Missing date
    {"date": "2024-01-15"},  // Missing name
    {"name": "Mamografia", "date": "not_a_date"},  // Invalid date
    {}  // Empty dict
  ]
}
```
**Expected:** 200 OK, malformed exams skipped safely

#### 3.4 Missing Required Fields
**Input:**
```json
{
  "tabagismo": "fumante",
  "comorbidades": [],
  "historia_familiar": []
}
```
**Expected:** 400 Bad Request (not 500), clear error message

## Manual Testing Steps

### Frontend Testing
1. **Open the application UI**
2. **Fill out the form with different tabagismo options:**
   - Select "Fumante" → should work
   - Select "Ex-fumante" → should work  
   - Select "Nunca fumou" → should work
3. **Upload PDF with different date formats**
4. **Submit form and verify:**
   - No "Erro HTTP: 500" message appears
   - Recommendations card loads successfully
   - Status chips (Devido/Em atraso/Recente) display correctly

### API Testing  
1. **Use curl or Postman to test endpoints:**

```bash
# Test /api/checkup endpoint
curl -X POST http://localhost:5000/api/checkup \
  -H "Content-Type: application/json" \
  -d '{"idade": 55, "sexo": "masculino", "tabagismo": {"status": "fumante", "macos_ano": 25}, "comorbidades": [], "historia_familiar": []}'

# Test /checkup-intelligent endpoint  
curl -X POST http://localhost:5000/checkup-intelligent \
  -H "Content-Type: application/json" \
  -d '{"idade": 55, "sexo": "masculino", "tabagismo_status": "ex-fumante", "tabagismo_macos_ano": "20", "comorbidades": [], "historia_familiar": []}'
```

2. **Verify responses:**
   - Status code 200 OK (not 500)
   - JSON response with recommendations array
   - Debug output shows normalized tabagismo values

## Expected Debug Output

When testing, you should see debug prints like:
```
DEBUG: tabagismo normalizado='fumante_atual', macos_ano=25
DEBUG: Verificando biomarqueurs - idade = 55
DEBUG: Idade válida para biomarqueurs (40-75)
```

## Success Criteria

✅ **All test scenarios return 200 OK or appropriate 4xx status codes**  
✅ **No HTTP 500 errors occur with any input combination**  
✅ **Tabagismo normalization works correctly for all formats**  
✅ **Date parsing handles multiple formats gracefully**  
✅ **Invalid/missing data handled with safe defaults**  
✅ **UI displays recommendations instead of error message**

## Regression Testing

Ensure existing functionality still works:
- Normal form submissions continue to work
- All recommendation types are still generated correctly
- Clinical logic and priorities remain unchanged
- CORS headers still applied correctly

This comprehensive testing confirms that the HTTP 500 errors have been eliminated while maintaining all existing functionality.