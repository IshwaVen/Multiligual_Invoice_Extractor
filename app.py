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

load_dotenv()

api_key = os.getenv("api_key")

print(f'API key: {api_key}')


# --- Configuration ---
st.set_page_config(page_title="Invoice Extractor", page_icon="🧾", layout="centered")

# --- Constants ---
# You can change the model here if you wish to use a different one.
# For this task, 'gemini-pro-vision' is required as it handles images.
GEMINI_MODEL = "gemini-pro-vision" 
# You create an instance of the specific model you need.
model = genai.GenerativeModel('gemini-pro-vision')
# This is the actual call that sends your data to Google's servers.
response = model.generate_content([input_prompt, image_list])
genai.configure(api_key=api_key)

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


def get_gemini_response(input_prompt, image_list, api_key, model_name):
    """
    Function to get the response from the specified Gemini model.
    It now accepts a list of images.
    """
    try:
        # --- Where the API Key is used ---
        # The API key is configured here for the genai library.
        genai.configure(api_key=api_key)
        
        # --- Where the Model Name is used ---
        # The model name is used here to initialize the GenerativeModel.
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

st.title("🧾 Invoice Data Extractor")
st.write("Upload an invoice (Image or PDF), and the AI will extract key details and line items.")

# --- API Key Input in Sidebar ---
with st.sidebar:
    st.header("Configuration")
    # --- Where to mention the API Key ---
    # The user enters the API key here. It is stored in the 'api_key' variable.
    api_key = st.text_input("Enter your Google Gemini API Key", type="password", help="Get your API key from Google AI Studio.")
    
    if not api_key:
        st.warning("Please enter your API key to proceed.")
        st.stop()
    st.markdown("---")
    st.info("Get your free Gemini API key from [Google AI Studio](https://aistudio.google.com/).")


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
            st.warning("Please ensure you have installed the 'poppler' dependency correctly (see instructions).")
            st.stop()
    else:
        # It's an image file
        image = Image.open(uploaded_file)
        image_list.append(image)
        st.image(image, caption=f"Uploaded Image: '{uploaded_file.name}'", use_column_width=True)

    # --- Prompt Definition ---
    input_prompt = """
    You are an expert in invoice data extraction. Your task is to analyze the provided invoice image(s)
    and extract key information. The invoice can be in any language and may span multiple pages.

    Please extract the following 10 fields:
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
    - Description
    - Quantity
    - Unit Price
    - Line Total

    Provide the output in a single, structured JSON format.
    The JSON should have a main object with the 10 key fields, and a 'line_items' key
    which is an array of objects, where each object represents a line item.
    If a field is not found, return "N/A".
    
    Example JSON structure:
    {
      "invoice_id": "value",
      "invoice_date": "value",
      "due_date": "value",
      "biller_name": "value",
      "biller_address": "value",
      "customer_name": "value",
      "customer_address": "value",
      "subtotal": "value",
      "total_tax": "value",
      "total_amount": "value",
      "line_items": [
        {"description": "value", "quantity": "value", "unit_price": "value", "line_total": "value"},
        {"description": "value", "quantity": "value", "unit_price": "value", "line_total": "value"}
      ]
    }
    """

    # --- Process Button and Extraction Logic ---
    if st.button("Extract Information"):
        if not image_list:
            st.warning("No images found to process. Please upload a valid file.")
        else:
            with st.spinner("Processing invoice... Please wait."):
                # Get response from Gemini, passing the list of images
                response_text = get_gemini_response(input_prompt, image_list, api_key, GEMINI_MODEL)

                if response_text:
                    try:
                        # Parse the JSON response
                        invoice_data = json.loads(response_text)
                        st.success("Invoice data extracted successfully!")

                        # --- Display Extracted Information ---
                        st.subheader("Extracted Key Information")
                        
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
                        st.subheader("Line Items")
                        if 'line_items' in invoice_data and invoice_data['line_items']:
                            line_items_df = pd.DataFrame(invoice_data['line_items'])
                            st.dataframe(line_items_df)
                        else:
                            st.warning("No line items were extracted.")

                    except json.JSONDecodeError:
                        st.error("Failed to parse the extracted data as JSON. The model may have returned an invalid format.")
                        st.text_area("Raw AI Response:", response_text, height=300)
                    except Exception as e:
                        st.error(f"An unexpected error occurred while displaying data: {e}")
                        st.text_area("Raw AI Response:", response_text, height=300)
else:
    st.info("Please upload PDF file to get started.")