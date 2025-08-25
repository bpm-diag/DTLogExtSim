from activity_param_extraction_module.activity_param_extraction import ActivityParamExtraction 

def extract_activity_parameters(self) -> None:
        """Estrae i parametri delle attività dal log."""
        try:
            print("Estraendo parametri attività...")
            extractor = ActivityParamExtraction(self.log, self.settings)
            result = extractor.extract_all_parameters()
            
            # Salva il risultato dell'estrazione
            self._activity_param = extractor
            print("✓ Parametri attività estratti")
        except Exception as e:
            raise Exception(f"Errore nell'estrazione dei parametri delle attività: {str(e)}")
    