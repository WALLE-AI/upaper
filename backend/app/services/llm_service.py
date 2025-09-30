from ..llm.models import OpenAIServerModel
import yaml
from ..llm.prompts.translate import translate_system_prompt
import os
import importlib


def llm_result_postprocess(llm_response_content):
    ##json的后处理
    from json_repair import repair_json
    json_string = repair_json(llm_response_content, return_objects=True)
    return json_string
class LLMService:
    def __init__(self):
        self.model = OpenAIServerModel(
            api_base=os.getenv('LOCAL_QWEN3_INSTRUCT_BASE'),
            api_key="empty",
            model_id="Qwen3-30B-A3B-Instruct-2507",
        )

    def get_model(self):
        return self.model

    def generate_stream(self, messages: list[dict]):
        return self.model.generate_stream(messages)

    def generate(self, messages: list[dict]):
        return self.model.generate(messages)
    
    def get_paper_analyze_stream(self, paper_id: str):
        return self.model.generate_stream([{"role": "user", "content": "What is the capital of France?"}])
    
    def get_paper_translate(self, translate_content: str):
        system_prompt = translate_system_prompt
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": translate_content}]
        translate = self.model.generate(messages)
        translate = llm_result_postprocess(translate.content)
        translate = translate.get("zh") if isinstance(translate, dict) else ""
        return translate
    
    def get_paper_translate_stream(self, paper_id: str):
        prompt_templates = prompt_templates or yaml.safe_load(
                importlib.resources.files("llm.prompts").joinpath("translate.yaml").read_text()
            )
        return self.model.generate_stream([{"role": "user", "content":prompt_templates}])
    
    def get_paper_chat_stream(self, paper_id: str):
        return self.model.generate_stream([{"role": "user", "content": "What is the capital of France?"}])
    
    def get_paper_interpret_stream(self, paper_id: str):
        return self.model.generate_stream([{"role": "user", "content": "What is the capital of France?"}])
    
    
llm_service = LLMService()