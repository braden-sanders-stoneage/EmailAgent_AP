# Email Agent - Automated Email Categorization & Organization System

## Overview

This is an intelligent email processing system that automatically fetches, categorizes, and organizes emails from Microsoft Outlook using AI-powered classification. The system runs as a Flask API with a background monitoring service that polls the inbox every 60 seconds, then displays results through an **Outlook Add-in** for easy access directly in Outlook Web.

**Key Components:**
- **Flask API** - Serves the Outlook Add-in and provides email data endpoints
- **Background Monitor** - Automatically polls inbox every 60 seconds for new emails
- **AI Classification** - Uses OpenAI GPT-5 to categorize and extract invoice numbers
- **Epicor Integration** - Verifies invoices in Epicor ERP with direct deep links
- **Outlook Add-in** - Displays categorization and invoice data in a sidebar panel

## What It Does

The system performs the following workflow:

1. **Background Monitoring** - Polls inbox every 60 seconds for unread emails
2. **Authenticates** with Microsoft Graph API to access Outlook mailbox
3. **Processes emails** - Downloads and decodes attachments (PDFs, images, etc.)
4. **Cleans HTML content** - Converts HTML email bodies to clean, readable plain text
5. **AI Categorization** - Uses OpenAI GPT-5 to categorize emails and extract invoice numbers
6. **Invoice Verification** - Checks invoice numbers against Epicor ERP and generates deep links
7. **Caches Results** - Saves processed data to JSON files for instant retrieval
8. **Outlook Integration** - Displays results in add-in sidebar when user opens an email

## Email Categories

The AI classifies emails into these six categories:

- **`new_invoice`** - Invoices, bills, or payment requests from vendors/suppliers
- **`supplier_statement`** - Monthly or periodic account statements showing balance and transactions
- **`request_for_status`** - Inquiries about order status, shipment tracking, payment status, or project updates
- **`account_update`** - Notifications about account changes, password resets, profile updates
- **`misc_spam`** - Marketing emails, newsletters, promotional content, or spam
- **`other`** - Anything that doesn't fit the above categories

## Folder Structure

```
EmailAgent_AP/
│
├── app.py                           # Flask API - Main entry point with Outlook Add-in support
│
├── static/                          # Static assets for add-in
│   ├── css/
│   │   └── taskpane.css
│   ├── js/
│   │   └── taskpane.js
│   └── images/
│       ├── icon-16.png
│       ├── icon-32.png
│       └── icon-80.png
│
├── templates/                       # HTML templates for add-in
│   ├── taskpane.html
│   └── commands.html
│
├── outlook-addin/                   # Outlook Add-in manifest
│   └── manifest.xml
│
├── core/                            # Core application modules
│   ├── integrations/                # External service integrations
│   │   ├── outlook/                 # Microsoft Graph API integration
│   │   │   ├── client.py           # Graph API authentication, email fetching, attachment retrieval
│   │   │   └── attachments.py      # Attachment processing (PDFs, images, .msg files)
│   │   └── epicor/                  # ERP system integration
│   │       ├── epicor_utils.py     # Epicor API utilities and authentication
│   │       └── invoices.py         # Invoice verification and URL generation
│   │
│   ├── ai/                          # AI classification module
│   │   └── classifier.py           # OpenAI GPT-5 integration for email categorization & invoice extraction
│   │
│   └── utils/                       # Utility modules
│       ├── monitor_system.py       # Background email monitoring (1-minute polling loop)
│       ├── email_processor.py      # Email processing logic
│       ├── secret_manager.py       # Credentials management (loads from .env)
│       └── log_manager/
│           └── log_manager.py      # Error logging and process tracking
│
├── dev/                             # Development utilities
│   └── generate_cert.py            # SSL certificate generator for local HTTPS
│
└── emails_data/                     # JSON cache for processed emails
    ├── *.json                       # Individual email processing results
    └── id_mapping.json              # Maps email IDs to processed data
```

## How It Works

### 1. Email Fetching (`core/integrations/outlook/client.py`)

- Authenticates with Microsoft Graph API using OAuth2 (tenant ID, client ID, client secret)
- Fetches emails from specified mailbox folder (default: inbox)
- Supports filtering by read/unread status
- Retrieves full email metadata: sender, subject, body, recipients, timestamps
- Downloads raw attachments via Graph API

### 2. HTML Content Cleaning (`core/integrations/outlook/client.py`)

- Uses `html2text` library to convert HTML email bodies to clean markdown/plain text
- Removes scripts, styles, tracking pixels, and zero-width spaces
- Preserves meaningful structure (paragraphs, line breaks)
- Makes email content readable for both humans and AI

### 3. Attachment Processing (`core/integrations/outlook/attachments.py`)

The system handles multiple attachment types:

- **Images** (PNG, JPEG): Decoded and saved, but NOT sent to AI (API limitation)
- **PDFs**: Decoded, saved, AND sent to AI for content analysis
- **Outlook .msg files**: Parsed to extract embedded email content
- **Other files**: Decoded and saved with original filenames

Returns structured data with:
- `images`: List of image attachments
- `other_files`: List of non-image attachments (PDFs, Excel, Word, etc.)
- `processed`: All processed attachments
- `skipped`: Attachments that couldn't be processed

### 4. AI Classification & Invoice Detection (`core/ai/classifier.py`)

Uses OpenAI's Responses API with structured outputs:

**Input to AI:**
- Sender name and email
- Subject line
- Email body (truncated to 2000 chars if needed)
- Attachment note: "X PDF(s), Y image(s)"
- PDF attachments (uploaded as base64-encoded files for analysis)

**AI Analysis:**
- Model: GPT-5 with minimal reasoning effort
- Uses Pydantic structured outputs for consistent response format
- Returns: `EmailCategorization` object with:
  - `email_type`: Category classification
  - `reason`: Explanation for categorization
  - `has_invoice`: Boolean indicating if invoice numbers were found
  - `invoice_numbers`: List of extracted invoice numbers from subject, body, and attachment filenames

**Invoice Detection:**
- AI scans email subject, body content, and attachment filenames
- Recognizes various invoice number patterns (numeric, alphanumeric, with prefixes like "INV-", etc.)
- Examples: "12345", "INV-67890", "C628970"
- Returns empty list if no invoices found

**Error Handling:**
- If AI classification fails, defaults to "other" category
- Prints error details but continues processing

### 5. Email Caching (`core/utils/monitor_system.py`)

**JSON Cache System:**
- Saves processed email data to `emails_data/<email_id>.json`
- Stores complete categorization results, invoice data, and Epicor verification
- Creates ID mapping file for quick lookups by internet message ID
- Enables instant retrieval when user opens add-in

**Cache Structure:**
- One JSON file per processed email
- Contains: category, reason, invoice numbers, Epicor results, sender info
- `id_mapping.json` maps internet message IDs to internal email IDs
- No file size limits - caches all processed emails

### 6. Invoice Verification (`core/integrations/epicor/invoices.py`)

**Epicor Integration:**
When the AI detects invoice numbers in an email, the system automatically verifies them against Epicor ERP:

**Verification Process:**
1. Queries Epicor BAQ (Business Activity Query) `APInvDtl` for each invoice number
2. Checks if invoice exists in the system
3. Extracts vendor number and invoice details from response
4. Generates direct URL to invoice in Epicor web interface

**URL Generation:**
- Constructs deep links to specific invoices in Epicor Kinetic
- URL format includes vendor number, invoice number, company, and workspace identifiers
- Enables one-click access to invoice details in Epicor

**Output:**
Creates `invoices.json` in each email folder containing:
```json
{
  "invoices": [
    {
      "invoice_number": "C628970",
      "found_in_epicor": true,
      "epicor_url": "https://kineticerp.stoneagetools.com/KineticLive/Apps/ERP/Home/..."
    },
    {
      "invoice_number": "12345",
      "found_in_epicor": false
    }
  ]
}
```

**API Details:**
- Uses Epicor REST API v2 with OData queries
- Authenticates with Basic auth + API key
- Filters invoices by `APInvHed_InvoiceNum` field
- Returns vendor info, invoice amounts, payment status, and more

### 7. Secret Management (`core/utils/secret_manager.py`)

Loads credentials from `.env` file:

**Outlook Secrets:**
- `OUTLOOK_TENANT_ID`
- `OUTLOOK_CLIENT_ID`
- `OUTLOOK_CLIENT_SECRET`
- `OUTLOOK_MAILBOX_ID`

**OpenAI Secret:**
- `OPENAI_API_KEY`

**Epicor Secrets:**
- `EPICOR_SERVER` - Epicor server hostname
- `EPICOR_INSTANCE` - Epicor instance name (e.g., "KineticLive")
- `EPICOR_API_KEY` - API key for REST authentication
- `EPICOR_USERNAME` - Username for Basic auth
- `EPICOR_PASSWORD` - Password for Basic auth
- `EPICOR_CHANNEL_ID` - Workspace channel ID for deep linking

**Other Integrations:**
- AWS Cognito credentials
- Marketo credentials
- Optimizely credentials
- Asana credentials

### 8. Logging (`core/utils/log_manager/log_manager.py`)

Tracks:
- Errors with full stack traces
- Attachment processing start/completion
- Saved to timestamped log files in `core/utils/log_manager/log_files/`

## Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Generate SSL Certificate (First Time Only)
```powershell
python dev/generate_cert.py
```

### 3. Start Flask Server
```powershell
python app.py
```

You should see:
```
Email monitor started, checking every 60 seconds...
Starting Flask server on https://localhost:5000
```

### 4. Install Outlook Add-in

1. Open **Outlook Web** (outlook.office.com)
2. Click **Settings** (⚙️) → **View all Outlook settings**
3. Go to **Mail** → **Integrated apps** or **Get Add-ins**
4. Click **"My Add-ins"** → **"Add App from File"**
5. Upload `outlook-addin/manifest.xml`
6. Confirm installation

### 5. Use the Add-in

1. Open any email in Outlook Web
2. Click **"Show Invoice Info"** button in the toolbar
3. Sidebar opens displaying:
   - Email category (color-coded badge)
   - Invoice numbers (if detected)
   - Epicor verification status
   - Vendor, amount, balance, payment status
   - **"Open in Epicor"** buttons with direct deep links

## Process Flow

```
1. Flask server starts (app.py)
   │
   ├─→ Background monitor thread starts
   │   └─→ Polls inbox every 60 seconds
   │
2. Monitor detects unread email
   │
3. Authenticate with Graph API
   │
4. For each unread email:
   │
   ├─→ Fetch email data and attachments
   │
   ├─→ Process attachments (decode PDFs, images)
   │
   ├─→ Categorize with AI:
   │   ├─→ Send email content + PDFs to GPT-5
   │   ├─→ Extract invoice numbers
   │   └─→ Get category classification
   │
   ├─→ Verify invoices in Epicor:
   │   ├─→ Query Epicor API for each invoice
   │   ├─→ Generate deep links to invoices
   │   └─→ Get vendor, amount, balance, status
   │
   ├─→ Apply Outlook category label (color coding)
   │
   └─→ Save results to emails_data/<email_id>.json
   
5. User opens email in Outlook Web
   │
6. User clicks "Show Invoice Info" button
   │
7. Add-in loads in sidebar
   │
8. Add-in calls: GET /api/email/<email_id>
   │
9. Flask returns cached JSON data
   │
10. Add-in displays:
    ├─→ Category badge
    ├─→ Invoice numbers
    ├─→ Epicor verification results
    └─→ "Open in Epicor" buttons
```

## Key Features

### Intelligent HTML Parsing
- Converts messy HTML emails to clean, readable text
- Removes tracking elements, inline styles, and hidden content
- Preserves links and meaningful structure

### Robust Attachment Handling
- Supports PDFs, images, Excel, Word, Outlook .msg files
- Handles duplicate filenames by appending counters
- Base64 decoding with error handling
- PDFs are analyzed by AI for better categorization

### Outlook Add-in Integration
- Displays results directly in Outlook Web sidebar
- No need to navigate folders - instant access from any email
- Color-coded category badges for quick visual identification
- One-click "Open in Epicor" buttons with deep links
- Real-time data retrieval from JSON cache

### AI-Powered Classification & Invoice Extraction
- Context-aware categorization using email content and attachments
- Automatic invoice number detection from subject, body, and filenames
- Recognizes various invoice number formats and patterns
- Structured output format for consistent processing
- Fallback handling for API errors
- Detailed reasoning provided for each classification

### Epicor ERP Integration
- Automatic invoice verification against Epicor system
- Direct deep-linking to invoices in Epicor web interface
- Real-time invoice status checking (paid/unpaid, amounts, vendor info)
- Structured JSON output for downstream automation
- Support for multiple invoice numbers per email

### Scalable Architecture
- Modular design with clear separation of concerns
- Integration folder for external services (Outlook, Epicor, etc.)
- Easy to add new email sources or categories
- Environment-based configuration

## Output Structure

Each processed email is cached as JSON for instant retrieval:

### emails_data/<email_id>.json
```json
{
  "email_id": "AQMkAGNl...",
  "subject": "Invoice C628970",
  "sender_name": "Vendor Name",
  "sender_email": "vendor@example.com",
  "category": "new_invoice",
  "reason": "Email contains an invoice from a supplier",
  "has_invoice": true,
  "invoice_numbers": ["C628970"],
  "epicor_results": [
    {
      "invoice_number": "C628970",
      "found_in_epicor": true,
      "epicor_url": "https://kineticerp.stoneagetools.com/...",
      "invoice_data": {
        "VendorName": "eShipping LLC",
        "DocInvoiceAmt": 697.94,
        "DocInvoiceBal": 697.94,
        "PaymentStatus": "Unpaid",
        "OpenPayable": true
      }
    }
  ],
  "internet_message_id": "<abc123@mail.com>"
}
```

### emails_data/id_mapping.json
Maps internet message IDs to internal email IDs for quick lookup:
```json
{
  "<abc123@mail.com>": "AQMkAGNl..."
}
```

## Debug Features

The system includes comprehensive debug output:
- Number of raw attachments fetched
- Processed attachments structure and counts
- Attachment processing success/failure per file
- AI classification results with reasoning
- Detected invoice numbers
- Epicor API request/response details
- Invoice verification results with clickable URLs
- Folder paths where emails are saved

## Limitations & Considerations

1. **Image Attachments**: Images are saved but NOT sent to the AI (OpenAI Responses API doesn't support image analysis in this format)
2. **Body Truncation**: Email bodies > 2000 characters are truncated before sending to AI
3. **API Costs**: Each email classification costs OpenAI API credits (GPT-5 usage), plus Epicor API calls for invoice verification
4. **Weekly Folders**: Week determination uses MST - may differ for users in other timezones
5. **Read Status**: Currently processes all emails; doesn't mark as read after processing
6. **Invoice Detection**: Relies on AI pattern recognition; may occasionally miss invoices with unusual formatting or identify false positives
7. **Epicor BAQ Dependency**: Requires the `APInvDtl` BAQ to be published and accessible in Epicor

## Future Enhancement Opportunities

- Mark emails as read after successful processing
- Add email reply functionality based on category
- Support for more attachment types (.eml, .zip, etc.)
- Batch processing optimization for large volumes
- Dashboard for viewing categorization statistics
- Email forwarding/routing based on category
- Custom category definitions per user
- Automatic invoice approval workflows based on verification results
- Integration with other ERP modules (Purchase Orders, Receipts, etc.)
- Multi-company support for invoice verification
- Invoice matching: cross-reference invoice numbers with PO numbers

