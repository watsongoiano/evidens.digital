# Análise dos Problemas Identificados no Sistema evidens.digital

## Problemas Reportados

### 1. Recomendações com "undefined" no grau de evidência e subtítulo

**Localização do problema:**
- Arquivo: `src/routes/checkup_intelligent.py` (linhas 500-510)
- Função: `generate_intelligent_recommendations()`

**Causa identificada:**
```python
# Garantir chaves opcionais presentes em todas as recomendações
try:
    for rec in response.get('recommendations', []) or []:
        if 'subtitulo' not in rec:
            rec['subtitulo'] = None  # ❌ Problema: None vira "undefined" no frontend
        if 'grau_evidencia' not in rec:
            rec['grau_evidencia'] = None  # ❌ Problema: None vira "undefined" no frontend
except Exception:
    pass
```

**Frontend (index.html linha ~580):**
```javascript
const subtitulo = rec && rec.subtitulo ? rec.subtitulo : '';  // ❌ None vira "undefined"
const grau = rec && rec.grau_evidencia ? rec.grau_evidencia : '';  // ❌ None vira "undefined"
```

### 2. Falha ao gerar "📋 Solicitação de Exames"

**Localização do problema:**
- Arquivo: `index.html` (função `generateExamRequest()`)
- Endpoint: `/api/gerar-solicitacao-exames`

**Causa identificada:**
```javascript
fetch('/api/gerar-solicitacao-exames', {  // ❌ Rota incorreta
    method: 'POST',
    // ...
})
```

**Rota correta no backend:**
```python
@checkup_intelligent_bp.route('/gerar-solicitacao-exames', methods=['POST'])  # ✅ Sem /api/
```

### 3. Erro 404 na receita de vacinas

**Localização do problema:**
- Arquivo: `index.html` (função `generateVaccineReceipt()`)
- Endpoint: `/api/gerar-receita-vacinas`

**Causa identificada:**
```javascript
fetch('/api/gerar-receita-vacinas', {  // ❌ Rota incorreta
    method: 'POST',
    // ...
})
```

**Rota correta no backend:**
```python
@checkup_intelligent_bp.route('/gerar-receita-vacinas', methods=['POST'])  # ✅ Sem /api/
```

### 4. Exames e recomendações não aparecendo

**Localização do problema:**
- Arquivo: `src/routes/checkup_intelligent.py`
- Funções: `generate_age_sex_recommendations()` e `generate_biomarker_recommendations()`

**Causas identificadas:**

#### 4.1 Problema na função `_add_rec()`:
```python
def _add_rec(rec):
    # Evita duplicados pelo título (case-insensitive) dentro desta função
    title = (rec.get('titulo') or '').strip().lower()
    if not title:
        return
    if any((r.get('titulo') or '').strip().lower() == title for r in recommendations):
        return  # ❌ Pode estar bloqueando recomendações válidas
    recommendations.append(rec)
```

#### 4.2 Categorização incorreta no frontend:
```javascript
// Lógica de categorização muito restritiva
if (cat.includes('vacina')) {
    category = 'Vacinas';
} else if (cat === 'laboratorio' ||  // ❌ Muito específico
          title.includes('hba1c') ||
          // ... lista muito específica
```

#### 4.3 Estrutura de dados inconsistente:
- Backend usa `categoria: 'laboratorio'`
- Frontend espera `categoria: 'laboratorial'` em alguns casos

## Soluções Propostas

### 1. Corrigir valores "undefined"
- Substituir `None` por strings vazias no backend
- Melhorar validação no frontend

### 2. Corrigir rotas dos endpoints
- Remover `/api/` das chamadas fetch
- Ou adicionar `/api/` nas rotas do backend

### 3. Melhorar lógica de categorização
- Padronizar nomes de categorias
- Tornar lógica mais flexível

### 4. Revisar função de deduplicação
- Melhorar algoritmo para evitar bloqueios desnecessários
- Adicionar logs para debug

## Arquivos que precisam ser modificados

1. `src/routes/checkup_intelligent.py`
2. `index.html` (funções JavaScript)
3. Possível adição de rotas em `app.py` ou arquivo de rotas principal
