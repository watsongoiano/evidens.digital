from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .user import db

class Patient(db.Model):
    """Modelo para armazenar dados dos pacientes"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    idade = db.Column(db.Integer, nullable=False)
    sexo = db.Column(db.String(10), nullable=False)  # 'masculino' ou 'feminino'
    peso = db.Column(db.Float)
    altura = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    checkups = db.relationship('Checkup', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'idade': self.idade,
            'sexo': self.sexo,
            'peso': self.peso,
            'altura': self.altura,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Checkup(db.Model):
    """Modelo para armazenar dados de check-ups realizados"""
    __tablename__ = 'checkups'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Dados clínicos
    pressao_sistolica = db.Column(db.Float)
    pressao_diastolica = db.Column(db.Float)
    colesterol_total = db.Column(db.Float)
    hdl_colesterol = db.Column(db.Float)
    creatinina = db.Column(db.Float)
    hba1c = db.Column(db.Float)
    
    # Cálculo de risco PREVENT
    risco_10_anos = db.Column(db.Float)
    risco_30_anos = db.Column(db.Float)
    classificacao_risco = db.Column(db.String(20))  # 'baixo', 'intermediario', 'alto'
    
    # Comorbidades e histórico
    comorbidades = db.Column(db.Text)  # JSON string
    historia_familiar = db.Column(db.Text)  # JSON string
    tabagismo = db.Column(db.String(20))
    macos_ano = db.Column(db.Integer)
    medicacoes = db.Column(db.Text)
    
    # Metadados
    pais_guideline = db.Column(db.String(10), default='BR')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    recomendacoes = db.relationship('Recomendacao', backref='checkup', lazy=True, cascade='all, delete-orphan')
    exames = db.relationship('ExameRealizado', backref='checkup', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Checkup {self.id} - Patient {self.patient_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'pressao_sistolica': self.pressao_sistolica,
            'pressao_diastolica': self.pressao_diastolica,
            'colesterol_total': self.colesterol_total,
            'hdl_colesterol': self.hdl_colesterol,
            'creatinina': self.creatinina,
            'hba1c': self.hba1c,
            'risco_10_anos': self.risco_10_anos,
            'risco_30_anos': self.risco_30_anos,
            'classificacao_risco': self.classificacao_risco,
            'comorbidades': self.comorbidades,
            'historia_familiar': self.historia_familiar,
            'tabagismo': self.tabagismo,
            'macos_ano': self.macos_ano,
            'medicacoes': self.medicacoes,
            'pais_guideline': self.pais_guideline,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Recomendacao(db.Model):
    """Modelo para armazenar recomendações geradas"""
    __tablename__ = 'recomendacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    checkup_id = db.Column(db.Integer, db.ForeignKey('checkups.id'), nullable=False)
    
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(50))  # 'laboratorio', 'imagem', 'vacina', 'outras'
    prioridade = db.Column(db.String(20))  # 'alta', 'media', 'baixa'
    referencia = db.Column(db.String(100))
    
    # Status da recomendação
    status = db.Column(db.String(20), default='pendente')  # 'pendente', 'realizada', 'cancelada'
    data_realizacao = db.Column(db.DateTime)
    observacoes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Recomendacao {self.titulo}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'checkup_id': self.checkup_id,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'prioridade': self.prioridade,
            'referencia': self.referencia,
            'status': self.status,
            'data_realizacao': self.data_realizacao.isoformat() if self.data_realizacao else None,
            'observacoes': self.observacoes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ExameRealizado(db.Model):
    """Modelo para armazenar histórico de exames realizados"""
    __tablename__ = 'exames_realizados'
    
    id = db.Column(db.Integer, primary_key=True)
    checkup_id = db.Column(db.Integer, db.ForeignKey('checkups.id'), nullable=False)
    
    nome_exame = db.Column(db.String(200), nullable=False)
    data_realizacao = db.Column(db.DateTime, nullable=False)
    resultado = db.Column(db.Text)
    valores_referencia = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    
    # Arquivo do exame (se houver)
    arquivo_path = db.Column(db.String(500))
    arquivo_nome = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExameRealizado {self.nome_exame}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'checkup_id': self.checkup_id,
            'nome_exame': self.nome_exame,
            'data_realizacao': self.data_realizacao.isoformat() if self.data_realizacao else None,
            'resultado': self.resultado,
            'valores_referencia': self.valores_referencia,
            'observacoes': self.observacoes,
            'arquivo_path': self.arquivo_path,
            'arquivo_nome': self.arquivo_nome,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Analytics(db.Model):
    """Modelo para armazenar dados de analytics do sistema"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    evento = db.Column(db.String(100), nullable=False)  # 'visita', 'checkup_gerado', 'pdf_gerado', etc.
    dados = db.Column(db.Text)  # JSON string com dados adicionais
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Analytics {self.evento}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'evento': self.evento,
            'dados': self.dados,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
