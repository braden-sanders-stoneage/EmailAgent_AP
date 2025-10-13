# Email Agent - Automated Email Categorization & Organization System

## Overview

This is an intelligent email processing system that automatically fetches, categorizes, and organizes emails from Microsoft Outlook using AI-powered classification. The system uses OpenAI's GPT-5 to analyze email content and attachments, extracts invoice numbers, verifies them against Epicor ERP, and saves everything into a structured folder hierarchy organized by business week and category.

## What It Does

The system performs the following workflow:

1. **Authenticates** with Microsoft Graph API to access Outlook mailbox
2. **Fetches emails** from the inbox (configurable to include read/unread)
3. **Processes attachments** - Downloads and decodes PDFs, images, and other file types
4. **Cleans HTML content** - Converts HTML email bodies to clean, readable plain text
5. **AI Categorization** - Uses OpenAI GPT-5 to categorize each email into one of six predefined categories and extract invoice numbers
6. **Organizes & Saves** - Saves emails with their attachments into a structured folder system organized by business week
7. **Invoice Verification** - Checks extracted invoice numbers against Epicor ERP and generates direct links to invoices

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
│       ├── file_system.py          # Email organization and file system management
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

### 5. Email Organization (`core/utils/file_system.py`)

**Weekly Folder Management:**
- Calculates current business week (Monday-Sunday) in Mountain Standard Time (MST)
- Sunday emails belong to the PREVIOUS week
- Format: `Week_Of_Oct_13_2025` (where Oct 13 is the Monday)
- Automatically creates new week folders each Monday

**Folder Creation Process:**
1. Determine current week folder (`Week_Of_Oct_13_2025`)
2. Create category subfolder (`new_invoice`, etc.)
3. Create email-specific folder: `{sanitized_subject}_{timestamp}`
4. Save `email_details.txt` with full email content
5. Save all attachments with original filenames

**Subject Sanitization:**
- Converts to lowercase snake_case
- Removes special characters
- Replaces spaces/hyphens with underscores
- Truncates to 50 characters
- Handles empty subjects → "no_subject"

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

## Process Flow

```
1. main.py starts
   │
2. Authenticate with Graph API
   │
3. Fetch emails (limit: 10, configurable)
   │
4. For each email:
   │
   ├─→ Print email preview (from, subject, date, body preview)
   │
   ├─→ If has attachments:
   │   ├─→ Fetch raw attachments
   │   └─→ Process attachments (decode base64, identify types)
   │
   ├─→ Categorize with AI:
   │   ├─→ Send email data + PDFs to GPT-5
   │   ├─→ Get structured response (category + reason + invoice detection)
   │   └─→ Print categorization result and invoice numbers
   │
   ├─→ Save to organized folders:
   │   ├─→ Calculate week folder
   │   ├─→ Create category subfolder
   │   ├─→ Create email-specific folder
   │   ├─→ Save email_details.txt
   │   └─→ Save all attachments
   │
   └─→ If invoices detected:
       ├─→ Query Epicor for each invoice number
       ├─→ Generate Epicor URLs for found invoices
       └─→ Save invoices.json
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

### Business Week Organization
- Automatic weekly folder creation based on Monday start date
- Mountain Standard Time (MST) timezone
- Sunday emails go into the previous week's folder
- Historical weeks remain intact

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

Each processed email results in:

```
emails/Week_Of_Oct_13_2025/new_invoice/invoice_payment_20251013_115523/
├── email_details.txt          # Full email content
├── invoice.pdf                 # Attachment 1
├── receipt.xlsx               # Attachment 2
└── invoices.json  # Epicor verification results (if invoices detected)
```

**email_details.txt format:**
```
FROM: Sender Name <sender@example.com>
SUBJECT: Invoice #12345
DATE: 2025-10-13T11:55:23Z

BODY:
[Clean, readable email content]
```

**invoices.json format:**
```json
{
  "invoices": [
    {
      "invoice_number": "C628970",
      "found_in_epicor": true,
      "epicor_url": "https://kineticerp.stoneagetools.com/KineticLive/Apps/ERP/Home/#/view/APGO1070/Erp.UI.APInvoiceTracker?..."
    },
    {
      "invoice_number": "INV-12345",
      "found_in_epicor": false
    }
  ]
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

