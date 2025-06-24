"""This Streamlit POC app demonstrates a simple, multilingual invoice extractor using Gemini LMM 
to perform OCR, translation, and standardized field extraction from uploaded invoices.

Author: Ishwariya
"""

import streamlit as st
from PIL import Image
import google.generativeai as genai
import json
import pandas as pd
from pdf2image import convert_from_bytes # To handle PDF files
from dotenv import load_dotenv
import os

import warnings 
warnings.filterwarnings("ignore")

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("api_key")
if not api_key:
    st.error("API key not found. Please create a .env file with 'api_key=YOUR_API_KEY'.")
    st.stop()

# --- Configuration ---
st.set_page_config(page_title="Invoice Extractor Pro", page_icon="🧾", layout="wide") # Use wide layout

# --- Constants ---
model_name = "gemini-1.5-flash" 

# Configure the genai library with the API key
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Error configuring Google AI: {e}")
    st.stop()

# --- Helper Functions ---

def clean_json_string(json_string):
    """
    Cleans the Gemini response to make it a valid JSON.
    It removes the markdown backticks and the 'json' prefix.
    """
    if json_string.startswith("```json"):
        json_string = json_string[7:]
    if json_string.endswith("```"):
        json_string = json_string[:-3]
    return json_string.strip()


def get_gemini_response(input_prompt, image_list, model_name):
    """
    Function to get the response and usage metadata from the Gemini model.
    Returns the response text and the usage metadata object.
    """
    try:
        model = genai.GenerativeModel(model_name)
        content = [input_prompt]
        content.extend(image_list)
        
        # Generate content and get the response object
        response = model.generate_content(content)
        
        # Extract the text and usage metadata
        cleaned_response_text = clean_json_string(response.text)
        usage_metadata = response.usage_metadata
        
        return cleaned_response_text, usage_metadata
    except Exception as e:
        st.error(f"An error occurred with the Gemini API: {e}")
        return None, None

# --- Application UI ---

st.title("🧾 Invoice Extractor Pro")
st.write("Upload an invoice (any language), and the AI will extract, translate, and display the data for verification.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Choose an invoice file (Image or PDF)...", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file is None:
    st.info("Please upload a file to get started.")
    st.stop()

image_list = []
# --- Logic to process PDF or Image ---
if uploaded_file.type == "application/pdf":
    try:
        images = convert_from_bytes(uploaded_file.read())
        image_list.extend(images)
    except Exception as e:
        st.error(f"Failed to process PDF file: {e}")
        st.warning("Please ensure you have installed the 'poppler' dependency correctly.")
        st.stop()
else:
    image = Image.open(uploaded_file)
    image_list.append(image)

# LMM input prompt: optimize for invoice features extraction, input format of the data, to update output format 
input_prompt = """
You are an expert multilingual data processor specializing in invoices. Your non-negotiable task is to extract key information from the invoice and provide ALL textual output in English.

This translation requirement is the most critical part of your task. You must not return any names, addresses, or item descriptions in their original language.

**Crucial Example:** If the invoice shows a customer address as "上海市徐汇区肇嘉浜路798号506室", your JSON output for "customer_address" MUST be the translated and formatted English version, such as "Room 506, No. 798, Zhaojiabang Road, Xuhui District, Shanghai, China". Do not, under any circumstances, return the original Chinese text. Apply this translation logic to all text fields. 
** If Invoice total amount is not given, you must return N/A. Do not make up an asnwer.

Please extract the following 10 fields, ensuring all text values are translated to English:
1.  Invoice ID
2.  Invoice Date
3.  Due Date
4.  Biller Name (or Vendor/Company Name)
5.  Biller Address
6.  Customer Name
7.  Customer Address
8.  Subtotal
9.  Total Tax
10. Total Amount

In addition to the fields above, please extract all line items.
For each line item, extract:
- Description (must be translated to English)
- Quantity
- Unit Price
- Line Total

Provide the final, fully translated output in a single, structured JSON format.
If a field is not found, must return "N/A" for its value. don't make up an answer. 

Final JSON structure required:
{
  "invoice_id": "value",
  "invoice_date": "value",
  "due_date": "value",
  "seller_name": "value",
  "seller_address": "value",
  "customer_name": "value",
  "customer_address": "value",
  "subtotal": "value",
  "total_tax": "value",
  "total_amount": "value",
  "line_items": [
    {"description": "value", "quantity": "value", "unit_price": "value", "line_total": "value"}
  ]
}
"""

if st.button("Extract & Verify Information", type="primary"):
    with st.spinner("Analyzing invoice, translating, and preparing verification view..."):
        # Get response and token usage from Gemini
        response_text, usage_metadata = get_gemini_response(input_prompt, image_list, model_name)

        if response_text and usage_metadata:
            try:
                # Parse the JSON response
                invoice_data = json.loads(response_text)
                st.success("Invoice data extracted and translated successfully!")      

                # --- Side-by-Side Verification UI - visual Evaluation ---
                view_col, data_col = st.columns(2, gap="large")

                with view_col:
                    st.subheader("Invoice Preview")
                    # If PDF has multiple pages, add a selector
                    if len(image_list) > 1:
                        page_num = st.selectbox(
                            "Select a page to view", 
                            options=range(1, len(image_list) + 1),
                            format_func=lambda x: f"Page {x}"
                        )
                        st.image(image_list[page_num - 1], use_container_width=True)
                    else:
                        st.image(image_list[0], use_container_width=True)
                
                with data_col:
                    st.subheader("Extracted Data (in English)")
                    key_fields = {k: v for k, v in invoice_data.items() if k != 'line_items'}
                    
                    for key, value in key_fields.items():
                        st.text_input(
                            label=f"**{key.replace('_', ' ').title()}**", 
                            value=str(value), # Ensure value is a string for the text input
                            key=key, 
                            disabled=True
                        )

                    st.subheader("Extracted Line Items")
                    if 'line_items' in invoice_data and invoice_data['line_items']:
                        line_items_df = pd.DataFrame(invoice_data['line_items'])
                        st.dataframe(line_items_df, use_container_width=True)
                    else:
                        st.warning("No line items were extracted.")
                
                # --- Raw JSON Visualization ---
                st.markdown("---")
                with st.expander("View Raw JSON Response"):
                    # Pretty-print the JSON with an indent of 2 spaces
                    pretty_json = json.dumps(invoice_data, indent=2, ensure_ascii=False) # ensure_ascii=False for proper display
                    st.code(pretty_json, language='json')

                st.markdown("---") # Visual separator
                
                # --- Display Token Usage Evaluation ---
                st.subheader("API Usage Evaluation")
                token_info = {
                    "Prompt Tokens": f"{usage_metadata.prompt_token_count:,}",
                    "Completion Tokens": f"{usage_metadata.candidates_token_count:,}",
                    "Total Tokens Used": f"{usage_metadata.total_token_count:,}"
                }
                st.json(token_info)

            except json.JSONDecodeError:
                st.error("Failed to parse the extracted data as JSON. The model may have returned an invalid format.")
                st.text_area("Raw AI Response:", response_text, height=300)
            except Exception as e:
                st.error(f"An unexpected error occurred while displaying data: {e}")
            st.text_area("Raw AI Response:", response_text, height=300)