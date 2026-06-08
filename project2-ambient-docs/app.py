# app.py - Streamlit with Minimal API
import streamlit as st
from orchestrate_minimal import generate_soap_with_attribution

#st.set_page_config(layout="wide")
st.title("SOAP Generator + Source Attribution")

# Input
conversation = st.text_area("Paste Conversation:", height=200)

if st.button("Generate SOAP + Attributions"):
    if not conversation.strip():
        st.error("Please enter a conversation")
    else:
        with st.spinner("Processing..."):
            result = generate_soap_with_attribution(conversation)

        if result['success']:
            # Display results
            st.success("✓ Generated successfully")

            #st.subheader("Statistics")
            col1, col2, col3, col4 = st.columns(4)
            stats = result['data']['statistics']
            col1.metric("Total Entities", stats['total_entities'])
            col2.metric("Hallucinations", stats['hallucination_count'])
            col3.metric("Coverage", f"{stats['attribution_coverage']:.1%}")
            col4.metric("Quality", stats['quality_score'].upper())

            col5, col6 = st.columns(2)
            with col5:
                st.subheader("SOAP Note")
                st.text(result['data']['soap_note'])

            with col6: 
                st.subheader("Attributions")
                for attr in result['data']['attributions'][:10]:
                    icon = "⚠️" if attr['is_hallucination'] else "✅"
                    st.write(f"{icon} **{attr['soap_text']}** → {attr['source_text']}")

        else:
            st.error(f"Error: {result['error']}")