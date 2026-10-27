
def str2tuple(strings):
    """
    Convert string to tuple.
    
    :param strings: A string representing a tuple, e.g., "(1,2,3,4)"
    :return: Tuple with four integers or floats.
    """
    
    if strings == "None":
        return None
    
    try:
        # Remove spaces and parentheses, then split by comma
        cleaned = strings.replace('(', '').replace(')', '').replace(' ', '').split(',')
        # Convert strings to integers or floats
        return tuple(float(i) for i in cleaned)
    except:
        raise "Tuple must be four comma-separated numbers enclosed in parentheses"

def str2list(strings):
    """
    Convert string to str list.
    
    :param strings: A string representing a list, e.g., "[a,b,c,d]"
    :return: list with four string.
    """
    
    if strings == "None":
        return None
    
    try:
        # Remove spaces and parentheses, then split by comma
        cleaned = strings.replace('[', '').replace(']', '').replace(' ', '').split(',')
        # Convert strings to integers or floats
        return cleaned
    except:
        raise "list must be comma-separated strings enclosed in parentheses"


class user_fifo():
    '''
    FIFO
    '''
    def __init__(self, max_size_i):
        self.max_size = max_size_i
        self.clear()
    
    def clear(self):
        self.data = []
        self.fifo_data_num = 0
    
    # write a data into fifo
    # force_write_i, if true, when fifo full, the oldest data will be thrown away
    def push(self, data_i, force_write_i=False):
        if self.fifo_data_num >= self.max_size:
            if force_write_i:
                self.pop()
            else:
                return False
        
        self.data.append(data_i)
        self.fifo_data_num += 1
        return True
    
    # read a data out from fifo
    def pop(self):
        if self.fifo_data_num > 0:
            self.fifo_data_num -= 1
            return self.data.pop(0)
        else:
            return None
    
    def is_full(self):
        return self.fifo_data_num >= self.max_size
    
    def is_empty(self):
        return self.fifo_data_num == 0
    
    def get_data_num(self):
        return self.fifo_data_num
    
    def get_data(self, start_i=0, end_i=None):
        if start_i >= self.fifo_data_num:
            return None
        if end_i is None or end_i >= self.fifo_data_num or end_i == -1:
            return self.data[start_i:]
        else:
            return self.data[start_i:end_i+1]
    
    def get_max_data(self, start_i=0, end_i=None):
        data = self.get_data(start_i, end_i)
        if data is None:
            return None
        return max(data)
    
    def get_min_data(self, start_i=0, end_i=None):
        data = self.get_data(start_i, end_i)
        if data is None:
            return None
        return min(data)