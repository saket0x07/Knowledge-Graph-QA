import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import requests
import time

# --- Constants ---
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="RAG Explorer", layout="wide")

st.markdown("""
<style>
    /* Clean layout styling */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    .stChatInputContainer {
        border-radius: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "document_filename" not in st.session_state:
    st.session_state.document_filename = "Global (All Documents)"
if "graph_ready" not in st.session_state:
    st.session_state.graph_ready = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Sidebar Navigation ---
st.sidebar.title("RAG Explorer")
st.sidebar.caption("v1.2.4")

page = st.sidebar.radio(
    "Navigation",
    ["Ingestion", "Knowledge Graph", "Chat / Q&A"]
)

st.sidebar.markdown("---")

# Fetch history for dropdown
try:
    history_res = requests.get(f"{API_BASE_URL}/documents/history", timeout=5)
    if history_res.status_code == 200:
        history = history_res.json()
        success_docs = [item["filename"] for item in history if item["status"] == "Success"]
        unique_docs = list(dict.fromkeys(success_docs))
    else:
        unique_docs = []
except Exception:
    unique_docs = []

kb_options = ["Global (All Documents)"] + unique_docs

if st.session_state.document_filename not in kb_options:
    st.session_state.document_filename = kb_options[0]

default_idx = kb_options.index(st.session_state.document_filename)

selected_kb = st.sidebar.selectbox(
    "Select Knowledge Base",
    options=kb_options,
    index=default_idx
)

if selected_kb != st.session_state.document_filename:
    st.session_state.document_filename = selected_kb
    st.session_state.graph_ready = (selected_kb != "Global (All Documents)")
    st.rerun()

st.sidebar.markdown("---")

# --- View 1: Ingestion ---
if page == "Ingestion":
    st.title("Data Ingestion Engine")
    st.markdown("Connect your enterprise documents to the RAG pipeline. Our engine extracts semantic relationships and entity links to build your private knowledge graph.")
    st.markdown("---")
    
    col_upload, col_history = st.columns([1.5, 1])
    
    with col_upload:
        st.markdown("### Upload Document")
        st.markdown("""
        <div style='border: 2px dashed #CBD5E1; padding: 2rem; border-radius: 0.5rem; text-align: center; background-color: white;'>
            <h4 style='color: #0047AB;'>Drop files to ingest</h4>
            <p style='color: #64748B; font-size: 0.9rem;'>PDF files supported. (Max 50MB per file)</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Browse Local Files", type=["pdf"], label_visibility="hidden")
        
        if uploaded_file is not None and uploaded_file.name != st.session_state.document_filename:
            st.session_state.document_filename = uploaded_file.name
            st.session_state.graph_ready = False
            st.session_state.chat_history = []
            
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    res = requests.post(f"{API_BASE_URL}/documents/upload", files=files, timeout=30)
                    if res.status_code == 200:
                        st.success("Upload successful! Processing started.")
                        
                        status_placeholder = st.empty()
                        max_retries = 60
                        retries = 0
                        while retries < max_retries:
                            status_res = requests.get(f"{API_BASE_URL}/documents/status/{uploaded_file.name}", timeout=5)
                            if status_res.status_code == 200:
                                status = status_res.json().get("status")
                                if status == "completed":
                                    status_placeholder.success("Graph extraction complete!")
                                    st.session_state.graph_ready = True
                                    st.rerun()
                                    break
                                elif status.startswith("error"):
                                    status_placeholder.error(f"Processing failed: {status}")
                                    break
                                else:
                                    status_placeholder.info("Extracting entities and building Knowledge Graph... (this may take a minute)")
                            time.sleep(3)
                            retries += 1
                    else:
                        st.error("Failed to upload document.")
                except Exception as e:
                    st.error(f"Upload request error: {e}")
                    
        if st.session_state.graph_ready:
            st.markdown("---")
            st.markdown("**CURRENT EXTRACTION PROGRESS**")
            st.markdown(f"**{st.session_state.document_filename}**")
            st.progress(100)
            
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.info("Entities \n\n **Extracted**")
            with mc2:
                st.info("Edges \n\n **Mapped**")
            with mc3:
                st.info("Triples \n\n **Generated**")
                
    with col_history:
        st.markdown("### Ingestion History")
        try:
            history_res = requests.get(f"{API_BASE_URL}/documents/history", timeout=5)
            if history_res.status_code == 200:
                history = history_res.json()
                if not history:
                    st.write("No ingestion history found.")
                for item in history:
                    bg_color = "#F1F5F9"
                    border_color = "#CBD5E1"
                    status_color = "#3B82F6"
                    icon = "🔄"
                    
                    if item['status'] == "Success":
                        bg_color = "#F0FDF4"
                        border_color = "#BBF7D0"
                        status_color = "#16A34A"
                        icon = "✅"
                    elif item['status'] == "Failed":
                        bg_color = "#FEF2F2"
                        border_color = "#FECACA"
                        status_color = "#DC2626"
                        icon = "❌"
                        
                    st.markdown(f"""
                    <div style='background-color: {bg_color}; border: 1px solid {border_color}; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <strong>{icon} {item['filename']}</strong><br/>
                                <span style='color: {status_color}; font-size: 0.85rem;'>{item['status']} &bull; {item['file_size_mb']} MB</span>
                            </div>
                            <span style='font-size: 0.75rem; color: #94A3B8;'>{item['timestamp'].split(' ')[0]}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("Could not retrieve history.")
        except Exception as e:
            st.error(f"Failed to fetch history: {e}")

# --- View 2: Knowledge Graph ---
elif page == "Knowledge Graph":
    st.title("Knowledge Graph Visualizer")
    
    if not st.session_state.document_filename or st.session_state.document_filename == "Global (All Documents)":
        st.warning("Please select a specific document from the sidebar dropdown to visualize its Knowledge Graph. Global visualization across all documents is disabled to prevent browser memory overflow.")
    else:
        st.markdown(f"**Source Document:** `{st.session_state.document_filename}`")
        st.markdown("---")
        
        col_graph, col_details = st.columns([2.5, 1])
        
        raw_nodes = []
        raw_edges = []
        
        with st.spinner("Loading graph data..."):
            try:
                graph_res = requests.get(f"{API_BASE_URL}/graph/visualize/{st.session_state.document_filename}", timeout=10)
                if graph_res.status_code == 200:
                    data = graph_res.json()
                    raw_nodes = data.get("nodes", [])
                    raw_edges = data.get("edges", [])
                else:
                    st.error(f"Failed to fetch graph data (Status {graph_res.status_code}).")
            except Exception as e:
                st.error(f"Error connecting to graph API: {e}")
            
        nodes = []
        edges = []
        
        color_map = {
            "Document": "#f56565",
            "Chunk": "#ed8936",
            "Disease": "#4299e1",
            "Treatment": "#9f7aea",
            "Symptom": "#48bb78"
        }
        
        for n in raw_nodes:
            color = color_map.get(n.get("group"), "#a0aec0")
            nodes.append(Node(id=n["id"], label=n["label"], size=25, color=color))
        
        for e in raw_edges:
            edges.append(Edge(source=e["from"], label=e["label"], target=e["to"], type="CURVE_SMOOTH"))
        
        config = Config(
            width="100%", 
            height=600, 
            directed=True,
            nodeHighlightBehavior=True, 
            highlightColor="#F7A7A6",
            collapsible=False,
            node={'labelProperty': 'label'},
            link={'labelProperty': 'label', 'renderLabel': True}
        )
        
        clicked_node_id = None
        with col_graph:
            if nodes:
                clicked_node_id = agraph(nodes=nodes, edges=edges, config=config)
            else:
                st.info("No entity nodes extracted for this document yet.")
            
        with col_details:
            st.markdown("### Node Details")
            if clicked_node_id:
                selected_node = next((n for n in raw_nodes if n["id"] == clicked_node_id), None)
                if selected_node:
                    group_color = color_map.get(selected_node.get("group"), "#a0aec0")
                    st.markdown(f"""
                    <div style='border: 1px solid #CBD5E1; border-radius: 0.5rem; padding: 1.5rem; background-color: white;'>
                        <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                            <div style='width: 40px; height: 40px; border-radius: 50%; background-color: {group_color}; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; margin-right: 1rem;'>
                                {selected_node.get('group', 'E')[0].upper()}
                            </div>
                            <h3 style='margin: 0; color: #0F172A;'>{selected_node.get('label')}</h3>
                        </div>
                        <span style='background-color: #F1F5F9; color: #475569; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;'>
                            {selected_node.get('group', 'Entity')}
                        </span>
                        <hr style='margin: 1.5rem 0;'/>
                        <h5 style='color: #64748B; font-size: 0.8rem; margin-bottom: 0.5rem; text-transform: uppercase;'>Description</h5>
                        <p style='color: #334155; font-size: 0.9rem;'>
                            Extracted entity from the document knowledge graph.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<h5 style='color: #64748B; font-size: 0.8rem; margin-top: 1.5rem; margin-bottom: 0.5rem; text-transform: uppercase;'>Connected Entities</h5>", unsafe_allow_html=True)
                    connected_edges = [e for e in raw_edges if e["from"] == clicked_node_id or e["to"] == clicked_node_id]
                    
                    if connected_edges:
                        for edge in connected_edges:
                            is_source = edge["from"] == clicked_node_id
                            other_node_id = edge["to"] if is_source else edge["from"]
                            other_node = next((n for n in raw_nodes if n["id"] == other_node_id), None)
                            if other_node:
                                direction = "Outgoing" if is_source else "Incoming"
                                st.markdown(f"""
                                <div style='background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.75rem; border-radius: 0.25rem; margin-bottom: 0.5rem;'>
                                    <div style='font-weight: 600; color: #1E293B; font-size: 0.9rem;'>{other_node.get('label')}</div>
                                    <div style='color: #64748B; font-size: 0.75rem;'>{direction} &bull; {edge['label']}</div>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #94A3B8; font-size: 0.85rem;'>No connections found.</p>", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='border: 1px dashed #CBD5E1; border-radius: 0.5rem; padding: 2rem; text-align: center; background-color: #F8FAFC;'>
                    <p style='color: #64748B;'>Click on any node in the graph to view its details and connections.</p>
                </div>
                """, unsafe_allow_html=True)

# --- View 3: Chat / Q&A ---
elif page == "Chat / Q&A":
    st.title("Chat & Q&A")
    st.markdown(f"**Knowledge Base Scope:** `{st.session_state.document_filename}`")
    st.markdown("---")

    col_recent, col_chat = st.columns([1, 2.5])
    
    with col_recent:
        st.markdown("<h3 style='color: #0047AB;'>GraphMind Explorer</h3>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 0.5rem 0;'/>", unsafe_allow_html=True)
        
        st.markdown("#### Recent Queries")
        
        user_queries = [m["content"] for m in st.session_state.chat_history if m["role"] == "user"]
        if not user_queries:
            st.markdown("<p style='color: #94A3B8; font-size: 0.9rem;'>No recent queries.</p>", unsafe_allow_html=True)
        else:
            for q in reversed(user_queries[-5:]):
                st.markdown(f"""
                <div style='background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.75rem; border-radius: 0.5rem; margin-bottom: 0.5rem;'>
                    <div style='font-weight: 600; color: #1E293B; font-size: 0.9rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;'>{q}</div>
                    <div style='color: #64748B; font-size: 0.75rem; margin-top: 0.25rem;'>Just now</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("<hr style='margin: 1.5rem 0 0.5rem 0;'/>", unsafe_allow_html=True)
        st.markdown("#### Saved Insights")
        st.markdown("""
        <div style='margin-bottom: 0.5rem;'>
            <div style='font-weight: bold; color: #0047AB; font-size: 0.9rem;'>🔖 Entity overlap detected</div>
            <div style='color: #64748B; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;'>High Confidence</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_chat:
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
                    if msg["role"] == "assistant":
                        if msg.get("cypher"):
                            st.markdown(f"""
                            <div style='background-color: #1E293B; color: #F8FAFC; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem; margin-bottom: 1rem; font-family: monospace; font-size: 0.85rem;'>
                                <div style='color: #94A3B8; font-size: 0.7rem; font-weight: bold; margin-bottom: 0.5rem; text-transform: uppercase;'>Inference Path (Cypher/SQL)</div>
                                {msg['cypher']}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        if msg.get("sources"):
                            st.markdown("<div style='color: #64748B; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; margin-bottom: 0.5rem;'>Sources Found</div>", unsafe_allow_html=True)
                            sources_html = ""
                            for src in msg["sources"]:
                                sources_html += f"<span style='background-color: white; border: 1px solid #CBD5E1; color: #475569; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.5rem;'>📄 {src}</span>"
                            st.markdown(sources_html, unsafe_allow_html=True)
        
        prompt = st.chat_input("Ask about your knowledge graph...")

        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        prompt = st.session_state.chat_history[-1]["content"]
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing Graph..."):
                    try:
                        payload = {"query": prompt, "top_k": 5}
                        if st.session_state.document_filename and st.session_state.document_filename != "Global (All Documents)":
                            payload["filename"] = st.session_state.document_filename
                            
                        res = requests.post(f"{API_BASE_URL}/qa/ask", json=payload, timeout=60)
                        if res.status_code == 200:
                            data = res.json()
                            answer = data.get("answer", "No answer generated.")
                            cypher = data.get("cypher_query", "")
                            sources = data.get("sources", [])
                            
                            st.write(answer)
                            
                            if cypher:
                                st.markdown(f"""
                                <div style='background-color: #1E293B; color: #F8FAFC; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem; margin-bottom: 1rem; font-family: monospace; font-size: 0.85rem;'>
                                    <div style='color: #94A3B8; font-size: 0.7rem; font-weight: bold; margin-bottom: 0.5rem; text-transform: uppercase;'>Inference Path (Cypher/SQL)</div>
                                    {cypher}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if sources:
                                st.markdown("<div style='color: #64748B; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; margin-bottom: 0.5rem;'>Sources Found</div>", unsafe_allow_html=True)
                                sources_html = ""
                                for src in sources:
                                    sources_html += f"<span style='background-color: white; border: 1px solid #CBD5E1; color: #475569; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.5rem;'>📄 {src}</span>"
                                st.markdown(sources_html, unsafe_allow_html=True)
                            
                            st.session_state.chat_history.append({
                                "role": "assistant", 
                                "content": answer,
                                "cypher": cypher,
                                "sources": sources
                            })
                            st.rerun()
                        else:
                            st.error(f"Error from API: {res.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API: {e}")
