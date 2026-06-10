from dotenv import load_dotenv
from app.agents.llm import get_llm
from langchain_core.messages import HumanMessage

load_dotenv()

llm = get_llm()

response = llm.invoke([
    HumanMessage(content="Say hello and plan a simple 1-day trip to Tokyo.")
])

print(response.content)