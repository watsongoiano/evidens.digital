import json
import os
from datetime import datetime
from functools import wraps
from flask import request, g

class Analytics:
    def __init__(self, data_file='analytics_data.json'):
        self.data_file = os.path.join('/tmp', data_file)
        self.data = self.load_data()
    
    def load_data(self):
        """Carrega dados de analytics do arquivo JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Dados padrão se arquivo não existe ou está corrompido
        return {
            'total_visits': 0,
            'total_recommendations': 0,
            'total_exam_requests': 0,
            'total_vaccine_prescriptions': 0,
            'daily_stats': {},
            'monthly_stats': {},
            'user_agents': {},
            'countries': {},
            'last_updated': None
        }
    
    def save_data(self):
        """Salva dados de analytics no arquivo JSON"""
        self.data['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar analytics: {e}")
    
    def track_visit(self, user_agent=None, country=None):
        """Registra uma visita ao site"""
        print(f"[ANALYTICS] Registrando visita - UA: {user_agent}, País: {country}")
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        
        # Incrementa contadores gerais
        self.data['total_visits'] += 1
        print(f"[ANALYTICS] Total de visitas agora: {self.data['total_visits']}")
        
        # Estatísticas diárias
        if today not in self.data['daily_stats']:
            self.data['daily_stats'][today] = {
                'visits': 0,
                'recommendations': 0,
                'exam_requests': 0,
                'vaccine_prescriptions': 0
            }
        self.data['daily_stats'][today]['visits'] += 1
        
        # Estatísticas mensais
        if month not in self.data['monthly_stats']:
            self.data['monthly_stats'][month] = {
                'visits': 0,
                'recommendations': 0,
                'exam_requests': 0,
                'vaccine_prescriptions': 0
            }
        self.data['monthly_stats'][month]['visits'] += 1
        
        # User agents
        if user_agent:
            if user_agent not in self.data['user_agents']:
                self.data['user_agents'][user_agent] = 0
            self.data['user_agents'][user_agent] += 1
        
        # Países
        if country:
            if country not in self.data['countries']:
                self.data['countries'][country] = 0
            self.data['countries'][country] += 1
        
        self.save_data()
        print(f"[ANALYTICS] Dados salvos em: {self.data_file}")
    
    def track_recommendation(self):
        """Registra geração de recomendação"""
        print(f"[ANALYTICS] Registrando recomendação gerada")
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        
        self.data['total_recommendations'] += 1
        print(f"[ANALYTICS] Total de recomendações agora: {self.data['total_recommendations']}")
        
        if today in self.data['daily_stats']:
            self.data['daily_stats'][today]['recommendations'] += 1
        
        if month in self.data['monthly_stats']:
            self.data['monthly_stats'][month]['recommendations'] += 1
        
        self.save_data()
        print(f"[ANALYTICS] Recomendação salva com sucesso")
    
    def track_exam_request(self):
        """Registra geração de solicitação de exames"""
        print(f"[ANALYTICS] Registrando solicitação de exames")
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        
        self.data['total_exam_requests'] += 1
        print(f"[ANALYTICS] Total de solicitações de exames agora: {self.data['total_exam_requests']}")
        
        if today in self.data['daily_stats']:
            self.data['daily_stats'][today]['exam_requests'] += 1
        
        if month in self.data['monthly_stats']:
            self.data['monthly_stats'][month]['exam_requests'] += 1
        
        self.save_data()
        print(f"[ANALYTICS] Solicitação de exames salva com sucesso")
    
    def track_vaccine_prescription(self):
        """Registra geração de receita de vacinas"""
        print(f"[ANALYTICS] Registrando receita de vacinas")
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        
        self.data['total_vaccine_prescriptions'] += 1
        print(f"[ANALYTICS] Total de receitas de vacinas agora: {self.data['total_vaccine_prescriptions']}")
        
        if today in self.data['daily_stats']:
            self.data['daily_stats'][today]['vaccine_prescriptions'] += 1
        
        if month in self.data['monthly_stats']:
            self.data['monthly_stats'][month]['vaccine_prescriptions'] += 1
        
        self.save_data()
        print(f"[ANALYTICS] Receita de vacinas salva com sucesso")
    
    def get_stats(self):
        """Retorna estatísticas completas"""
        return self.data
    
    def get_summary(self):
        """Retorna resumo das estatísticas principais"""
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')
        
        today_stats = self.data['daily_stats'].get(today, {
            'visits': 0, 'recommendations': 0, 'exam_requests': 0, 'vaccine_prescriptions': 0
        })
        
        month_stats = self.data['monthly_stats'].get(month, {
            'visits': 0, 'recommendations': 0, 'exam_requests': 0, 'vaccine_prescriptions': 0
        })
        
        return {
            'total': {
                'visits': self.data['total_visits'],
                'recommendations': self.data['total_recommendations'],
                'exam_requests': self.data['total_exam_requests'],
                'vaccine_prescriptions': self.data['total_vaccine_prescriptions']
            },
            'today': today_stats,
            'this_month': month_stats,
            'last_updated': self.data['last_updated']
        }

# Instância global
analytics = Analytics()

def track_visit():
    """Decorator para rastrear visitas"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_agent = request.headers.get('User-Agent', 'Unknown')
            # Simplificar user agent para análise
            if 'Chrome' in user_agent:
                simplified_ua = 'Chrome'
            elif 'Firefox' in user_agent:
                simplified_ua = 'Firefox'
            elif 'Safari' in user_agent:
                simplified_ua = 'Safari'
            elif 'Edge' in user_agent:
                simplified_ua = 'Edge'
            else:
                simplified_ua = 'Other'
            
            analytics.track_visit(user_agent=simplified_ua)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

