# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

from dotenv import load_dotenv
import os 
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import os 
import google.generativeai as genai
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from app.gemini.tools.analista_tools import TOOLS_ANALISE
import json
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
