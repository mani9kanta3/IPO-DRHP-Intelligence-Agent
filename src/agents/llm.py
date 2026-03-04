import os
from dotenv import load_dotenv

load_dotenv()

def get_llm(complex_task: bool = True):
    provider = os.getenv("LLM_PROVIDER", "gemini")
        
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )  

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        model = "gpt-4o" if complex_task else "gpt-4o-mini"
        return ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


if __name__ == "__main__":
    llm = get_llm(complex_task=False)
    response = llm.invoke("Say 'LLM is ready!' and nothing else.")
    print(response.content)