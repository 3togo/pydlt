from os import path
import logging
from .paths import process
from .misc import is_tensor

class Logger(object):
    """Logs values in a csv file.

    Args:
        name (str): Filename without extension.
        fields (list or tuple): Field names (column headers).
        directory (str, optional): Directory to save file (default '.').
        delimiter (str, optional): Delimiter for values (default ',').
        resume (bool, optional): If True it appends to an already existing
            file (default True).

    """
    def __init__(self, name, fields, directory=".",
                 delimiter=',', resume=True):
        self.filename = name + ".csv"
        self.directory = process(path.join(directory), True)
        self.file = path.join(self.directory, self.filename)
        self.fields = fields
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        # Write header
        if not resume or not path.exists(self.file):
            with open(self.file, 'w') as f:
                f.write(delimiter.join(fields)+ '\n')

        file_handler = logging.FileHandler(self.file)
        # Adding underscore to avoid clashes with reserved words from logging
        field_tmpl = delimiter.join(['%({0})s'.format('_' + x) for x in fields])
        file_handler.setFormatter(logging.Formatter(field_tmpl))
        self.logger.addHandler(file_handler)
        

    def __call__(self, values):
        """Same as :meth:`log`"""
        self.log(values)

    def _create_dict(self, values):
        ret = {'_' + key: '' for key in self.fields}
        ret.update({'_' + key: val.item() if is_tensor(val) else val
                    for key, val in values.items()})
        return ret

    def log(self, values):
        """Logs a row of values.

        Args:
            values (dict): Dictionary containing the names and values.
        """
        self.logger.info('', extra=self._create_dict(values))
        