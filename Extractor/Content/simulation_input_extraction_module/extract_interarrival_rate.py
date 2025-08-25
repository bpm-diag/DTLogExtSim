from interarrival_rate_extraction_module.interarrival_rate_extraction import InterArrivalCalculation


def extract_interarrival_rate(self) -> None:
    """Estrae il tasso di inter-arrivo dal log."""
    try:
        print("Estraendo tasso di inter-arrivo...")
        self._inter_arrival_calc = InterArrivalCalculation(self.log, self.settings)

        # Calcolo completo
        results = self._inter_arrival_calc.calculate_interarrival_distribution()

        # Accesso ai risultati
        distribution_params = self._inter_arrival_calc._distribution_params
        interarrival_times = self._inter_arrival_calc._interarrival_times
        print("✓ Tasso di inter-arrivo estratto")
    except Exception as e:
        raise Exception(f"Errore nell'estrazione del tasso di inter-arrivo: {str(e)}")
    