# Invoice Structured Data Extractor API

A high-reliability **FastAPI service** that extracts structured invoice information from unstructured, free-form text. The API combines deterministic pattern recognition with local Large Language Model (LLM) processing to extract key invoice fields while maintaining schema validation and resilience against malformed inputs.

**Live Endpoint:** https://local-llm-structured-output.onrender.com/extract

![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg?style=flat&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Validation-E92063.svg?style=flat)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black.svg?style=flat)

---

## ✨ Features

- **Structured Data Extraction:** Extracts vendor name, invoice amount, currency, and date from free-form invoice text.
- **Schema Validation:** Uses Pydantic models to enforce the expected response structure and field types.
- **Date-Aware Amount Parsing:** Identifies date components such as `2026-05-12` to prevent date values from being mistaken for invoice amounts.
- **Precise Numeric Matching:** Uses strict digit boundaries to reduce numeric truncation errors, such as parsing `8700.04` as `870`.
- **Fault Tolerance:** Handles empty, noisy, and malformed inputs with appropriate fallback responses or validation errors.
- **Local LLM Integration:** Supports local language model processing through Ollama, depending on the configured implementation.
- **REST API:** Provides a simple HTTP interface for integration with applications and automated workflows.

## 🚀 Live API

The deployed API endpoint is:

```text
https://local-llm-structured-output.onrender.com/extract
```

**HTTP Method:** `POST`

**Content-Type:** `application/json`

## 📌 API Specification

### `POST /extract`

Extracts structured invoice information from raw text and returns a JSON object.

#### Request Body

```json
{
  "text": "Invoice from Acme-9821 Ltd. Total amount due: EUR 1001.15 payable by 2026-08-12."
}
```

#### Successful Response — `200 OK`

```json
{
  "vendor": "Acme-9821 Ltd.",
  "amount": 1001.15,
  "currency": "EUR",
  "date": "2026-08-12"
}
```

### Response Field Specifications

| Field | Type | Description | Example |
|---|---|---|---|
| `vendor` | String | Supplier or business name | `"Acme-9821 Ltd."` |
| `amount` | Number | Extracted invoice amount due | `1001.15` |
| `currency` | String | Three-letter uppercase currency code | `"EUR"` |
| `date` | String | Extracted date in `YYYY-MM-DD` format | `"2026-08-12"` |

The extraction logic aims to identify the relevant invoice values while avoiding common parsing errors involving dates and numeric boundaries.

## 🛡️ Error and Edge Case Handling

The service is designed to handle several types of input.

### 1. Empty Input

**Request**

```json
{
  "text": ""
}
```

**Expected fallback response**

```json
{
  "vendor": "Unknown Vendor",
  "amount": 0.0,
  "currency": "USD",
  "date": "2026-01-01"
}
```

The fallback values shown above reflect the documented behavior of this implementation.

### 2. Garbage or Unstructured Input

**Request**

```json
{
  "text": "asdfghjk 1234 !!!"
}
```

**Example fallback response**

```json
{
  "vendor": "Unknown Vendor",
  "amount": 0.0,
  "currency": "USD",
  "date": "2026-01-01"
}
```

The extraction logic attempts to handle noisy input without crashing. The exact result depends on the implementation's validation and fallback rules.

### 3. Malformed Request Payload

Requests that do not conform to the expected input schema can return:

```text
HTTP 422 Unprocessable Entity
```

FastAPI provides request validation and error details for invalid payloads.

## 🧪 Usage Examples

### Example 1: Standard Invoice Extraction

Use cURL to send an invoice to the deployed API.

```bash
curl -X POST "https://local-llm-structured-output.onrender.com/extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "Billed By: Apex Solutions. Total Due $8237.34. Due date 2026-11-04."}'
```

**Example response**

```json
{
  "vendor": "Apex Solutions",
  "amount": 8237.34,
  "currency": "USD",
  "date": "2026-11-04"
}
```

### Example 2: Extracting a Different Currency

```bash
curl -X POST "https://local-llm-structured-output.onrender.com/extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "Vendor: Global Supplies. Invoice total: GBP 245.80. Invoice date: 2026-09-15."}'
```

**Example response**

```json
{
  "vendor": "Global Supplies",
  "amount": 245.80,
  "currency": "GBP",
  "date": "2026-09-15"
}
```

### Example 3: Testing Empty or Noisy Input

```bash
curl -X POST "https://local-llm-structured-output.onrender.com/extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "asdfghjk 1234 !!!"}'
```

Inspect the returned JSON to verify how the deployed service handles noisy text.

## 🛠️ Local Setup and Development

### Prerequisites

- Python 3.10 or later
- pip
- Git
- Ollama (optional, if using a locally hosted LLM)

### 1. Clone the Repository

Replace `YOUR_USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR_USERNAME/local-llm-invoice-extractor.git
cd local-llm-invoice-extractor
```

### 2. Create a Virtual Environment

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ensure that `requirements.txt` contains the dependencies required by your application.

### 4. Configure the Local LLM (Optional)

If the application uses Ollama, install and start Ollama, then download the model configured in your application.

For example, to use `llama3.2`:

```bash
ollama pull llama3.2
```

Make sure the Ollama service is running and that the model name matches the configuration in your code.

> If your implementation uses only deterministic extraction or a different LLM provider, follow the corresponding application configuration instead.

### 5. Start the FastAPI Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The local API will be available at:

- API endpoint: http://127.0.0.1:8000/extract
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 📁 Repository Structure

```text
local-llm-invoice-extractor/
├── main.py              # FastAPI application and extraction endpoint
├── requirements.txt     # Python dependencies
├── README.md            # Project documentation
└── .gitignore           # Git ignore rules
```

The structure above is a suggested layout. Include any additional modules, configuration files, or Docker files that exist in your actual repository.

## ⚙️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| FastAPI | REST API framework |
| Pydantic | Input and output schema validation |
| Regular expressions | Pattern-based field extraction |
| Ollama | Optional local LLM inference |
| Uvicorn | ASGI application server |
| Render | Cloud deployment |

## 🔄 Processing Workflow

1. The client submits raw invoice text through the `/extract` endpoint.
2. FastAPI validates the incoming request.
3. The extraction logic identifies relevant invoice fields using deterministic patterns and, where configured, local LLM processing.
4. Date-aware and numeric-boundary checks help prevent common extraction errors.
5. Pydantic validates the resulting data structure.
6. The API returns structured JSON or an appropriate validation error.

## 🔒 Reliability Considerations

For production use, consider the following improvements:

- Validate extracted dates and currency codes against accepted formats and supported currency codes.
- Distinguish missing values from genuine zero amounts instead of silently treating every failure as a valid invoice.
- Add confidence scores or validation flags for uncertain extractions.
- Test invoices containing multiple amounts, tax values, subtotals, and payment dates.
- Add request size limits and timeouts for LLM processing.
- Avoid logging sensitive invoice contents or personal information.
- Add automated unit and integration tests for empty inputs, malformed payloads, and ambiguous amounts.

---

**Built with FastAPI for reliable, schema-validated invoice data extraction.**
