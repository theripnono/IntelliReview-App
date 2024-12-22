import os
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter,CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate


# Todo search for multiple business

#setup
apikey = os.environ['OPENAI_API_KEY']
os.environ["TOKENIZERS_PARALLELISM"] = "false"

llm = ChatOpenAI(openai_api_key=apikey)

chain = load_qa_chain(llm, chain_type="stuff")


def csv_to_text(csv_file):
    """
    Funtion that it transforms the csv into a plain text
    """
    text = ''
    df = pd.read_csv(csv_file, sep=';')
    new_df = df[['comment', 'date']].copy()
    df_dict = new_df.to_dict(orient='records')
    for row in df_dict:
        text += row['comment'] + 'fecha del comentario ' + row['date'] + '\n\n'

    return text


csv_reviews = pd.DataFrame('data.csv')

text_content = csv_to_text(csv_reviews)

#text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100, length_function=len)

text_splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=2000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

docs = text_splitter.split_text(text_content)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

#Vectorestore
vectorstore = FAISS.from_texts(docs, embeddings) # local dbstore
retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 6})

def format_docs(docs):

    return "\n\n".join(doc.page_content for doc in docs)

template = """Eres un agente especilizado en dar información detallada sobre las
                opiniones de los usuarios, para analizar y mejorar la experiencia.
                Si no sabes la respuesta, di simplemente que no la sabes,
                no intentes inventarte una respuesta. Si conoces la fecha, mencionala
                Utiliza tres frases como máximo y procura que la respuesta sea 
                lo más concreta posible.

{context}

Question: {question}

Respuestas útiles:"""
custom_rag_prompt = PromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | custom_rag_prompt
    | llm
    | StrOutputParser()
)

