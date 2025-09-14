#!/usr/bin/env python3
"""
Script para inicializar o banco de dados do sistema de check-up médico
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.models.user import db, User
from src.models.medical import Patient, Checkup, Recomendacao, ExameRealizado, Analytics

def create_app():
    """Criar aplicação Flask para inicialização do banco"""
    app = Flask(__name__)
    
    # Configuração do banco de dados
    database_path = os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar extensões
    db.init_app(app)
    
    return app

def init_database():
    """Inicializar o banco de dados com todas as tabelas"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Criando tabelas do banco de dados...")
        
        # Criar todas as tabelas
        db.create_all()
        
        print("✅ Tabelas criadas com sucesso!")
        
        # Verificar se já existem dados de exemplo
        if Patient.query.count() == 0:
            print("📝 Inserindo dados de exemplo...")
            
            # Criar paciente de exemplo
            paciente_exemplo = Patient(
                nome="João Silva",
                idade=45,
                sexo="masculino",
                peso=80.0,
                altura=175.0
            )
            
            db.session.add(paciente_exemplo)
            db.session.commit()
            
            # Criar checkup de exemplo
            checkup_exemplo = Checkup(
                patient_id=paciente_exemplo.id,
                pressao_sistolica=140.0,
                pressao_diastolica=90.0,
                colesterol_total=220.0,
                hdl_colesterol=45.0,
                creatinina=1.1,
                hba1c=6.2,
                risco_10_anos=7.5,
                risco_30_anos=21.0,
                classificacao_risco="intermediario",
                comorbidades='["hipertensao"]',
                historia_familiar='["diabetes"]',
                tabagismo="nunca_fumou",
                macos_ano=0,
                medicacoes="Losartana 50mg 1x/dia",
                pais_guideline="BR"
            )
            
            db.session.add(checkup_exemplo)
            db.session.commit()
            
            # Criar recomendações de exemplo
            recomendacoes_exemplo = [
                Recomendacao(
                    checkup_id=checkup_exemplo.id,
                    titulo="Colesterol total e frações",
                    descricao="Colesterol total, HDL, LDL e triglicerídeos",
                    categoria="laboratorio",
                    prioridade="alta",
                    referencia="AHA/ACC 2019"
                ),
                Recomendacao(
                    checkup_id=checkup_exemplo.id,
                    titulo="Eletrocardiograma de repouso",
                    descricao="ECG de 12 derivações - Rastreamento cardiovascular",
                    categoria="imagem",
                    prioridade="alta",
                    referencia="SBC 2019"
                ),
                Recomendacao(
                    checkup_id=checkup_exemplo.id,
                    titulo="Vacina Influenza Tetravalente",
                    descricao="Dose anual - Aplicar em dose única, INTRAMUSCULAR",
                    categoria="vacina",
                    prioridade="alta",
                    referencia="SBIm/ANVISA 2024"
                )
            ]
            
            for rec in recomendacoes_exemplo:
                db.session.add(rec)
            
            db.session.commit()
            
            print("✅ Dados de exemplo inseridos com sucesso!")
        
        # Mostrar estatísticas do banco
        print("\n📊 Estatísticas do banco de dados:")
        print(f"   👥 Usuários: {User.query.count()}")
        print(f"   🏥 Pacientes: {Patient.query.count()}")
        print(f"   📋 Check-ups: {Checkup.query.count()}")
        print(f"   💊 Recomendações: {Recomendacao.query.count()}")
        print(f"   🧪 Exames realizados: {ExameRealizado.query.count()}")
        print(f"   📈 Eventos de analytics: {Analytics.query.count()}")

def show_database_info():
    """Mostrar informações sobre o banco de dados"""
    app = create_app()
    
    with app.app_context():
        print("\n🗄️  INFORMAÇÕES DO BANCO DE DADOS")
        print("=" * 50)
        
        # Listar todas as tabelas
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Tabelas encontradas: {len(tables)}")
        for table in tables:
            print(f"   • {table}")
        
        print("\n📊 Dados por tabela:")
        if 'user' in tables:
            print(f"   👥 user: {User.query.count()} registros")
        if 'patients' in tables:
            print(f"   🏥 patients: {Patient.query.count()} registros")
        if 'checkups' in tables:
            print(f"   📋 checkups: {Checkup.query.count()} registros")
        if 'recomendacoes' in tables:
            print(f"   💊 recomendacoes: {Recomendacao.query.count()} registros")
        if 'exames_realizados' in tables:
            print(f"   🧪 exames_realizados: {ExameRealizado.query.count()} registros")
        if 'analytics' in tables:
            print(f"   📈 analytics: {Analytics.query.count()} registros")

def reset_database():
    """Resetar o banco de dados (CUIDADO: apaga todos os dados!)"""
    app = create_app()
    
    response = input("⚠️  ATENÇÃO: Isso irá apagar TODOS os dados do banco. Continuar? (digite 'SIM' para confirmar): ")
    if response != 'SIM':
        print("❌ Operação cancelada.")
        return
    
    with app.app_context():
        print("🔄 Removendo todas as tabelas...")
        db.drop_all()
        
        print("🔄 Recriando tabelas...")
        db.create_all()
        
        print("✅ Banco de dados resetado com sucesso!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            init_database()
        elif command == "info":
            show_database_info()
        elif command == "reset":
            reset_database()
        else:
            print("❌ Comando inválido. Use: init, info ou reset")
    else:
        print("🏥 Sistema de Check-up Médico - Gerenciador de Banco de Dados")
        print("=" * 60)
        print("Comandos disponíveis:")
        print("  python init_database.py init   - Inicializar banco de dados")
        print("  python init_database.py info   - Mostrar informações do banco")
        print("  python init_database.py reset  - Resetar banco de dados (CUIDADO!)")
        print()
        
        # Mostrar informações por padrão
        show_database_info()
