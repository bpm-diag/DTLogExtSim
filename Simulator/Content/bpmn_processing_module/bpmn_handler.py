import json


class BPMNHandler:
    def __init__(self, simulation_path, simulation_no_ext, extra_path, process_path):
        self.simulation_path = simulation_path
        self.simulation_no_ext = simulation_no_ext
        self.extra_path = extra_path
        self.process_path = process_path

        self.process_data = None
        self.extra_data = None

    def load_configuration_files(self):
        try:
            with open(self.process_path, 'r') as file:
                self.process_data = json.load(file)
        except FileNotFoundError:
            print(f"-----ERROR-----: bpmn file not found")
            raise ValueError("-----ERROR-----: bpmn file not found")
        except json.JSONDecodeError:
            print(f"-----ERROR-----: bpmn file bad syntax")
            raise ValueError("-----ERROR-----: bpmn file bad syntax")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise ValueError("An error occurred: {e}")


        try:
            with open(self.extra_path, 'r') as file:
                self.extra_data = json.load(file)
        except FileNotFoundError:
            print(f"-----ERROR-----: extra file not found")
            raise ValueError("-----ERROR-----: extra file not found")
        except json.JSONDecodeError:
            print(f"-----ERROR-----: extra file bad syntax")
            raise ValueError("-----ERROR-----: extra file bad syntax")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise ValueError("An error occurred: {e}")
        
