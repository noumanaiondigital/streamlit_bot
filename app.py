import streamlit as st
import os
import time

from langchain.agents.openai_assistant import OpenAIAssistantRunnable


# interpreter_assistant = OpenAIAssistantRunnable.create_assistant(
#     name="langchain assistant",
#     instructions="Healthcare Billing Navigator embodies the persona of a revenue cycle manager with a medical background, blending professional expertise with a deep understanding of healthcare practices. This unique perspective allows it to interpret insurance updates not just from a billing standpoint, but also with an awareness of medical procedures and requirements. It presents information in a manner that is both professional and insightful, reflecting a dual focus on maximizing revenue and ensuring compliance with healthcare standards. The GPT communicates in a manner that is knowledgeable yet approachable, making complex insurance and medical terminologies accessible to its users. It strikes a balance between being detail-oriented and efficient, providing summaries that are not only informative but also easy to understand and act upon for hospital revenue optimization. You provide an executive summary of the changes that affect billing for the hospital revue cycle manager. You will receive latest updates from a Healthcare insurance company. Review all of them, then produce the report. If the output is large, ask to continue. The report needs to be clear and detailed for the items identified.",
#     tools=[{"type": "code_interpreter"}],
#     model="gpt-4-1106-preview",
# )

from openai import OpenAI
assistant_client_obj = OpenAI()



def submit_message_assistant(prompt: str, assistant_client: str, thread_id: str):
    user_prompt = f"""
    Please generate a beautiful summary and answer any followup question from the attached File.
    Your job is to understand and summarzie already attached files and then put a little description in my final summary.
    {prompt}
    Please return the beautiful final summary only.
    """
    message = assistant_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_prompt
    )
    run = assistant_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id= "asst_QWJw2IJ74RfepAAvROGhCYXl",
    )
    return run


def wait_on_run(run, assistant_client, thread_id):
    while run.status == "queued" or run.status == "in_progress":
        run = assistant_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        time.sleep(3)
    return run

def create_thread():
    thread_details = assistant_client_obj.beta.threads.create()
    return thread_details.id, assistant_client_obj

thread_details = assistant_client_obj.beta.threads.create()


def get_response(assistant_client, thread_id):
    return assistant_client.beta.threads.messages.list(thread_id=thread_id, order="asc")


thread_id, assistant_client = create_thread()




# os.environ["OPENAI_API_KEY"] = "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"

# create sidebar and ask for openai api key if not set in secrets
secrets_file_path = os.path.join(".streamlit", "secrets.toml")
if os.path.exists(secrets_file_path):
    try:
        if "OPENAI_API_KEY" in st.secrets:
            os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
        else:
            print("OpenAI API Key not found in environment variables")
    except FileNotFoundError:
        print('Secrets file not found')
else:
    print('Secrets file not found')

if not os.getenv('OPENAI_API_KEY', '').startswith("sk-"):
    os.environ["OPENAI_API_KEY"] = st.sidebar.text_input(
        "OpenAI API Key", type="password"
    )
else:
    pass

# create the app
st.title("ALIVIA AI - Revenue Cycle Assistant")

chosen_file = st.radio(
    "Choose a Healthcare provider to find Latest Updates", ["Aetna", "Anthem", "Cigna Network", "OptimaHealth", "United Healthcare"], index=0
)

chosen_file = chosen_file + ".pdf"
# check if openai api key is set
if not os.getenv('OPENAI_API_KEY', '').startswith("sk-"):
    st.warning("Please enter your OpenAI API key!", icon="⚠")
    st.stop()

# load the agent
from llm_helper import convert_message, get_rag_chain, get_rag_fusion_chain

get_rag_chain_func = get_rag_chain
## get the chain WITHOUT the retrieval callback (not used)
# custom_chain = get_rag_chain_func(chosen_file)

# create the message history state
if "messages" not in st.session_state:
    st.session_state.messages = []

# render older messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# render the chat input
prompt = st.chat_input("Enter your message...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    # render the user's new message
    with st.chat_message("user"):
        st.markdown(prompt)

    # render the assistant's response
    with st.chat_message("assistant"):
        retrival_container = st.container()
        message_placeholder = st.empty()

        retrieval_status = retrival_container.status("**Analyzing**")
        queried_questions = []
        rendered_questions = set()
        def update_retrieval_status():
            for q in queried_questions:
                if q in rendered_questions:
                    continue
                rendered_questions.add(q)
                retrieval_status.markdown(f"\n\n`- {q}`")
        def retrieval_cb(qs):
            for q in qs:
                if q not in queried_questions:
                    queried_questions.append(q)
            return qs
        
        # get the chain with the retrieval callback
        custom_chain = get_rag_chain_func(chosen_file, retrieval_cb=retrieval_cb)
        
        if "messages" in st.session_state:
            chat_history = [convert_message(m) for m in st.session_state.messages[:-1]]
        else:
            chat_history = []



        run = submit_message_assistant(prompt, assistant_client, thread_id)
        wait_on_run(run, assistant_client, thread_id)
        response = get_response(assistant_client, thread_id)
        full_response = response.data[-1].content[0].text.value
        # for response in custom_chain.stream(
        #     {"input": prompt, "chat_history": chat_history}
        # ):
        #     if "output" in response:
        #         full_response += response["output"]
        #     else:
        #         full_response += response.content

        message_placeholder.markdown(full_response + "▌")
        update_retrieval_status()

        retrieval_status.update(state="complete")
        message_placeholder.markdown(full_response)

    # add the full response to the message history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
