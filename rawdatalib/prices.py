__package__ = "rawdatalib"

import oemof.iolib.csv_io as csv

class CsvPrice(object):

    def __init__(self, scenario):
        self.weather = csv.load_dict_from_csv("weather.csv")

    def get_timeseries(self, parameter):
        ts = {}

        for k,v in self.weather.items():
            ts[k] = v[parameter]

        return ts