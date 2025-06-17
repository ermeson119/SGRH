#!/usr/bin/env python3
"""
Script de migração para atualizar a estrutura da tabela folha
"""
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Folha, PessoaFolha

def migrate_folha():
    """Migra a estrutura da tabela folha"""
    app = create_app()
    
    with app.app_context():
        print("Iniciando migração da tabela folha...")
        
        try:
            # Verificar se a coluna mes_ano já existe
            result = db.session.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'folha' AND column_name = 'mes_ano'
            """)
            
            if not result.fetchone():
                print("Adicionando coluna mes_ano...")
                db.session.execute("ALTER TABLE folha ADD COLUMN mes_ano VARCHAR(7)")
                
                # Atualizar registros existentes
                print("Atualizando registros existentes...")
                folhas = Folha.query.all()
                for folha in folhas:
                    folha.mes_ano = folha.data.strftime('%Y-%m')
                
                db.session.commit()
                print(f"Atualizados {len(folhas)} registros")
            else:
                print("Coluna mes_ano já existe")
            
            # Verificar se a coluna valor_total já existe
            result = db.session.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'folha' AND column_name = 'valor_total'
            """)
            
            if not result.fetchone():
                print("Adicionando coluna valor_total...")
                db.session.execute("ALTER TABLE folha ADD COLUMN valor_total FLOAT DEFAULT 0.0")
                
                # Calcular valores totais para registros existentes
                print("Calculando valores totais...")
                folhas = Folha.query.all()
                for folha in folhas:
                    total = sum(pf.valor for pf in folha.pessoa_folhas)
                    folha.valor_total = total
                
                db.session.commit()
                print(f"Calculados valores totais para {len(folhas)} folhas")
            else:
                print("Coluna valor_total já existe")
            
            # Verificar se a coluna status já existe
            result = db.session.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'folha' AND column_name = 'status'
            """)
            
            if not result.fetchone():
                print("Adicionando coluna status...")
                db.session.execute("ALTER TABLE folha ADD COLUMN status VARCHAR(20) DEFAULT 'aberta'")
                db.session.commit()
                print("Coluna status adicionada")
            else:
                print("Coluna status já existe")
            
            # Verificar se a coluna observacao já existe
            result = db.session.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'folha' AND column_name = 'observacao'
            """)
            
            if not result.fetchone():
                print("Adicionando coluna observacao...")
                db.session.execute("ALTER TABLE folha ADD COLUMN observacao TEXT")
                db.session.commit()
                print("Coluna observacao adicionada")
            else:
                print("Coluna observacao já existe")
            
            # Criar índice na coluna mes_ano se não existir
            result = db.session.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'folha' AND indexname LIKE '%mes_ano%'
            """)
            
            if not result.fetchone():
                print("Criando índice na coluna mes_ano...")
                db.session.execute("CREATE INDEX ix_folha_mes_ano ON folha (mes_ano)")
                db.session.commit()
                print("Índice criado")
            else:
                print("Índice na coluna mes_ano já existe")
            
            print("Migração concluída com sucesso!")
            
        except Exception as e:
            print(f"Erro durante a migração: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_folha() 