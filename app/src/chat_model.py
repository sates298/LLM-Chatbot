from typing import Union, Optional
import openai
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

class DockerModelRunnerChatModel(ChatOpenAI):
    
    def _create_chat_result(
        self,
        response: Union[dict, openai.BaseModel],
        generation_info: Optional[dict] = None,
    ) -> ChatResult:
        response_dict = (
            response if isinstance(response, dict) else response.model_dump()
        )
        timings = response_dict.get("timings", None)
        chat_result = super()._create_chat_result(
            response=response, generation_info=generation_info
        )
        if timings:
            chat_result.llm_output["timings"] = timings
        return chat_result
    

