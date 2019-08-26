import csv
from datetime import datetime
import settings.app_settings as app_settings
import os
import errno

class EventLog:
    def __init__(self, directory, header):
        self.header = header
        file_name = datetime.now().strftime('%Y%m%d-%H%M%S' + '.csv')
        self.file_path = os.path.join(directory, file_name)

        # create directory structure if it doesn't already exist
        if not os.path.exists(os.path.dirname(self.file_path)):
            try:
                os.makedirs(os.path.dirname(self.file_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def write(self, data):
        with open(self.file_path, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(self.header)
            writer.writerow(data)

if __name__ == '__main__':

    header = [('Row ' + str(i)) for i in range(0, app_settings.flame_detect_len)]
    data = [(str(i)) for i in range(0, app_settings.flame_detect_len)]

    event_log = EventLog(directory = os.path.join(app_settings.flame_log_dir, 'alarm_counters'), header = header)
    event_log.write(data)