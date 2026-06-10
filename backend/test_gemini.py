from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
)

response = llm.invoke("Say hello and plan a simple 1-day trip to Tokyo.")
print(response.content)