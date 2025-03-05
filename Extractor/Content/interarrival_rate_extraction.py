import pandas as pd
import numpy as np
from fitter import Fitter
from collections import Counter

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_intancetype = 'instanceType'

class InterArrivalCalculation():

    ''' This class is responsible for calculating the inter-arrival distribution and parameters, and also the types of instances if there are any '''

    def __init__(self, log, settings):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        
        print("--- Compute Distribution of interarrival ---")

        self._start_acts = self.extract_start_acts()
        self._intarr_list = self.interarrival_list_calculation()


        self._distribution_params = self.extract_distribution([x for x in self._intarr_list])

        self.save_on_file_interarrival()


    def extract_distribution(self, X):
        d = None
        most_common_elem, count = Counter(X).most_common(1)[0]
        if count > 0.9 * len(X):
            d = 'fixed'
            mean = 0
            if count == len(X):
                mean = 0 if X[0] == 0.00001 else X[0]
            else:
                mean = most_common_elem
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
            return [d, params]
        
        f = Fitter(X, distributions=['norm', 'expon', 'uniform', 'triang', 'lognorm', 'gamma'])
        #f = Fitter(X, distributions=['norm', 'expon', 'uniform'])
        f.fit()
        f.summary()
        d = list(f.get_best(method='sumsquare_error').keys())[0]
        params = self.extract_params(X, d)
        return [d, params]
    
    def extract_params(self, X, dtype):
        params = None
        if dtype == 'fixed':
            mean = 0 if X[0] == 0.00001 else X[0]
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype == 'norm':
            mean = np.mean(X)
            arg1 = np.std(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': 0}
        elif dtype == 'expon':
            mean = np.mean(X)
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype == 'uniform':
            mean = np.mean(X)
            arg1 = np.min(X)
            arg2 = np.max(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': round(arg2, 2)}
        elif dtype == 'triang':
            mean = np.mean(X)
            arg1 = np.min(X)
            arg2 = np.max(X)
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype in ['lognorm', 'gamma']:
            mean = np.mean(X)
            arg1 = np.var(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': 0}
        return params
        
    
    def interarrival_list_calculation(self):
        self._start_acts['date'] = self._start_acts[tag_to_identify_timestamp].dt.floor('d')
        inter_arrival_times = list()
        for key, group in self._start_acts.groupby('date'):
            daily_times = sorted(list(group[tag_to_identify_timestamp]))
            for i in range(1, len(daily_times)):
                delta = (daily_times[i] - daily_times[i-1]).total_seconds()
                if delta == 0: #to avoid problem with distribution calculation
                    delta = 0.00001
                inter_arrival_times.append(delta)
        return inter_arrival_times

    def extract_start_acts(self):
        min_timestamp_per_case = self._log.loc[self._log.groupby(tag_to_identify_trace)[tag_to_identify_timestamp].idxmin()]
        return min_timestamp_per_case.sort_values(by=tag_to_identify_timestamp)
    
    def save_on_file_interarrival(self):
        with open(self._path + 'output_data/output_file/interarrival' + self._name + '.txt', 'w') as file:
            file.write("Interarrival distribution and parameters\n")
            file.write(f"{self._distribution_params}\n")
    