import streamlit as st
import requests
import json
import random
from sseclient import SSEClient
from urllib.parse import quote

def sse_with_requests(url, headers) -> requests.Response:
    """Get a streaming response for the given event feed using requests."""
    return requests.get(url, stream=True, headers=headers)

class DocumentPicker:

    def __init__(self, base_url):
        self.base_url = base_url
        self.documents = None
        self.selected_documents = []

    def fetch(self):
        response = requests.get(f"{self.base_url}/api/document/")
        if response.status_code == 200:
            self.documents = random.choices(response.json(), k=5)
            return self.documents
        else:
            st.write(f"Error: {response.text}")
            return []

    def fetch_and_display(self):
        self.fetch()
        docs = {doc['url']: doc for doc in self.documents}
        return docs

    def select(self, selected_doc_key):
        selected_doc = [doc for doc in self.documents if f"{doc['id']} - {doc['url']}" == selected_doc_key][0]
        self.selected_documents.append(selected_doc)
        return selected_doc
    
    def select_by_id(self, entered_id):
        response = requests.get(f"{self.base_url}/api/document/{entered_id}")
        if response.status_code == 200:
            doc = response.json()
            self.selected_documents.append(doc)
            return doc
        else:
            st.write("Invalid ID.")
            return None


class Conversation:

    def __init__(self, base_url):
        self.base_url = base_url
        self.conversation_id = None
        self.document_ids = []

    def pick_docs(self, picker):
        picker.fetch()
        doc_idx = st.selectbox("Select a document:", range(len(picker.documents)))
        doc = picker.select(doc_idx)
        self.document_ids = [doc["id"]]
        st.write(f"Selected document: {doc['url']}")

    def create(self):
        req_body = {"document_ids": self.document_ids}
        response = requests.post(f"{self.base_url}/api/conversation/", json=req_body)
        if response.status_code == 200:
            self.conversation_id = response.json()["id"]
            st.write(f"Created conversation with ID {self.conversation_id}")
        else:
            st.write(f"Error: {response.text}")

    def detail(self):
        if not self.conversation_id:
            st.write("No active conversation. Use CREATE to start a new conversation.")
            return
        response = requests.get(f"{self.base_url}/api/conversation/{self.conversation_id}")
        if response.status_code == 200:
            st.write(response.json())
        else:
            st.write(f"Error: {response.text}")

    def delete(self):
        if not self.conversation_id:
            st.write("No active conversation to delete.")
            return
        response = requests.delete(f"{self.base_url}/api/conversation/{self.conversation_id}")
        if response.status_code == 204:
            st.write(f"Deleted conversation with ID {self.conversation_id}")
            self.conversation_id = None
        else:
            st.write(f"Error: {response.text}")

    def message(self, user_message):
        if not self.conversation_id:
            st.write("No active conversation. Use CREATE to start a new conversation.")
            return
        message = quote(user_message)
        url = f"{self.base_url}/api/conversation/{self.conversation_id}/message?user_message={message}"
        headers = {"Accept": "text/event-stream"}
        response = sse_with_requests(url, headers)
        messages = SSEClient(response).events()
        for msg in messages:
            msg_json = json.loads(msg.data)
            st.write(msg_json)

def main():
    st.title("Streamlit Chatbot")

    # Initialize or Retrieve state
    if 'base_url' not in st.session_state:
        st.session_state.base_url = "http://localhost:8000"
    if 'selected_document' not in st.session_state:
        st.session_state.selected_document = None
    if 'conversation' not in st.session_state:
        st.session_state.conversation = Conversation(st.session_state.base_url)

    base_url = st.text_input("Enter the base URL for API endpoints", st.session_state.base_url)
    st.session_state.base_url = base_url

    picker = DocumentPicker(base_url)

    if st.button("Fetch Documents"):
        picker.fetch_and_display()  # Populate picker.documents with available options

    entered_id = st.text_input("Enter Document ID:")

    if st.button("Pick Document by ID"):
        selected_doc = picker.select_by_id(entered_id)
        if selected_doc:
            st.session_state.selected_document = selected_doc
            st.session_state.conversation.document_ids = [st.session_state.selected_document["id"]]


    if st.button("Create"):
        st.session_state.conversation.create()

    if st.button("Details"):
        st.session_state.conversation.detail()

    if st.button("Delete"):
        st.session_state.conversation.delete()

    user_message = st.text_input("Your message:")
    if st.button("Send Message"):
        st.session_state.conversation.message(user_message)

if __name__ == "__main__":
    main()