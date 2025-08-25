from extraction_bpmn_module.extraction_bpmn import ExtractionBPMN

def extract_bpmn_model(self) -> None:
    """
    Estrae il modello BPMN dal log.
    
    Raises:
        Exception: Se l'estrazione del modello BPMN fallisce
    """
    try:
        print("Estraendo modello BPMN...")
        extractor = ExtractionBPMN(self.log, self.settings, self.with_start_end_act)
        bpmn_file = extractor.extract_bpmn_model()
        
        # Salva il risultato dell'estrazione
        self._extract_bpmn = extractor
        print("✓ Modello BPMN estratto con successo")
    except Exception as e:
        raise Exception(f"Errore nell'estrazione del modello BPMN: {str(e)}")