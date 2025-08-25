from instance_types_extraction_module.instance_types_extraction import InstanceTypesCalculation

def extract_instance_types(self) -> None:
    """Estrae i tipi di istanza dal log."""
    try:
        print("Estraendo tipi di istanza...")
        
        if not self._branch_prob:
            raise ValueError("Probabilità di branching non calcolate. Chiamare prima calculate_branching_probabilities()")
        
        branches = self._branch_prob._branches
        tot_execute_per_branch = self._branch_prob._tot
        
        self._instance_types = InstanceTypesCalculation(self.log, self.settings, branches, tot_execute_per_branch)
        # Calcolo completo
        results = self._instance_types.calculate_all_instance_types()

        # Accesso ai risultati
        instance_types = self._instance_types._instance_types
        forced_types = self._instance_types._forced_instance_types
        print("✓ Tipi di istanza estratti")
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei tipi di istanza: {str(e)}")