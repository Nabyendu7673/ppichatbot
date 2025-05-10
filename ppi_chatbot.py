import streamlit as st
import requests
import json

# Configure page settings - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="PPI Research Navigator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.example.com',
        'Report a bug': "https://www.example.com",
        'About': "### PPI Research Navigator\nVersion 2.0\n\nEvidence-Based PPI Research from PubMed"
    }
)

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import xml.etree.ElementTree as ET
from urllib.parse import quote

# Add myUpchar API key
MYUPCHAR_API_KEY = "34f265f31c97921576cf43b3279d310be008"  # Using the provided API key

def search_pubmed(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search PubMed using E-utilities API
    """
    try:
        # Base URL for E-utilities
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        api_key = "34f265f31c97921576cf43b3279d310be008"
        
        # Search for articles
        search_url = f"{base_url}esearch.fcgi?db=pubmed&term={quote(query)}&retmax={max_results}&retmode=json&api_key={api_key}"
        search_response = requests.get(search_url)
        search_data = search_response.json()
        
        if 'esearchresult' not in search_data or 'idlist' not in search_data['esearchresult']:
            return []
        
        # Get article details
        article_ids = search_data['esearchresult']['idlist']
        fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(article_ids)}&retmode=xml&api_key={api_key}"
        fetch_response = requests.get(fetch_url)
        
        # Parse XML response
        root = ET.fromstring(fetch_response.content)
        articles = []
        
        for article in root.findall('.//PubmedArticle'):
            try:
                # Extract article information
                title = article.find('.//ArticleTitle').text
                abstract = article.find('.//Abstract/AbstractText')
                abstract_text = abstract.text if abstract is not None else "No abstract available"
                
                # Get authors
                authors = []
                for author in article.findall('.//Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')
                    if last_name is not None and fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")
                
                # Get publication date
                pub_date = article.find('.//PubDate')
                year = pub_date.find('Year').text if pub_date is not None else "Unknown"
                
                # Get DOI
                doi = article.find('.//ELocationID[@EIdType="doi"]')
                doi_text = doi.text if doi is not None else None
                
                # Create article dictionary
                article_dict = {
                    'title': title,
                    'abstract': abstract_text,
                    'authors': authors,
                    'year': year,
                    'doi': doi_text,
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{article.find('.//PMID').text}/"
                }
                articles.append(article_dict)
            except Exception as e:
                continue
        
        return articles
    except Exception as e:
        st.error(f"Error searching PubMed: {str(e)}")
        return []

def get_pubmed_response(messages: List[dict]) -> tuple[str, List[Dict[str, str]]]:
    """
    Get response using PubMed E-utilities
    """
    try:
        # Get the last user message
        last_user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
        
        # Add "proton pump inhibitor" to the query if not present
        if "ppi" not in last_user_message.lower() and "proton pump inhibitor" not in last_user_message.lower():
            query = f"{last_user_message} proton pump inhibitor"
        else:
            query = last_user_message
        
        # Show loading message
        with st.spinner('Searching PubMed...'):
            # Search PubMed
            articles = search_pubmed(query)
        
        if not articles:
            return "No relevant articles found. Please try rephrasing your question.", []
        
        # Format response
        response_text = "Based on recent medical literature:\n\n"
        for i, article in enumerate(articles, 1):
            response_text += f"[{i}] {article['title']}\n"
            response_text += f"Authors: {', '.join(article['authors'])}\n"
            response_text += f"Year: {article['year']}\n"
            response_text += f"Abstract: {article['abstract'][:200]}...\n\n"
        
        # Create references
        references = []
        for i, article in enumerate(articles, 1):
            references.append({
                "number": str(i),
                "text": f"{article['title']} ({article['year']})",
                "url": article['url']
            })
        
        return response_text, references
        
    except Exception as e:
        st.error(f"""
        Error generating response: {str(e)}
        
        Please try:
        1. Refreshing the page
        2. Asking your question again
        3. If the error persists, try a different question
        """)
        return f"Error generating response: {str(e)}", []

def process_user_message(prompt):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Get and display assistant response
    response, references = get_pubmed_response(st.session_state.messages)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "references": references
    })
    st.rerun()

# Comprehensive PPI Interaction Database
PPI_INTERACTIONS = {
    "Omeprazole": {
        "Clopidogrel": {
            "mechanism": "Inhibits CYP2C19, reducing clopidogrel activation",
            "severity": "Major",
            "reliability": "High",
            "sources": [
                "https://pubmed.ncbi.nlm.nih.gov/20608754/",
                "https://www.frontiersin.org/articles/10.3389/fcvm.2024.1385318/full"
            ],
            "score": 9,
            "management": "Avoid concomitant use. Consider pantoprazole or H2 blockers instead. Increased risk of thrombotic events, especially post-stenting."
        },
        "Warfarin": {
            "mechanism": "Inhibits CYP2C9, increasing warfarin levels and bleeding risk",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.verywellhealth.com/protonix-pantoprazole-5079594"],
            "score": 7,
            "management": "Monitor INR closely. Consider dose adjustment of warfarin. Increased risk of bleeding requires careful monitoring."
        },
        "Diazepam": {
            "mechanism": "Inhibits CYP2C19, reducing diazepam clearance",
            "severity": "Moderate",
            "reliability": "High",
            "sources": ["https://pubmed.ncbi.nlm.nih.gov/11396546/"],
            "score": 7,
            "management": "Monitor for increased sedation. Consider dose reduction of diazepam. Watch for signs of excessive CNS depression."
        },
        "Phenytoin": {
            "mechanism": "Inhibits CYP2C19, increasing phenytoin levels",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://pubmed.ncbi.nlm.nih.gov/11396546/"],
            "score": 7,
            "management": "Monitor phenytoin levels closely. Consider dose adjustment if needed. Watch for signs of toxicity."
        },
        "Digoxin": {
            "mechanism": "Increases gastric pH, enhancing digoxin absorption",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC1885178/"],
            "score": 7,
            "management": "Monitor digoxin levels and clinical response. Consider dose adjustment if needed. Increased risk in elderly."
        },
        "Methotrexate": {
            "mechanism": "Decreases renal clearance, increasing methotrexate toxicity",
            "severity": "Major",
            "reliability": "Moderate",
            "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC3975086/"],
            "score": 9,
            "management": "Monitor for methotrexate toxicity (neutropenia, mucositis, renal failure). Consider dose adjustment or alternative PPI."
        },
        "Ketoconazole": {
            "mechanism": "Increases gastric pH, reducing ketoconazole absorption",
            "severity": "Moderate",
            "reliability": "High",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 7,
            "management": "Administer ketoconazole with acidic beverage. Consider alternative antifungal if needed."
        },
        "Iron Salts": {
            "mechanism": "Increases gastric pH, reducing iron absorption",
            "severity": "Moderate",
            "reliability": "High",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 7,
            "management": "Administer iron salts 2 hours before or 4 hours after PPI. Consider alternative iron formulation if needed."
        },
        "Atazanavir": {
            "mechanism": "Increases gastric pH, reducing atazanavir absorption",
            "severity": "Major",
            "reliability": "High",
            "sources": ["https://www.verywellhealth.com/protonix-pantoprazole-5079594"],
            "score": 9,
            "management": "Avoid concomitant use. Consider alternative PPI or antiretroviral if needed."
        },
        "Nelfinavir": {
            "mechanism": "Increases gastric pH, reducing nelfinavir absorption",
            "severity": "Major",
            "reliability": "High",
            "sources": ["https://www.verywellhealth.com/protonix-pantoprazole-5079594"],
            "score": 9,
            "management": "Avoid concomitant use. Consider alternative PPI or antiretroviral if needed."
        },
        "Citalopram": {
            "mechanism": "Inhibits CYP2C19, increasing citalopram levels",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC3975086/"],
            "score": 7,
            "management": "Monitor for increased citalopram effects. Consider dose adjustment if needed. Monitor ECG for QT prolongation."
        },
        "Erlotinib": {
            "mechanism": "Increases gastric pH, reducing erlotinib absorption",
            "severity": "Major",
            "reliability": "High",
            "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC4973002/"],
            "score": 9,
            "management": "Avoid concomitant use. Consider alternative PPI or timing of administration."
        },
        "Rilpivirine": {
            "mechanism": "Increases gastric pH, reducing rilpivirine absorption",
            "severity": "Major",
            "reliability": "High",
            "sources": ["https://www.verywellhealth.com/protonix-pantoprazole-5079594"],
            "score": 9,
            "management": "Avoid concomitant use. Consider alternative PPI or antiretroviral if needed."
        },
        "Tacrolimus": {
            "mechanism": "Inhibits CYP3A4, increasing tacrolimus levels",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC4973002/"],
            "score": 7,
            "management": "Monitor tacrolimus levels closely. Consider dose adjustment if needed."
        },
        "Theophylline": {
            "mechanism": "Inhibits CYP1A2, increasing theophylline levels",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://pubmed.ncbi.nlm.nih.gov/11396546/"],
            "score": 7,
            "management": "Monitor theophylline levels. Consider dose adjustment if needed."
        },
        "Ampicillin": {
            "mechanism": "Increases gastric pH, reducing ampicillin absorption",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 7,
            "management": "Administer ampicillin 2 hours before or 4 hours after PPI. Consider alternative antibiotic if needed."
        },
        "Cyanocobalamin (Vitamin B12)": {
            "mechanism": "Increases gastric pH, reducing vitamin B12 absorption",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 7,
            "management": "Monitor vitamin B12 levels. Consider parenteral supplementation if needed."
        }
    },
    "Esomeprazole": {
        "Clopidogrel": {
            "mechanism": "Inhibits CYP2C19, reducing clopidogrel activation",
            "severity": "Major",
            "reliability": "High",
            "sources": [
                "https://pubmed.ncbi.nlm.nih.gov/20608754/",
                "https://www.frontiersin.org/articles/10.3389/fcvm.2024.1385318/full"
            ],
            "score": 9,
            "management": "Avoid concomitant use. Consider pantoprazole or H2 blockers instead. Increased risk of thrombotic events, especially post-stenting."
        }
    },
    "Lansoprazole": {
        "Clopidogrel": {
            "mechanism": "Minimal effect on CYP2C19",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 5,
            "management": "Monitor for reduced clopidogrel efficacy. Consider alternative PPI if needed."
        }
    },
    "Pantoprazole": {
        "Clopidogrel": {
            "mechanism": "Minimal effect on CYP2C19",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.elsevier.com/resources/clinicalkey-ai/what-are-some-common-drug-interactions-with-proton-pump-inhibitors-4710"],
            "score": 5,
            "management": "Monitor for reduced clopidogrel efficacy. Consider alternative PPI if needed."
        },
        "Warfarin": {
            "mechanism": "Inhibits CYP2C9, increasing warfarin levels and bleeding risk",
            "severity": "Moderate",
            "reliability": "Moderate",
            "sources": ["https://www.verywellhealth.com/protonix-pantoprazole-5079594"],
            "score": 7,
            "management": "Monitor INR closely. Consider dose adjustment of warfarin. Increased risk of bleeding requires careful monitoring."
        }
    }
}

def check_ppi_interaction(ppi: str, other_drug: str) -> Dict[str, Any]:
    """
    Check for known interactions between a PPI and another drug using the comprehensive database
    """
    try:
        # Check if PPI exists in database
        if ppi not in PPI_INTERACTIONS:
            return {
                "interaction": {
                    "severity": "Unknown",
                    "description": f"No interaction data available for {ppi}",
                    "management": "Consult healthcare provider for guidance",
                    "evidence": "Not available",
                    "score": 0
                },
                "source": "Local Database"
            }
        
        # Check if interaction exists for the drug combination
        if other_drug in PPI_INTERACTIONS[ppi]:
            interaction = PPI_INTERACTIONS[ppi][other_drug]
            return {
                "interaction": {
                    "severity": interaction["severity"],
                    "description": f"{ppi} {interaction['mechanism']}",
                    "management": interaction["management"],
                    "evidence": f"Reliability: {interaction['reliability']}",
                    "score": interaction["score"],
                    "sources": interaction["sources"]
                },
                "source": "Local Database"
            }
        
        # If no specific interaction found
        return {
            "interaction": {
                "severity": "None",
                "description": f"No known significant interactions between {ppi} and {other_drug}",
                "management": "Routine monitoring recommended",
                "evidence": "Based on current medical literature",
                "score": 0
            },
            "source": "Local Database"
        }
    except Exception as e:
        return {
            "error": f"Error checking interaction between {ppi} and {other_drug}: {str(e)}"
        }

def get_interaction_score_color(score: int) -> str:
    """
    Get color based on interaction score
    """
    if score >= 8:
        return "#FF0000"  # Red for high risk
    elif score >= 5:
        return "#FFA500"  # Orange for moderate risk
    elif score > 0:
        return "#FFFF00"  # Yellow for low risk
    else:
        return "#00FF00"  # Green for no risk

# Custom CSS for a modern, visually appealing chat UI
st.markdown("""
    <style>
        :root {
            --primary-color: #4F46E5;  /* Vibrant indigo */
            --secondary-color: #7C3AED;  /* Rich purple */
            --accent-color: #10B981;  /* Emerald green */
            --warning-color: #F59E0B;  /* Amber */
            --danger-color: #EF4444;  /* Red */
            --info-color: #3B82F6;  /* Blue */
            --background-color: #000000;  /* Black */
            --card-bg: #1a1a1a;  /* Dark gray */
            --text-primary: #ffffff;  /* White */
            --text-secondary: #a3a3a3;  /* Light gray */
            --border-color: #333333;  /* Dark gray */
            --shadow-color: rgba(0, 0, 0, 0.3);
            --gradient-primary: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            --gradient-secondary: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        }
        
        /* Main app styling */
        .stApp {
            background-color: var(--background-color);
            color: var(--text-primary);
        }
        
        /* Header styling */
        h1 {
            color: var(--text-primary) !important;
            font-weight: 800 !important;
            font-size: 2.75rem !important;
            margin-bottom: 1rem !important;
            text-shadow: 2px 2px 4px var(--shadow-color);
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        h2, h3 {
            color: var(--text-primary) !important;
            font-weight: 700 !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            box-shadow: 4px 0 12px var(--shadow-color);
            border-right: 1px solid var(--border-color);
        }
        section[data-testid="stSidebar"] * {
            color: #000 !important;
        }
        
        .stSidebar .stButton>button {
            background: var(--gradient-primary) !important;
            color: white !important;
            border-radius: 12px;
            border: none;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px var(--shadow-color);
        }
        
        .stSidebar .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px var(--shadow-color);
        }
        
        /* Input fields styling */
        .stTextInput>div>div>input {
            background: #ffffff !important;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            color: var(--text-primary);
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px var(--shadow-color);
        }
        
        .stTextInput>div>div>input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.2);
        }
        
        /* Select box styling */
        .stSelectbox>div>div>div {
            background: #ffffff !important;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            color: #000000 !important;
            box-shadow: 0 2px 4px var(--shadow-color);
        }
        .stSelectbox label, .stSelectbox span, .stSelectbox div, .stSelectbox input, .stSelectbox option {
            color: #000000 !important;
        }
        /* Force dropdown and its options to be visible: white background, black font */
        .stSelectbox [data-baseweb="select"] * {
            background: #fff !important;
            color: #000 !important;
            opacity: 1 !important;
        }
        /* Fallback: if any option uses a dark background, force font to white */
        .stSelectbox [data-baseweb="select"] [style*="background: rgb(47, 51, 54)"] {
            color: #fff !important;
        }
        /* Remove any transparency or filter effects */
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option,
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option[aria-selected="true"],
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option:active,
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option:focus,
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option:hover,
        .stSelectbox [data-baseweb="select"] .css-1n76uvr-option[aria-disabled="true"] {
            filter: none !important;
            opacity: 1 !important;
        }
        
        /* Chat message styling */
        .stChatMessage {
            background-color: var(--card-bg) !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 6px var(--shadow-color) !important;
            margin-bottom: 1.5rem !important;
            padding: 1.25rem !important;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        
        .stChatMessage[data-testid="user"] {
            border-left: 4px solid var(--primary-color);
            background: linear-gradient(to right, rgba(79, 70, 229, 0.1), var(--card-bg)) !important;
        }
        
        .stChatMessage[data-testid="assistant"] {
            border-left: 4px solid var(--accent-color);
            background: linear-gradient(to right, rgba(16, 185, 129, 0.1), var(--card-bg)) !important;
        }
        
        /* Interaction severity cards */
        .severity-card {
            background-color: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px var(--shadow-color);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        
        .severity-major {
            border-left-color: var(--danger-color);
            background: linear-gradient(to right, rgba(239, 68, 68, 0.1), var(--card-bg));
        }
        
        .severity-moderate {
            border-left-color: var(--warning-color);
            background: linear-gradient(to right, rgba(245, 158, 11, 0.1), var(--card-bg));
        }
        
        .severity-minor {
            border-left-color: var(--accent-color);
            background: linear-gradient(to right, rgba(16, 185, 129, 0.1), var(--card-bg));
        }
        
        /* Quick reference styling */
        .quick-reference {
            background-color: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px var(--shadow-color);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        
        .quick-reference h3 {
            color: var(--text-primary);
            margin-bottom: 1rem;
            font-weight: 700;
        }
        
        .quick-reference ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .quick-reference li {
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
            transition: all 0.3s ease;
            color: var(--text-primary);
        }
        
        .quick-reference li:hover {
            background-color: rgba(79, 70, 229, 0.1);
            transform: translateX(4px);
        }
        
        .quick-reference li:last-child {
            border-bottom: none;
        }
        
        /* Link styling */
        a {
            color: var(--primary-color) !important;
            text-decoration: none !important;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        a:hover {
            color: var(--secondary-color) !important;
            text-decoration: underline !important;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--card-bg);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--secondary-color);
        }
        
        /* General text styling */
        p, div, span {
            color: var(--text-primary) !important;
        }
        
        /* Streamlit specific elements */
        .stMarkdown {
            color: var(--text-primary) !important;
        }
        
        .stTextInput>div>div>input::placeholder {
            color: var(--text-secondary) !important;
        }
        
        .stSelectbox>div>div>div {
            color: var(--text-primary) !important;
        }
        
        .welcome-header, .welcome-subheader {
            color: #000 !important;
            background: none !important;
            -webkit-background-clip: unset !important;
            -webkit-text-fill-color: #000 !important;
            text-shadow: none !important;
        }
        
        /* Chat input box styling */
        .stChatInputContainer, .stChatInputContainer input, .stChatInputContainer textarea {
            background: #ffffff !important;
            color: #000000 !important;
        }
        
        /* Force all dropdown menu options to black font and white background */
        [role="option"], [role="option"] * {
            color: #000 !important;
            background: #fff !important;
        }
        /* Also target the dropdown menu container */
        [role="listbox"] {
            background: #fff !important;
            color: #000 !important;
        }
        
        /* Key Guidelines section: force all text and links to white */
        .key-guidelines, .key-guidelines *, .key-guidelines a {
            color: #fff !important;
        }
        
        .professional-box {
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(44, 62, 80, 0.08);
            border-left: 6px solid #4F46E5;
            background: #fff;
            color: #000 !important;
            padding: 1.25rem 1.5rem 1.25rem 1.25rem;
            margin-bottom: 1.5rem;
        }
        .professional-box h3 {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #2563eb !important;
            letter-spacing: 0.5px;
        }
        .professional-box ul {
            margin: 0;
            padding-left: 1.2rem;
        }
        .professional-box li {
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }
        .key-guidelines.professional-box a {
            color: #fff !important;
            font-weight: 600;
            background: #4F46E5;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            margin-bottom: 0.5rem;
            text-decoration: none;
            display: inline-block;
            transition: background 0.2s;
        }
        .key-guidelines.professional-box a:hover {
            background: #7C3AED;
        }
        /* Streamlit tab color customization */
        .stTabs [data-baseweb="tab-list"] {
            background: #4F46E5;
            border-radius: 12px 12px 0 0;
            padding: 0.25rem 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            color: #fff;
            font-weight: 600;
            background: transparent;
            border-radius: 8px 8px 0 0;
            margin-right: 0.5rem;
            padding: 0.5rem 1.25rem;
            transition: background 0.2s;
        }
        .stTabs [aria-selected="true"] {
            background: #7C3AED;
            color: #fff;
        }
        .quick-reference.professional-box li {
            color: #2563eb !important;
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "references" not in st.session_state:
    st.session_state.references = []
if "ratings" not in st.session_state:
    st.session_state.ratings = {}

# Sidebar with drug interaction checker
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1.5rem;'>
        <h2 style='color: #2563eb; font-weight: 700;'>Drug Interaction Checker</h2>
        <p style='color: #000; font-size: 1rem;'>Instantly identify clinically significant drug interactions with proton pump inhibitors (PPIs) to optimize patient safety and therapeutic outcomes.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # PPI Selection
    ppi = st.selectbox(
        "Select a PPI:",
        ["Omeprazole", "Esomeprazole", "Lansoprazole", "Pantoprazole"],
        key="ppi_select"
    )
    
    # Other Drug Input
    other_drug = st.text_input(
        "Enter another medication:",
        placeholder="e.g., Warfarin, Clopidogrel",
        key="other_drug_input"
    )
    
    # Check Interaction Button
    if st.button("Check Interaction", key="check_interaction"):
        if other_drug:
            # Convert drug names to title case for consistent matching
            ppi = ppi.title()
            other_drug = other_drug.title()
            
            result = check_ppi_interaction(ppi, other_drug)
            
            if "error" in result:
                st.error(result["error"])
            else:
                interaction = result["interaction"]
                
                # Display interaction severity with enhanced styling
                severity_color = get_interaction_score_color(interaction["score"])
                st.markdown(f"""
                <div style='
                    background-color: {severity_color};
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                '>
                    <h3 style='margin: 0; font-size: 1.2em;'>Interaction Severity</h3>
                    <p style='margin: 5px 0 0 0; font-size: 1.5em; font-weight: bold;'>{interaction["severity"]}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display interaction details with enhanced styling
                st.markdown("""
                <div style='
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                '>
                    <h3 style='color: #2563eb; margin-top: 0;'>Interaction Details</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Description with icon
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 12px;
                    border-radius: 6px;
                    margin-bottom: 10px;
                    border-left: 4px solid #2563eb;
                '>
                    <p style='margin: 0;'><strong>📝 Description:</strong> {interaction['description']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Management with icon
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 12px;
                    border-radius: 6px;
                    margin-bottom: 10px;
                    border-left: 4px solid #34a853;
                '>
                    <p style='margin: 0;'><strong>💊 Management:</strong> {interaction['management']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Evidence with icon
                st.markdown(f"""
                <div style='
                    background-color: white;
                    padding: 12px;
                    border-radius: 6px;
                    margin-bottom: 10px;
                    border-left: 4px solid #fbbc05;
                '>
                    <p style='margin: 0;'><strong>🔍 Evidence:</strong> {interaction['evidence']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display sources with enhanced styling
                if "sources" in interaction and interaction["sources"]:
                    st.markdown("""
                    <div style='
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        margin-bottom: 15px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    '>
                        <h3 style='color: #2563eb; margin-top: 0;'>References</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for source in interaction["sources"]:
                        st.markdown(f"""
                        <div style='
                            background-color: white;
                            padding: 10px;
                            border-radius: 6px;
                            margin-bottom: 8px;
                            border-left: 4px solid #4285f4;
                        '>
                            <a href='{source}' target='_blank' style='color: #4285f4; text-decoration: none;'>
                                📚 {source}
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("Please enter a medication name to check for interactions.")

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2.5rem; padding: 2rem; background: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h1 class='welcome-header' style='font-weight: 700; margin-bottom: 0.5rem;'>PPI Research Navigator</h1>
        <h3 class='welcome-subheader' style='font-weight: 500; margin-top: 0;'>Explore Latest PPI Research from PubMed-Indexed Journals</h3>
        <p class='welcome-header' style='font-size: 1.1rem; margin-top: 1rem; line-height: 1.6;'>Access evidence-based information on Proton Pump Inhibitors, including clinical trials, systematic reviews, and recent advancements in PPI therapy and safety.</p>
    </div>
    """, unsafe_allow_html=True)

    # Chat area directly on the page, no card
    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)
                if message["role"] == "assistant" and message.get("references"):
                    st.markdown("### References")
                    for ref in message["references"]:
                        if ref.get("url"):
                            st.markdown(f"[{ref['number']}] [{ref['text']}]({ref['url']})")
                        else:
                            st.markdown(f"[{ref['number']}] {ref['text']}")
                if i in st.session_state.ratings:
                    st.markdown(f"**Rating:** {st.session_state.ratings[i]}")
    prompt = st.chat_input("Ask about PPI management, guidelines, or interactions...", key="main_chat_input")
    if prompt:
        process_user_message(prompt)

with col2:
    tab1, tab2 = st.tabs([
        "Quick Reference",
        "Key Guidelines"
    ])
    with tab1:
        st.markdown("""
        <div class='quick-reference professional-box'>
            <h3>PPI Safety Pearls</h3>
            <ul>
                <li>Risk of C. difficile infection</li>
                <li>Key drug interactions (clopidogrel, warfarin)</li>
                <li>Increased fracture risk (long-term use)</li>
                <li>Hypomagnesemia and B12 deficiency</li>
                <li>Deprescribe if no clear indication</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with tab2:
        st.markdown("""
        <div class='key-guidelines professional-box'>
            <h3 style='color: #fff; font-weight: 700; margin-bottom: 1.25rem; text-align: center;'>Key Guidelines</h3>
            <div style='display: flex; flex-direction: column; gap: 0.75rem;'>
                <a href="https://journals.lww.com/ajg/fulltext/2022/01000/american_college_of_gastroenterology_clinical.14.aspx" target="_blank">ACG GERD Guidelines (2022)</a>
                <a href="https://www.gastrojournal.org/article/S0016-5085(20)30065-5/fulltext" target="_blank">AGA PPI Clinical Practice Update (2020)</a>
                <a href="https://www.fda.gov/drugs/postmarket-drug-safety-information-patients-and-providers/proton-pump-inhibitors-ppis" target="_blank">FDA PPI Safety Updates (2023)</a>
                <a href="https://emedicine.medscape.com/article/1811445-overview" target="_blank">Medscape: Proton Pump Inhibitors Overview (2023)</a>
                <a href="https://www.nhs.uk/medicines/proton-pump-inhibitors/" target="_blank">NHS: PPIs for Acid Reflux, Heartburn & GORD (2024)</a>
                <a href="https://www.uptodate.com/contents/proton-pump-inhibitors-overview-of-use-and-adverse-effects-in-the-treatment-of-acid-related-disorders" target="_blank">UpToDate: PPI Use and Adverse Effects (2024)</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

def validate_response(response: str) -> bool:
    """Validate that the response contains relevant medical information"""
    required_keywords = ['dose', 'interaction', 'side effect', 'mechanism', 'contraindication', 'guideline']
    return any(keyword in response.lower() for keyword in required_keywords)

def format_response(response: str) -> str:
    """Format the response for better readability"""
    formatted = response.replace(" - ", ":\n• ")
    formatted = formatted.replace("; ", "\n• ")
    return formatted

if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = {
        'total_queries': 0,
        'successful_responses': 0,
        'failed_responses': 0
    }

# Add patient education resources
def generate_patient_handout(ppi: str, indication: str) -> str:
    """
    Generate a patient education handout in markdown format
    """
    handout = f"""
# Patient Guide: {ppi} for {indication}

## About Your Medication
{ppi} belongs to a group of medicines called Proton Pump Inhibitors (PPIs). These medications work by reducing the amount of acid your stomach produces.

## Important Information
- Take this medication at least 30-60 minutes before meals
- Complete the full course as prescribed by your healthcare provider
- Do not stop taking this medication without consulting your healthcare provider

## Common Side Effects
- Headache
- Nausea
- Diarrhea
- Stomach pain
- Vomiting
- Gas

## When to Seek Medical Attention
Seek immediate medical attention if you experience:
- Severe diarrhea
- Unexplained weight loss
- Difficulty swallowing
- Chest pain
- Blood in stool

## Lifestyle Modifications
1. Maintain a healthy weight
2. Avoid trigger foods
3. Eat smaller meals
4. Avoid lying down for 2-3 hours after meals
5. Elevate the head of your bed

## Follow-up Care
- Keep all scheduled follow-up appointments
- Report any new or worsening symptoms
- Discuss any concerns about your medication

For more information, visit:
- [FDA Medication Guide](https://www.fda.gov)
- [ACG Patient Resources](https://gi.org)
- [NIH Health Information](https://www.nih.gov)
"""
    return handout

# Add patient education section to the sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1rem;'>
        <h3 style='color: #2563eb; font-weight: 700;'>Patient Education Center</h3>
    </div>
    """, unsafe_allow_html=True)
    
    edu_ppi = st.selectbox(
        "Select Medication:",
        ["Omeprazole", "Esomeprazole", "Lansoprazole", "Pantoprazole"],
        key="edu_ppi_select"
    )
    
    edu_indication = st.selectbox(
        "Select Condition:",
        ["GERD", "Peptic Ulcer", "H. pylori Infection"],
        key="edu_indication_select"
    )
    
    if st.button("Generate Patient Handout", key="generate_handout"):
        handout_content = generate_patient_handout(edu_ppi, edu_indication)
        
        # Convert markdown to PDF-ready format
        from io import StringIO
        import base64
        
        # Create downloadable PDF
        pdf_buffer = StringIO()
        pdf_buffer.write(handout_content)
        pdf_string = pdf_buffer.getvalue()
        
        # Create download button
        st.download_button(
            label="Download Patient Handout (PDF)",
            data=pdf_string,
            file_name=f"{edu_ppi}_{edu_indication}_Guide.pdf",
            mime="application/pdf"
        )
        
        # Display preview
        st.markdown("""
        <div style='
            background: #ffffff;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 1rem;
        '>
            <h4 style='color: #2563eb; margin-bottom: 0.5rem;'>Handout Preview</h4>
        """, unsafe_allow_html=True)
        
        st.markdown(handout_content)
        st.markdown("</div>", unsafe_allow_html=True)

# Add PPI warning signs section
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1rem;'>
        <h3 style='color: #2563eb; font-weight: 700;'>PPI Warning Signs & Adverse Effects</h3>
        <p style='color: #666; font-size: 0.9rem;'>Based on FDA Safety Communications</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("Renal Effects", expanded=False):
        st.markdown("""
        ### Acute Interstitial Nephritis (AIN)
        **Signs:** Decreased urine output, blood in urine, fatigue  
        **Notes:** PPIs are a leading cause of drug-induced AIN; onset can occur weeks to months after initiation. Early recognition is crucial to prevent progression to chronic kidney disease.
        
        ### Chronic Kidney Disease (CKD)
        **Signs:** Fatigue, swelling, elevated creatinine levels  
        **Notes:** Long-term PPI use has been linked to an increased risk of CKD, independent of AIN. Regular monitoring of renal function is advised for chronic users.
        """)
    
    with st.expander("Gastrointestinal Effects", expanded=False):
        st.markdown("""
        ### Clostridioides difficile Infection (CDI)
        **Signs:** Persistent diarrhea, abdominal pain, fever  
        **Notes:** PPIs increase susceptibility to CDI due to reduced gastric acidity, which impairs the gut\'s defense against pathogens.
        
        ### Rebound Acid Hypersecretion
        **Signs:** Worsening heartburn or indigestion upon discontinuation  
        **Notes:** Abrupt cessation after prolonged use may lead to increased gastric acid production. Tapering the dose is recommended to mitigate symptoms.
        """)
    
    with st.expander("Musculoskeletal Effects", expanded=False):
        st.markdown("""
        ### Bone Fractures (Hip, Spine, Wrist)
        **Signs:** Sudden bone pain, fractures from minimal trauma  
        **Notes:** Long-term PPI use is associated with decreased calcium absorption, leading to increased fracture risk, especially in the elderly.
        """)
    
    with st.expander("Neurological Effects", expanded=False):
        st.markdown("""
        ### Vitamin B12 Deficiency
        **Signs:** Fatigue, numbness, memory issues  
        **Notes:** PPIs can impair B12 absorption, leading to deficiency over prolonged periods. Monitoring B12 levels is advisable for long-term users.
        
        ### Dementia (Potential Association)
        **Signs:** Memory loss, confusion, cognitive decline  
        **Notes:** Some studies suggest a possible link between extended PPI use and increased dementia risk, though findings are not conclusive.
        """)
    
    with st.expander("Electrolyte Imbalance", expanded=False):
        st.markdown("""
        ### Hypomagnesemia
        **Signs:** Muscle cramps, seizures, arrhythmias  
        **Notes:** PPIs may cause low magnesium levels, especially when combined with other medications like diuretics. Regular monitoring is recommended for at-risk patients.
        """)
    
    with st.expander("Dermatological/Autoimmune Effects", expanded=False):
        st.markdown("""
        ### Subacute Cutaneous Lupus Erythematosus (SCLE)
        **Signs:** Rash, joint pain, photosensitivity  
        **Notes:** Rare autoimmune reaction linked to PPI use; symptoms typically resolve upon discontinuation.
        """)
    
    with st.expander("Infectious Effects", expanded=False):
        st.markdown("""
        ### Community-Acquired Pneumonia
        **Signs:** Cough, fever, shortness of breath  
        **Notes:** Increased risk of pneumonia due to reduced gastric acidity and potential bacterial overgrowth.
        """)
    
    st.markdown("""
    <div style='background: #fff3cd; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
        <p style='color: #856404; margin: 0;'>
            <strong>Important:</strong> These warnings are based on FDA safety communications. Regular monitoring and assessment of continued need for PPI therapy is recommended.
        </p>
    </div>
    """, unsafe_allow_html=True)

def search_medicines(name=None, limit=10):
    """
    Search medicines using RxNorm API
    """
    try:
        base_url = "https://rxnav.nlm.nih.gov/REST/drugs.json"
        params = {
            "name": name if name else "",
            "maxEntries": limit
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error searching medicines: {str(e)}")
        return None

def get_drug_details(rxcui):
    """
    Get detailed drug information using RxNorm API
    """
    try:
        base_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json"
        response = requests.get(base_url)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching drug details: {str(e)}")
        return None

# Add medicine search section to the sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1rem;'>
        <h3 style='color: #2563eb; font-weight: 700;'>Medicine Search</h3>
        <p style='color: #666; font-size: 0.9rem;'>Search medications using RxNorm database</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("Search Medicines", expanded=True):
        # Search filters
        medicine_name = st.text_input("Medicine Name", placeholder="Enter medicine name (e.g., Rabeprazole)")
        
        # Search button
        if st.button("Search Medicines"):
            if not medicine_name:
                st.warning("Please enter a medicine name")
            else:
                with st.spinner("Searching medicines..."):
                    results = search_medicines(name=medicine_name)
                    
                    if results and "drugGroup" in results and "conceptGroup" in results["drugGroup"]:
                        concept_groups = results["drugGroup"]["conceptGroup"]
                        st.markdown("### Search Results")
                        
                        for group in concept_groups:
                            if "conceptProperties" in group:
                                for drug in group["conceptProperties"]:
                                    rxcui = drug.get('rxcui', '')
                                    rxnorm_url = f"https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={rxcui}"
                                    
                                    st.markdown(f"""
                                    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                                        <h4 style='color: #2563eb; margin-bottom: 5px;'>{drug.get('name', 'N/A')}</h4>
                                        <p style='margin-bottom: 5px;'><strong>Type:</strong> {drug.get('tty', 'N/A')}</p>
                                        <p style='margin-bottom: 5px;'><strong>RxCUI:</strong> {rxcui}</p>
                                        <a href='{rxnorm_url}' target='_blank' style='color: #2563eb; text-decoration: none;'>
                                            🔗 View on RxNorm
                                        </a>
                                    </div>
                                    """, unsafe_allow_html=True)
                    else:
                        st.info("No medicines found matching your criteria")

