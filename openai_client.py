import os
from llama_index.llms.azure_openai import AzureOpenAI
from typing import Optional, Dict, Any

def create_azure_openai_client(
    api_key: str,
    endpoint: str,
    api_version: str = "2025-03-01-preview",
    engine: str = "gpt-4.1",
    model: str = "gpt-4.1",
    temperature: float = 0.0,
    model_kwargs: Optional[Dict[str, Any]] = None
) -> AzureOpenAI:
    return AzureOpenAI(
        engine=engine,
        model=model,
        temperature=temperature,
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        model_kwargs=model_kwargs or {}
    )

if __name__ == "__main__":
    # 方式1
    llm = create_azure_openai_client(
        api_key="<YOUR_API_KEY>",
        endpoint="<YOUR_ENDPOINT>"
    )
    
    # 直接使用llama_index的方法
    response = llm.complete("你好")
    print(response)