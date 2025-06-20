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
st.set_page_config(page_title="Invoice Extractor", page_icon="🧾", layout="centered")

# --- Constants ---
# You can change the model here if you wish to use a different one.
# For this task, a model that handles images is required.
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
    Function to get the response from the specified Gemini model.
    It now accepts a list of images.
    """
    try:
        # Initialize the GenerativeModel with the specified model name
        model = genai.GenerativeModel(model_name)
        
        # Prepare the content list for the model
        # The first item is the text prompt.
        # The subsequent items are the images from the list.
        content = [input_prompt]
        content.extend(image_list) # Add all images to the content list
        
        # Generate content
        response = model.generate_content(content)
        
        # Clean the response to ensure it's valid JSON
        cleaned_response = clean_json_string(response.text)
        
        return cleaned_response
    except Exception as e:
        st.error(f"An error occurred with the Gemini API: {e}")
        return None

# --- Application UI ---

st.title("🧾 Multilingual Invoice Data Extractor")
st.write("Upload an invoice in any language (Image or PDF), and the AI will extract key details in English.")

# --- File Uploader for both PDF and Images ---
uploaded_file = st.file_uploader("Choose an invoice file...", type=["jpg", "jpeg", "png", "pdf"])

image_list = []
if uploaded_file is not None:
    # --- Logic to process PDF or Image ---
    if uploaded_file.type == "application/pdf":
        try:
            # Convert PDF to a list of images
            images = convert_from_bytes(uploaded_file.read())
            image_list.extend(images)
            # Display the first page of the PDF as a preview
            st.image(images[0], caption=f"First page of '{uploaded_file.name}'", use_column_width=True)
            st.info(f"PDF processed successfully. Found {len(images)} page(s).")
        except Exception as e:
            st.error(f"Failed to process PDF file: {e}")
            st.warning("Please ensure you have installed the 'poppler' dependency correctly.")
            st.stop()
    else:
        # It's an image file
        image = Image.open(uploaded_file)
        image_list.append(image)
        st.image(image, caption=f"Uploaded Image: '{uploaded_file.name}'", use_column_width=True)

    # --- UPDATED PROMPT DEFINITION ---
    # The prompt is updated to instruct the model to detect the language,
    # extract the data, and translate all textual information to English.
    input_prompt = """
You are an expert multilingual data processor specializing in invoices. Your non-negotiable task is to extract key information from the invoice and provide ALL textual output in English.

This translation requirement is the most critical part of your task. You must not return any names, addresses, or item descriptions in their original language.

**Crucial Example:** If the invoice shows a customer address as "上海市徐汇区肇嘉浜路798号506室", your JSON output for "customer_address" MUST be the translated and formatted English version, such as "Room 506, No. 798, Zhaojiabang Road, Xuhui District, Shanghai, China". Do not, under any circumstances, return the original Chinese text. Apply this translation logic to all text fields.
    Your process should be as follows:
    1.  First, automatically detect the language of the invoice.
    2.  Next, extract the key information listed below.
    3.  Translate all extracted textual data into English. This includes fields like Biller Name, Biller Address, Customer Name, Customer Address, and the Description for each line item.
    4.  Do NOT translate numeric values (IDs, quantities, prices, totals) or dates. Standardize dates to a common format like YYYY-MM-DD if possible.

    Please extract the following 10 fields ensuring all text values are translated to English:
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

    # --- Process Button and Extraction Logic ---
    if st.button("Extract Information"):
        if not image_list:
            st.warning("No images found to process. Please upload a valid file.")
        else:
            with st.spinner("Analyzing invoice and translating to English..."):
                # Get response from Gemini, passing the list of images
                response_text = get_gemini_response(input_prompt, image_list, model_name)

                if response_text:
                    try:
                        # Parse the JSON response
                        invoice_data = json.loads(response_text)
                        st.success("Invoice data extracted and translated successfully!")

                        # --- Display Extracted Information ---
                        st.subheader("Extracted Key Information (in English)")
                        
                        col1, col2 = st.columns(2)
                        key_fields = {k: v for k, v in invoice_data.items() if k != 'line_items'}
                        fields_list = list(key_fields.items())
                        mid_point = (len(fields_list) + 1) // 2
                        
                        with col1:
                            for key, value in fields_list[:mid_point]:
                                st.text_input(f"**{key.replace('_', ' ').title()}**", value, key=f"col1_{key}", disabled=True)
                        
                        with col2:
                            for key, value in fields_list[mid_point:]:
                                st.text_input(f"**{key.replace('_', ' ').title()}**", value, key=f"col2_{key}", disabled=True)

                        # Display Line Items in a table
                        st.subheader("Line Items (in English)")
                        if 'line_items' in invoice_data and invoice_data['line_items']:
                            line_items_df = pd.DataFrame(invoice_data['line_items'])
                            st.dataframe(line_items_df, use_container_width=True)
                        else:
                            st.warning("No line items were extracted.")

                    except json.JSONDecodeError:
                        st.error("Failed to parse the extracted data as JSON. The model may have returned an invalid format.")
                        st.text_area("Raw AI Response:", response_text, height=300)
                    except Exception as e:
                        st.error(f"An unexpected error occurred while displaying data: {e}")
                        st.text_area("Raw AI Response:", response_text, height=300)
else:
    st.info("Please upload a PDF or image file to get started.")