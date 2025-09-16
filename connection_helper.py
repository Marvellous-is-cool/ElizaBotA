import asyncio
from typing import Callable, Any, Coroutine
from aiohttp.client_exceptions import ClientConnectionError, ClientConnectorError, ClientConnectionResetError

async def with_retry(func: Callable[..., Coroutine[Any, Any, Any]], *args, max_retries=3, initial_delay=1, **kwargs):
    """
    Execute an async function with retry logic for connection issues.
    
    Args:
        func: The async function to call
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retries before giving up
        initial_delay: Initial delay in seconds before retrying (doubles with each retry)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function if successful
        
    Raises:
        The last exception encountered if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except (ClientConnectionResetError, ClientConnectorError, ClientConnectionError) as e:
            last_exception = e
            if attempt == max_retries:
                raise  # Re-raise if we've exhausted retries
            
            print(f"Connection error (attempt {attempt+1}/{max_retries+1}): {e}")
            print(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    
    # This should never be reached due to the raise in the except block
    raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")
