import json
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import RetrievalQA

def main():
    # -----------------------------------------
    # 1) SET YOUR OPENAI API KEY
    # -----------------------------------------
    my_api_key = ""  # Replace with your actual key

    # -----------------------------------------
    # 2) LOAD THE SCRAPED DATA
    # -----------------------------------------
    JSON_FILE = "twz_articles.json"
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # Example article fields:
    #  {
    #      "Section": "Air",
    #      "Title": "Bunker Talk: Let’s Talk About...",
    #      "Link": "https://www.twz.com/news-features/bunker-talk...",
    #      "Author(s)": ["Tyler Rogoway"],
    #      "Date Posted": "Jan 22, 2025",
    #      "Date Updated": "Jan 23, 2025",
    #      "Updates": "...",
    #      "Full Article": "This is the entire text..."
    #  }

    # -----------------------------------------
    # 3) SPLIT TEXT INTO CHUNKS
    # -----------------------------------------
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""],
    )

    # We'll store the chunks as a list of LangChain `Document` objects.
    docs = []
    for article in articles:
        link = article.get("Link", "")
        title = article.get("Title", "")
        full_text = article.get("Full Article", "")

        # Optionally embed some additional fields in text if you want:
        combined_text = (
            f"TITLE: {title}\n"
            f"LINK: {link}\n"
            f"DATE_POSTED: {article.get('Date Posted','')}\n"
            f"DATE_UPDATED: {article.get('Date Updated','')}\n"
            f"AUTHORS: {','.join(article.get('Author(s)',[]))}\n"
            f"SECTION: {article.get('Section','')}\n"
            f"UPDATES: {article.get('Updates','')}\n\n"
            f"{full_text}"
        )

        # Split combined_text into smaller pieces:
        chunks = text_splitter.split_text(combined_text)
        for chunk in chunks:
            # Use metadata to store link + title (and anything else you want).
            # The chunk itself is the page_content.
            doc = Document(
                page_content=chunk,
                metadata={
                    "url": link,
                    "title": title,
                }
            )
            docs.append(doc)

    print(f"Total text chunks: {len(docs)}")

    # -----------------------------------------
    # 4) BUILD A FAISS VECTOR STORE
    # -----------------------------------------
    # Create embeddings with `api_key`
    embeddings = OpenAIEmbeddings(api_key=my_api_key)
    faiss_store = FAISS.from_documents(docs, embeddings)

    # -----------------------------------------
    # 5) CREATE RETRIEVAL Q&A CHAIN
    # -----------------------------------------
    retriever = faiss_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    chat_model = ChatOpenAI(
        api_key=my_api_key,
        model_name="gpt-3.5-turbo",
        temperature=0
    )

    # Return the source documents so we can show them to the user
    qa_chain = RetrievalQA.from_chain_type(
        llm=chat_model,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

    # -----------------------------------------
    # 6) CHATBOT LOOP
    # -----------------------------------------
    print("Chatbot is ready! Ask a question (type 'quit' to end).")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        # result is a dict with keys: "result" (the answer) and "source_documents".
        result = qa_chain(user_input)
        answer = result["result"]
        source_docs = result["source_documents"]

        print(f"\nChatbot: {answer}\n")

        # Show the source(s):
        print("Source(s) used:")
        for idx, doc in enumerate(source_docs, start=1):
            # doc.metadata["url"] / doc.metadata["title"]
            link = doc.metadata.get("url", "No link found")
            title = doc.metadata.get("title", "No title found")
            print(f"  {idx}. {title}\n     {link}")

        print()

    print("Goodbye!")

if __name__ == "__main__":
    main()
