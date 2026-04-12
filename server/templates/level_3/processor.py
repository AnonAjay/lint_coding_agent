# BROKEN: The default list [] is created once at definition time.
def add_to_box(item, box=[]):
    box.append(item)
    return box

def clear_and_process(data):
    # This should return a fresh list every time, 
    # but currently it accumulates data from previous calls.
    return add_to_box(data)