#!/usr/bin/env python3
import pandas as pd
import numpy as np

def analyze_prevent_excel():
    """Analyser les fichiers Excel PREVENT pour extraire les coefficients"""
    
    print("=== Analyse des fichiers Excel PREVENT ===\n")
    
    # Fichiers à analyser
    excel_files = [
        "/home/ubuntu/upload/10.1161.circulationaha.123.067626_supplemental_excel.xlsx",
        "/home/ubuntu/upload/supplement_tables_for_manuscript_20240126_withcalc.check.xlsx"
    ]
    
    for file_path in excel_files:
        try:
            print(f"Analyse de: {file_path}")
            
            # Lire toutes les feuilles du fichier Excel
            excel_file = pd.ExcelFile(file_path)
            print(f"Feuilles disponibles: {excel_file.sheet_names}\n")
            
            # Chercher les feuilles avec les coefficients (Table S12)
            for sheet_name in excel_file.sheet_names:
                if 'S12' in sheet_name or 'coefficient' in sheet_name.lower() or 'equation' in sheet_name.lower():
                    print(f"=== Feuille: {sheet_name} ===")
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    print(f"Dimensions: {df.shape}")
                    print(f"Colonnes: {list(df.columns)}")
                    print(f"Premières lignes:")
                    print(df.head(10))
                    print("\n" + "="*50 + "\n")
                    
                    # Sauvegarder cette feuille pour analyse détaillée
                    output_file = f"/home/ubuntu/prevent_coefficients_{sheet_name.replace(' ', '_')}.csv"
                    df.to_csv(output_file, index=False)
                    print(f"Sauvegardé dans: {output_file}\n")
            
        except Exception as e:
            print(f"Erreur lors de l'analyse de {file_path}: {e}\n")

if __name__ == "__main__":
    analyze_prevent_excel()

