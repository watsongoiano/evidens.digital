#!/usr/bin/env python3

def test_gerar_solicitacao_exames():
    """Teste da funcionalidade de geração de solicitação de exames"""
    
    # Dados de teste
    test_data = {
        "patient_data": {
            "nome": "Maria Silva Santos",
            "cpf": "123.456.789-00",
            "sexo": "feminino",
            "idade": 35
        },
        "medico": {
            "nome": "Dr. João Oliveira",
            "crm": "12345-GO"
        },
        "recommendations": [
            {
                "titulo": "Hemograma Completo",
                "categoria": "Exames Laboratoriais",
                "descricao": "Exame de sangue completo"
            },
            {
                "titulo": "Glicemia de Jejum",
                "categoria": "Exames Laboratoriais",
                "descricao": "Dosagem de glicose no sangue"
            },
            {
                "titulo": "Tomografia Computadorizada do Tórax",
                "categoria": "Exames de Imagem",
                "descricao": "Exame de imagem do tórax"
            },
            {
                "titulo": "Ultrassom Abdominal",
                "categoria": "Exames de Imagem",
                "descricao": "Exame de ultrassom do abdômen"
            },
            {
                "titulo": "Colesterol Total e Frações",
                "categoria": "Exames Laboratoriais",
                "descricao": "Dosagem de colesterol"
            },
            {
                "titulo": "Colonoscopia com ou sem biópsia",
                "categoria": "Rastreamento",
                "descricao": "Colonoscopia para rastreamento colorretal"
            },
            {
                "titulo": "Lipoproteína(a) - Lp(a), soro",
                "categoria": "Estratificação Cardiovascular",
                "descricao": "Marcador complementar para estratificação de risco"
            },
            {
                "titulo": "Proteína C Reativa ultrassensível (hsCRP), soro",
                "categoria": "Estratificação Cardiovascular",
                "descricao": "Marcador inflamatório para estratificação de risco"
            },
            {
                "titulo": "Citologia Cervical + Teste de HPV",
                "categoria": "Outras recomendações",
                "descricao": "Co-teste (citologia + HPV) a cada 5 anos para mulheres de 30-65 anos"
            }
        ]
    }
    
    print("🧪 Iniciando teste de geração de solicitação de exames...")
    
    try:
        # Importar e testar diretamente a função
        import sys
        sys.path.append('/home/ubuntu/evidens.digital/api')
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("gerar_solicitacao_exames", "/home/ubuntu/evidens.digital/api/gerar-solicitacao-exames.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        categorizar_exames = module.categorizar_exames
        gerar_pdf_solicitacao = module.gerar_pdf_solicitacao
        
        # Teste 1: Categorização de exames
        print("📋 Testando categorização de exames...")
        
        # Debug específico para hsCRP
        hscrp_rec = {
            "titulo": "Proteína C Reativa ultrassensível (hsCRP), soro",
            "categoria": "Estratificação Cardiovascular",
            "descricao": "Marcador inflamatório para estratificação de risco"
        }
        
        # Debug detalhado
        titulo_norm = module._normalize_for_matching(hscrp_rec.get('titulo'))
        categoria_norm = module._normalize_for_matching(hscrp_rec.get('categoria'))
        descricao_norm = module._normalize_for_matching(hscrp_rec.get('descricao'))
        combined = ' '.join(filter(None, (titulo_norm, '', descricao_norm)))
        
        print(f"🔍 Debug hsCRP:")
        print(f"   Título normalizado: '{titulo_norm}'")
        print(f"   Categoria normalizada: '{categoria_norm}'")
        print(f"   Descrição normalizada: '{descricao_norm}'")
        print(f"   Combined: '{combined}'")
        print(f"   Classificação: {module._classify_exam_type(hscrp_rec)}")
        
        # Verificar se alguma palavra-chave de laboratório está presente
        lab_matches = [kw for kw in module.LAB_TITLE_KEYWORDS if kw in combined]
        img_matches = [kw for kw in module.IMAGING_TITLE_KEYWORDS if kw in combined]
        print(f"   Lab keywords encontradas: {lab_matches}")
        print(f"   Img keywords encontradas: {img_matches}")
        
        exames_lab, exames_img = categorizar_exames(test_data["recommendations"])

        print(f"   ✅ Exames laboratoriais encontrados: {len(exames_lab)}")
        for exame in exames_lab:
            print(f"      - {exame}")
            
        print(f"   ✅ Exames de imagem encontrados: {len(exames_img)}")
        for exame in exames_img:
            print(f"      - {exame}")

        assert "Lipoproteína(a) - Lp(a), soro" in exames_lab, "Lp(a) deveria ser categorizado como exame laboratorial"
        assert "Proteína C Reativa ultrassensível (hsCRP), soro" in exames_lab, "hsCRP deveria ser categorizado como exame laboratorial"
        assert "Colonoscopia com ou sem biópsia" in exames_img, "Colonoscopia deveria ser categorizada como exame de imagem"
        assert "Citologia Cervical + Teste de HPV" not in exames_lab, "O coteste deve ser substituído por exames específicos"
        assert "Pesquisa do Papilomavírus Humano (HPV), por técnica molecular, autocoleta" in exames_lab, "O teste de HPV por técnica molecular (autocoleta) deve ser solicitado"
        assert "Citologia cérvico-vaginal, em base líqüida, material vaginal e colo uterino" in exames_lab, "A citologia em base líqüida deve ser solicitada junto com o coteste"
        
        # Teste 2: Geração de PDF para exames laboratoriais
        if exames_lab:
            print("📄 Testando geração de PDF para exames laboratoriais...")
            pdf_lab = gerar_pdf_solicitacao(
                exames_lab,
                'Laboratorial',
                test_data["medico"],
                test_data["patient_data"]
            )
            
            # Salvar PDF de teste
            with open('/home/ubuntu/evidens.digital/teste_solicitacao_laboratorial.pdf', 'wb') as f:
                f.write(pdf_lab)
            print("   ✅ PDF laboratorial gerado com sucesso!")
        
        # Teste 3: Geração de PDF para exames de imagem
        if exames_img:
            print("📄 Testando geração de PDF para exames de imagem...")
            pdf_img = gerar_pdf_solicitacao(
                exames_img,
                'Imagem',
                test_data["medico"],
                test_data["patient_data"]
            )
            
            # Salvar PDF de teste
            with open('/home/ubuntu/evidens.digital/teste_solicitacao_imagem.pdf', 'wb') as f:
                f.write(pdf_img)
            print("   ✅ PDF de imagem gerado com sucesso!")
        
        print("🎉 Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gerar_solicitacao_exames()
