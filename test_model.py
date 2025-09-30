import os
from app.llm.models import OpenAIServerModel


from dotenv import load_dotenv
load_dotenv()

model_name = "Qwen3-30B-A3B-Thinking-2507"
api_key = "empty"
api_base = os.getenv('LOCAL_QWEN3_THINKING_BASE')

def test_model():   
    model = OpenAIServerModel(
        api_base=api_base,
        api_key=api_key,
        model_id=model_name,
    )
    response = model.generate_stream([{"role": "user", "content": "What is the capital of France?"}])
    for chunk in response:
        print(chunk.content, end="", flush=True)

if __name__ == "__main__":
    test_model()



