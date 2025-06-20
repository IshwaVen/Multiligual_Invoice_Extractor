# Multiligual Invoice Extractor 🧾

A powerful, multilingual invoice processing application powered by Google's Gemini Pro Vision. This Streamlit web app allows users to upload invoices in any format (PDF, JPG, PNG) and any language, and instantly extracts, translates, and structures the key information for easy verification and use.

## ✨ Key Features

-   **Multilingual & Multi-format:** Accepts PDFs and common image formats, automatically detecting the language of the invoice.
-   **Intelligent Data Extraction:** Uses the Gemini 1.5 Flash model to identify and extract 10 key invoice fields plus all line items.
-   **Automatic Translation:** All extracted textual data (biller name, address, item descriptions) is translated into English for standardized output.
-   **Side-by-Side Verification:** A user-friendly interface displays the invoice image next to the extracted data for easy and accurate validation.
-   **API Usage Analytics:** Provides a clear breakdown of the tokens used for each API call, helping to monitor costs.
-   **Developer-Friendly Output:** Displays the raw, structured JSON response for easy debugging or integration with other systems.

## 🛠️ Technology Stack

-   **Backend & ML:** Python
-   **AI Model:** Google Gemini 1.5 Flash (via `google-generativeai` SDK)
-   **Web Framework:** Streamlit
-   **PDF Processing:** `pdf2image` & `poppler`
-   **Data Handling:** Pandas
-   **Environment Management:** `dotenv`