import streamlit as st
import requests

# -------------------- Page Configuration --------------------
st.set_page_config(
    page_title="Legal Case Search",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://localhost:8000"

# -------------------- Custom CSS --------------------
st.markdown("""
<style>
.main { padding: 2rem; }
.case-title { font-size: 20px; font-weight: bold; color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

# -------------------- Title --------------------
st.title("⚖️ Legal Case Search System")
st.markdown("### AI-Powered Semantic Search for Supreme Court Cases")
st.markdown("---")

# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("📊 System Information")

    try:
        r = requests.get(f"{API_URL}/stats")
        if r.status_code == 200:
            stats = r.json()
            st.metric("Total Cases", f"{stats['total_cases']:,}")
            st.metric("Searchable Cases", f"{stats['searchable_cases']:,}")
            st.metric("Coverage", stats['coverage_percentage'])
        else:
            st.error("Could not load statistics")
    except Exception as e:
        st.error(f"API error: {e}")

    st.markdown("---")
    num_results = st.slider("Number of results", 1, 20, 10)

# -------------------- Search Input --------------------
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "🔍 Search for similar legal cases",
        placeholder="e.g., employee termination without notice period"
    )

with col2:
    st.write("")
    st.write("")
    search_button = st.button("🔎 Search", use_container_width=True)

# -------------------- Example Queries --------------------
st.markdown("**💡 Example queries:**")
c1, c2, c3 = st.columns(3)

if c1.button("👔 Employment Dispute"):
    search_query = "employee termination without notice period"
    search_button = True

if c2.button("🏠 Property Dispute"):
    search_query = "property dispute between family members"
    search_button = True

if c3.button("📄 Contract Breach"):
    search_query = "contract breach and compensation"
    search_button = True

st.markdown("---")

# -------------------- Search Results --------------------
if search_button and search_query:
    with st.spinner("🔍 Searching cases..."):
        try:
            response = requests.get(
                f"{API_URL}/search",
                params={"q": search_query, "top_k": num_results}
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                st.success(f"✅ Found {len(results)} similar cases for **{search_query}**")

                for i, result in enumerate(results, 1):
                    title = result.get("title", "Unknown Case")
                    court = result.get("court", "Unknown")
                    date = result.get("date") or "Not available"
                    case_id = result.get("case_id", "N/A")
                    summary = result.get("summary", "No summary available")
                    petitioner = result.get("petitioner", "")
                    respondent = result.get("respondent", "")
                    citations = result.get("citations", [])

                    with st.expander(
                        f"**{i}. {title}**",
                        expanded=(i == 1)
                    ):
                        col_info, col_meta = st.columns([2, 1])

                        with col_info:
                            st.markdown(f"**Court:** {court}")
                            st.markdown(f"**Date:** {date}")
                            st.markdown(f"**Case ID:** `{case_id}`")
                            if petitioner:
                                st.markdown(f"**Petitioner:** {petitioner}")
                            if respondent:
                                st.markdown(f"**Respondent:** {respondent}")

                        with col_meta:
                            if citations:
                                st.markdown(f"**Citations:** {len(citations)}")

                        st.markdown("**Summary:**")
                        st.write(summary)

            else:
                st.error(f"Search failed: {response.status_code}")

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info("Run backend using: `uvicorn src.api.main:app --reload`")

elif search_button:
    st.warning("⚠️ Please enter a search query")

# -------------------- Footer --------------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;'>Legal Case Search System | AI Semantic Search</div>",
    unsafe_allow_html=True
)
