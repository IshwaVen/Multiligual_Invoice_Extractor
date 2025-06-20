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

# It's recommended to handle the case where the API key might not be set
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

# --- UPDATED PROMPT DEFINITION ---
input_prompt = """
You are an expert multilingual invoice data extractor. Your primary task is to analyze the provided invoice image(s), which can be in any language.

Your process should be as follows:
1.  First, automatically detect the language of the invoice.
2.  Next, extract the key information listed below.
3.  Translate all extracted textual data into English. This includes fields like Biller Name, Biller Address, Customer Name, Customer Address, and the Description for each line item.
4.  Do NOT translate numeric values (IDs, quantities, prices, totals) or dates. Standardize dates to a common format like YYYY-MM-DD if possible.

Please extract the following 10 fields (with text values translated to English):
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
- Description (translated to English)
- Quantity
- Unit Price
- Line Total

Provide the final output in a single, structured JSON format.
The JSON must have a main object with the 10 key fields, and a 'line_items' key
which is an array of objects, where each object represents a line item.
If a field is not found, return "N/A" for its value.

Example JSON structure:
{
  "invoice_id": "INV-123",
  "invoice_date": "2023-10-26",
  "due_date": "2023-11-25",
  "biller_name": "Global Tech Inc.",
  "biller_address": "123 Tech Street, Silicon Valley, CA 94000, USA",
  "customer_name": "International Solutions Ltd.",
  "customer_address": "456 Business Avenue, London, EC1A 1AA, UK",
  "subtotal": "2000.00",
  "total_tax": "160.00",
  "total_amount": "2160.00",
  "line_items": [
    {"description": "Cloud Service Subscription", "quantity": "1", "unit_price": "1500.00", "line_total": "1500.00"},
    {"description": "Advanced Support Package", "quantity": "1", "unit_price": "500.00", "line_total": "500.00"}
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
                
                # --- NEW: Display Token Usage Evaluation ---
                st.subheader("API Usage Evaluation")
                token_info = {
                    "Prompt Tokens": f"{usage_metadata.prompt_token_count:,}",
                    "Completion Tokens": f"{usage_metadata.candidates_token_count:,}",
                    "Total Tokens Used": f"{usage_metadata.total_token_count:,}"
                }
                st.json(token_info)

                st.markdown("---") # Visual separator

                # --- NEW: Side-by-Side Verification UI ---
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
                        st.image(image_list[page_num - 1], use_column_width=True)
                    else:
                        st.image(image_list[0], use_column_width=True)
                
                with data_col:
                    st.subheader("Extracted Data (in English)")
                    key_fields = {k: v for k, v in invoice_data.items() if k != 'line_items'}
                    
                    for key, value in key_fields.items():
                        st.text_input(
                            label=f"**{key.replace('_', ' ').title()}**", 
                            value=value, 
                            key=key, 
                            disabled=True
                        )

                    st.subheader("Extracted Line Items")
                    if 'line_items' in invoice_data and invoice_data['line_items']:
                        line_items_df = pd.DataFrame(invoice_data['line_items'])
                        st.dataframe(line_items_df, use_container_width=True)
                    else:
                        st.warning("No line items were extracted.")
                
                # --- NEW: Raw JSON Visualization ---
                st.markdown("---")
                with st.expander("View Raw JSON Response"):
                    # Pretty-print the JSON with an indent of 2 spaces
                    pretty_json = json.dumps(invoice_data, indent=2)
                    st.code(pretty_json, language='json')

            except json.JSONDecodeError:
                st.error("Failed to parse the extracted data as JSON. The model may have returned an invalid format.")
                st.text_area("Raw AI Response:", response_text, height=300)
            except Exception as e:
                st.error(f"An unexpected error occurred while displaying data: {e}")
                st.text_area("Raw AI Response:", response_text, height=300)