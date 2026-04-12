import asyncio

# BROKEN: This global variable is shared across all async tasks.
# Task A will set this, then 'await'. Task B will then overwrite it.
request_store = {"id": None}

async def process_request(req_id):
    request_store["id"] = req_id
    
    # Simulate a database call or API hit
    await asyncio.sleep(1) 
    
    # By the time we get here, another request might have 
    # changed request_store["id"]
    return f"Finished request: {request_store['id']}"

async def main():
    # Simulate two concurrent requests
    results = await asyncio.gather(
        process_request("REQ-100"),
        process_request("REQ-200")
    )
    print(results) # Likely to show ['Finished request: REQ-200', 'Finished request: REQ-200']