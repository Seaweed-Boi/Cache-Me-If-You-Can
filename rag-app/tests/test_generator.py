from fastapi import FastAPI
from src.core.generator import ResponseGenerator

app = FastAPI()
generator = ResponseGenerator()

def test_response_generation():
    input_data = "Sample input for testing"
    expected_output = "Expected output based on input"
    assert generator.generate_response(input_data) == expected_output

def test_invalid_input():
    input_data = ""
    with pytest.raises(ValueError):
        generator.generate_response(input_data)