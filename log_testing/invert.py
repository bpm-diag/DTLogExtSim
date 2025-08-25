#!/usr/bin/env python3
"""
Script per invertire le voci 'assign' e 'start' nei log XES.
Sostituisce 'assign' con 'start' e viceversa nell'attributo lifecycle:transition.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import argparse

def invert_lifecycle_transitions(file_path, output_path=None):
    """
    Inverte le transizioni 'assign' e 'start' nel file XES.
    
    Args:
        file_path (str): Percorso del file XES di input
        output_path (str, optional): Percorso del file di output. Se None, sovrascrive l'input.
    """
    
    # Leggi il file come testo per debug
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File non trovato: {file_path}")
        return False
    except Exception as e:
        print(f"Errore nella lettura del file: {e}")
        return False
    
    # Debug: contiamo le occorrenze prima della modifica
    import re
    start_pattern = r'key="lifecycle:transition"\s+value="start"'
    assign_pattern = r'key="lifecycle:transition"\s+value="assign"'
    
    start_matches_before = len(re.findall(start_pattern, content))
    assign_matches_before = len(re.findall(assign_pattern, content))
    
    print(f"Prima della modifica:")
    print(f"  - Trovati {start_matches_before} 'start'")
    print(f"  - Trovati {assign_matches_before} 'assign'")
    
    if start_matches_before == 0 and assign_matches_before == 0:
        print("Nessuna transizione 'start' o 'assign' trovata!")
        return False
    
    # Carica il file XML con ElementTree
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Errore nel parsing del file XML: {e}")
        return False
    
    # Contatori per tracciare le modifiche
    assign_to_start_count = 0
    start_to_assign_count = 0
    
    # Trova tutti gli elementi con key="lifecycle:transition" usando xpath semplice
    # Cerchiamo tutti gli elementi indipendentemente dal tag
    elements_found = root.findall(".//*[@key='lifecycle:transition']")
    
    print(f"Elementi lifecycle:transition trovati: {len(elements_found)}")
    
    # Processa gli elementi trovati
    for elem in elements_found:
        current_value = elem.get('value')
        print(f"Trovato elemento con valore: '{current_value}'")
        
        if current_value == 'assign':
            elem.set('value', 'start')
            assign_to_start_count += 1
            print(f"  Cambiato 'assign' → 'start'")
        elif current_value == 'start':
            elem.set('value', 'assign')
            start_to_assign_count += 1
            print(f"  Cambiato 'start' → 'assign'")
    
    # Se non abbiamo trovato elementi con ElementTree, proviamo con regex
    if assign_to_start_count == 0 and start_to_assign_count == 0 and (start_matches_before > 0 or assign_matches_before > 0):
        print("ElementTree non ha trovato elementi, uso regex come fallback...")
        return invert_with_regex(file_path, output_path)
    
    # Determina il percorso di output
    if output_path is None:
        output_path = file_path
    
    # Salva il file modificato senza dichiarazione XML namespace
    try:
        # Rimuovi tutti i prefissi namespace dagli elementi se presenti
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[-1]
        
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"File salvato con successo: {output_path}")
        print(f"Modifiche effettuate:")
        print(f"  - 'assign' → 'start': {assign_to_start_count} occorrenze")
        print(f"  - 'start' → 'assign': {start_to_assign_count} occorrenze")
        print(f"  - Totale modifiche: {assign_to_start_count + start_to_assign_count}")
        return True
    except Exception as e:
        print(f"Errore nel salvataggio del file: {e}")
        return False

def invert_with_regex(file_path, output_path=None):
    """
    Fallback: usa regex per invertire le transizioni quando ElementTree fallisce.
    """
    import re
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Errore nella lettura del file: {e}")
        return False
    
    # Contatori
    assign_to_start_count = 0
    start_to_assign_count = 0
    
    # Pattern per trovare e sostituire
    def replace_start(match):
        nonlocal start_to_assign_count
        start_to_assign_count += 1
        return match.group(0).replace('value="start"', 'value="assign"')
    
    def replace_assign(match):
        nonlocal assign_to_start_count
        assign_to_start_count += 1
        return match.group(0).replace('value="assign"', 'value="start"')
    
    # Sostituzioni
    content = re.sub(r'key="lifecycle:transition"\s+value="start"', replace_start, content)
    content = re.sub(r'key="lifecycle:transition"\s+value="assign"', replace_assign, content)
    
    # Determina il percorso di output
    if output_path is None:
        output_path = file_path
    
    # Salva il file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"File salvato con successo (regex): {output_path}")
        print(f"Modifiche effettuate:")
        print(f"  - 'assign' → 'start': {assign_to_start_count} occorrenze")
        print(f"  - 'start' → 'assign': {start_to_assign_count} occorrenze")
        print(f"  - Totale modifiche: {assign_to_start_count + start_to_assign_count}")
        return True
    except Exception as e:
        print(f"Errore nel salvataggio del file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Inverte le transizioni 'assign' e 'start' nei log XES"
    )
    parser.add_argument(
        'input_file', 
        help='File XES di input'
    )
    parser.add_argument(
        '-o', '--output', 
        help='File di output (default: sovrascrive il file di input)',
        default=None
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Crea un backup del file originale con estensione .bak'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    
    # Verifica che il file esista
    if not input_path.exists():
        print(f"Errore: Il file {input_path} non esiste")
        return 1
    
    # Crea backup se richiesto
    if args.backup:
        backup_path = input_path.with_suffix(input_path.suffix + '.bak')
        try:
            import shutil
            shutil.copy2(input_path, backup_path)
            print(f"Backup creato: {backup_path}")
        except Exception as e:
            print(f"Errore nella creazione del backup: {e}")
            return 1
    
    # Esegui l'inversione
    success = invert_lifecycle_transitions(str(input_path), args.output)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())