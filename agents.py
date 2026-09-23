from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_Search,scrape_url
from rich import print
import os
from dotenv import load_dotenv
load_dotenv()

llm=ChatGroq(model="openai/gpt-oss-120b",temperature=0)

def search_agent():
    return create_agent(
        model=llm,
        tools=[web_Search]
    )


def reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url]
    )




# chains

# writer_chain

writer_prompt=ChatPromptTemplate.from_messages([
    ("system", "you are an expert research writer . write clear, structured and insightful reports."
    ),
    ("human","""write a detailed research reports on the topic below.
    topic:{topic}

    research gathered :{research}
    structure the report as :
    -introduction
    -key findings (minimum 3 well-explained points)
    -conclusion
    -sources (list all urls dound in the research)

    be detailed , factual and professional.""")

])

writer_chain=writer_prompt| llm | StrOutputParser()


# critic_chain


critic_prompt=ChatPromptTemplate.from_messages([
    ("system","you are a sharp and constructive research critc, be honest and specific"),
    ("human","""review the research report below and evaluate it strictly.
    report : {report}
    respond in this exact format :
    score :x/10
    strengths : - ...
    areas to improve : -...
    one line verdict: ..."""
    )
])

critic_chain=critic_prompt | llm | StrOutputParser()