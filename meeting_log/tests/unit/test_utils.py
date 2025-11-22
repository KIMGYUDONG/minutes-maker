from utils import chunk_text

def test_chunk_text():
    """
    Test that chunk_text splits a string into chunks of specified size.
    Input: A string with 3000 characters.
    Expected Output: A list of 2 strings (2000 chars, 1000 chars).
    """
    # Create a string of 3000 characters
    input_text = "a" * 3000
    
    # Call the function with a limit of 2000
    chunks = chunk_text(input_text, limit=2000)
    
    # Verify the results
    assert len(chunks) == 2
    assert len(chunks[0]) == 2000
    assert len(chunks[1]) == 1000
    assert chunks[0] == "a" * 2000
    assert chunks[1] == "a" * 1000
