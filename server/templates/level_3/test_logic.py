from processor import add_to_box

def test_accumulation():
    print("Running Test 1...")
    res1 = add_to_box("A")
    print(f"Call 1: {res1}")
    
    print("Running Test 2...")
    res2 = add_to_box("B")
    print(f"Call 2: {res2}")
    
    # If the bug is fixed, res2 should only be ['B']
    if len(res2) > 1:
        print("FAIL: List is accumulating items!")
        return False
    return True

if __name__ == "__main__":
    test_accumulation()