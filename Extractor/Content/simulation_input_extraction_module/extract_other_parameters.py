from other_parameters_extraction_module.other_parameters_extraction import OtherParametersCalculation

def extract_other_parameters(self) -> None:
        """Estrae altri parametri dal log (costi, setup time, etc.)."""
        try:
            print("Estraendo altri parametri...")
            
            if not self._resource_param:
                raise ValueError("Parametri risorse non estratti. Chiamare prima extract_resource_parameters()")
            
            roles = self._resource_param._roles
            self._other_params = OtherParametersCalculation(self.log, self.settings, roles)
            
            # Estrazione parametri aggiuntivi basati sulla configurazione
            if self.primary_config['cost_hour']:
                print("  - Estraendo costi orari...")
                self._other_params.cost_hour_parameter(self.log)
            
            if self.primary_config['fixed_cost']:
                print("  - Estraendo costi fissi...")
                self._other_params.fixed_activity_cost(self.log)
            
            if self.primary_config['diag_log'] and self.primary_config['setup_time']:
                print("  - Estraendo setup time...")
                self._other_params.setup_time_act(self.log)
            
            print("✓ Altri parametri estratti")
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione degli altri parametri: {str(e)}")