# Esempio di utilizzo del normalizzatore XES

from xes_normalizer import XESLogNormalizer, normalize_xes_file

# METODO 1: Funzione semplice
def quick_normalize():
    """Metodo veloce per normalizzare un file."""
    input_file = "event_log_processed.xes"
    
    # Normalizza automaticamente
    normalized_file, report = normalize_xes_file(input_file)
    
    print(f"✓ File normalizzato: {normalized_file}")
    print(f"✓ Eventi: {report['transformation_summary']['normalized_events']}")
    
    return normalized_file


# METODO 2: Classe completa con più controllo
def advanced_normalize():
    """Metodo avanzato con più controllo."""
    
    # Inizializza normalizzatore
    normalizer = XESLogNormalizer()
    
    # File da normalizzare
    input_files = [
        "event_log_processed.xes",
        "manufacturing_log.xes",
        "hospital_log.xes"
    ]
    
    results = []
    
    for input_file in input_files:
        try:
            print(f"\n📁 Processando: {input_file}")
            
            # Normalizza
            output_file = f"normalized_{input_file}"
            normalized_path = normalizer.normalize_xes_log(input_file, output_file)
            
            # Genera report
            report = normalizer.get_normalization_report(input_file, normalized_path)
            
            # Verifica compatibilità
            compatibility = report['compatibility_check']
            compatible = all(compatibility.values())
            
            results.append({
                'file': input_file,
                'normalized': normalized_path,
                'compatible': compatible,
                'report': report
            })
            
            print(f"✓ Normalizzato: {normalized_path}")
            print(f"✓ Compatibile: {'Sì' if compatible else 'No'}")
            
        except Exception as e:
            print(f"✗ Errore con {input_file}: {e}")
    
    return results


# METODO 3: Integrazione con il tuo sistema esistente
def integrate_with_existing_system():
    """Integra normalizzatore con ProcessXesFile."""
    from process_xes_file import ProcessXesFile
    
    def process_any_xes_file(file_path, output_dir, eta="0.01", eps="0.001", simthreshold="0.9"):
        """
        Processa qualsiasi file XES normalizzandolo prima.
        
        Args:
            file_path: Percorso file XES (anche non standard)
            output_dir: Directory output
            eta, eps, simthreshold: Parametri del sistema
            
        Returns:
            Risultato del processamento
        """
        
        try:
            # 1. Normalizza il file XES
            print(f"🔧 Normalizzando {file_path}...")
            normalized_path, report = normalize_xes_file(file_path)
            
            # 2. Verifica compatibilità
            compatibility = report['compatibility_check']
            if not all(compatibility.values()):
                print("⚠️ Avvisi di compatibilità:")
                for check, result in compatibility.items():
                    if not result:
                        print(f"  - {check.replace('_', ' ').title()}")
            
            # 3. Processa con il tuo sistema esistente
            print(f"⚙️ Processando con il sistema esistente...")
            processor = ProcessXesFile(
                file_path=normalized_path,
                output_dir_path=output_dir,
                eta=eta,
                eps=eps,
                simthreshold=simthreshold
            )
            
            result = processor.process()
            
            # 4. Aggiungi info normalizzazione al risultato
            if result.get('success'):
                result['normalization_info'] = {
                    'original_file': file_path,
                    'normalized_file': normalized_path,
                    'transformation_report': report
                }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Errore nel processamento: {str(e)}",
                'file_processed': file_path
            }
    
    return process_any_xes_file


# METODO 4: Batch processing per multiple file
def batch_normalize_directory():
    """Normalizza tutti i file XES in una directory."""
    import glob
    
    # Directory con file XES
    input_directory = "logs/"
    output_directory = "normalized_logs/"
    
    # Trova tutti i file XES
    xes_files = glob.glob(f"{input_directory}*.xes")
    
    print(f"📂 Trovati {len(xes_files)} file XES")
    
    results = []
    normalizer = XESLogNormalizer()
    
    for file_path in xes_files:
        try:
            print(f"\n📄 Processando: {os.path.basename(file_path)}")
            
            # Output path
            output_file = os.path.join(
                output_directory, 
                f"normalized_{os.path.basename(file_path)}"
            )
            
            # Normalizza
            normalized_path = normalizer.normalize_xes_log(file_path, output_file)
            
            # Report
            report = normalizer.get_normalization_report(file_path, normalized_path)
            
            results.append({
                'original': file_path,
                'normalized': normalized_path,
                'success': True,
                'report': report
            })
            
            print(f"✅ Completato")
            
        except Exception as e:
            results.append({
                'original': file_path,
                'success': False,
                'error': str(e)
            })
            print(f"❌ Errore: {e}")
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n📊 Risultati: {successful}/{len(results)} file normalizzati con successo")
    
    return results


# METODO 5: Classe wrapper per il tuo sistema
class UniversalProcessXesFile:
    """Wrapper che normalizza automaticamente qualsiasi XES prima di processarlo."""
    
    def __init__(self, auto_normalize=True):
        self.auto_normalize = auto_normalize
        self.normalizer = XESLogNormalizer() if auto_normalize else None
    
    def process_any_xes(self, file_path, output_dir_path, eta="0.01", eps="0.001", simthreshold="0.9"):
        """
        Processa qualsiasi file XES, normalizzandolo automaticamente se necessario.
        
        Args:
            file_path: File XES (standard o non-standard)  
            output_dir_path: Directory di output
            eta, eps, simthreshold: Parametri sistema
            
        Returns:
            Risultato processamento con info normalizzazione
        """
        
        try:
            original_file = file_path
            processing_file = file_path
            normalization_report = None
            
            if self.auto_normalize:
                # Controlla se il file necessita normalizzazione
                needs_normalization = self._check_if_normalization_needed(file_path)
                
                if needs_normalization:
                    print(f"🔧 File non standard rilevato, normalizzazione in corso...")
                    
                    # Normalizza
                    normalized_path, report = normalize_xes_file(file_path)
                    processing_file = normalized_path
                    normalization_report = report
                    
                    print(f"✅ Normalizzazione completata")
                else:
                    print(f"✅ File già in formato standard")
            
            # Processa con il sistema esistente
            print(f"⚙️ Avvio processamento parametri...")
            
            processor = ProcessXesFile(
                file_path=processing_file,
                output_dir_path=output_dir_path,
                eta=eta,
                eps=eps,
                simthreshold=simthreshold
            )
            
            result = processor.process()
            
            # Aggiungi info normalizzazione
            if normalization_report:
                result['normalization_applied'] = True
                result['normalization_report'] = normalization_report
                result['original_file'] = original_file
                result['normalized_file'] = processing_file
            else:
                result['normalization_applied'] = False
                result['original_file'] = original_file
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Errore nel processamento universale: {str(e)}",
                'file_processed': file_path,
                'normalization_applied': False
            }
    
    def _check_if_normalization_needed(self, file_path):
        """Controlla se un file necessita normalizzazione."""
        try:
            import pm4py
            log = pm4py.read_xes(file_path)
            
            # Verifica presenza colonne standard
            required_columns = [
                'case:concept:name',
                'concept:name', 
                'time:timestamp',
                'lifecycle:transition'
            ]
            
            missing_columns = [col for col in required_columns if col not in log.columns]
            
            # Se mancano colonne essenziali, serve normalizzazione
            return len(missing_columns) > 0
            
        except Exception:
            # In caso di errore, normalizza comunque
            return True


# ESEMPIO PRATICO DI UTILIZZO
if __name__ == "__main__":
    
    print("🚀 ESEMPI DI UTILIZZO NORMALIZZATORE XES")
    print("="*50)
    
    # Esempio 1: Normalizzazione singola
    print("\n1️⃣ NORMALIZZAZIONE SINGOLA")
    try:
        normalized_file, report = normalize_xes_file("event_log_processed.xes")
        print(f"✅ Successo: {normalized_file}")
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    # Esempio 2: Wrapper universale  
    print("\n2️⃣ PROCESSAMENTO UNIVERSALE")
    try:
        universal_processor = UniversalProcessXesFile(auto_normalize=True)
        result = universal_processor.process_any_xes(
            file_path="event_log_processed.xes",
            output_dir_path="output/",
            eta="0.01",
            eps="0.001", 
            simthreshold="0.9"
        )
        
        if result['success']:
            print(f"✅ Processamento completato")
            print(f"   Normalizzazione applicata: {result['normalization_applied']}")
            if result['normalization_applied']:
                print(f"   File originale: {result['original_file']}")
                print(f"   File normalizzato: {result['normalized_file']}")
        else:
            print(f"❌ Errore: {result['error']}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    # Esempio 3: Integrazione con app Flask
    print("\n3️⃣ INTEGRAZIONE FLASK")
    print("""
    # Modifica il tuo app.py così:
    
    from normalize_xes import UniversalProcessXesFile
    
    @app.route("/", methods=["GET","POST"])
    def index():
        if request.method == "POST":
            # ... codice esistente per salvare file ...
            
            try:
                # USA IL PROCESSORE UNIVERSALE invece di ProcessXesFile
                universal_processor = UniversalProcessXesFile(auto_normalize=True)
                result = universal_processor.process_any_xes(
                    file_path=new_unique_filename,
                    output_dir_path=f"extractor/{unique_id}/",
                    eta=params['eta'],
                    eps=params['eps'],
                    simthreshold=params['simthreshold']
                )
                
                data = {
                    "Service Name": app.config["SERVICE_NAME"],
                    "extractor_output": True,
                    "result": result,
                    "normalization_applied": result.get('normalization_applied', False)
                }
                
            except Exception as e:
                # ... gestione errori ...
    """)
    
    print("\n🎯 CONCLUSIONE:")
    print("Ora puoi processare QUALSIASI file XES!")
    print("Il normalizzatore gestisce automaticamente:")
    print("  ✅ Log standard e non-standard")
    print("  ✅ Colonne con nomi diversi") 
    print("  ✅ Valori mancanti o incorretti")
    print("  ✅ Eventi start/end con nomi diversi")
    print("  ✅ Gateway e nodi speciali")
    print("  ✅ Timestamp e lifecycle non standard")