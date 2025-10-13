Office.initialize = function () {
    console.log('Office.js initialized');
};

Office.onReady(function () {
    loadEmailData();
});

function loadEmailData() {
    const item = Office.context.mailbox.item;
    
    if (!item) {
        showError('Unable to access email item');
        return;
    }
    
    const internetMessageId = item.internetMessageId;
    
    if (!internetMessageId) {
        showError('Email ID not available');
        return;
    }
    
    const cleanId = internetMessageId.replace(/[<>]/g, '');
    const apiUrl = `https://localhost:5000/api/email/${encodeURIComponent(cleanId)}`;
    
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Email not processed yet. Please wait up to 1 minute and refresh.');
                }
                throw new Error('Unable to load email data');
            }
            return response.json();
        })
        .then(data => {
            displayEmailData(data);
        })
        .catch(error => {
            showError(error.message);
        });
}

function displayEmailData(data) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('content').style.display = 'block';
    
    const categoryBadge = document.getElementById('categoryBadge');
    categoryBadge.textContent = data.category.replace('_', ' ');
    categoryBadge.className = `badge ${data.category}`;
    
    const categoryReason = document.getElementById('categoryReason');
    categoryReason.textContent = data.reason;
    
    if (data.has_invoice && data.epicor_results && data.epicor_results.length > 0) {
        document.getElementById('invoiceSection').style.display = 'block';
        document.getElementById('noInvoice').style.display = 'none';
        
        const invoiceList = document.getElementById('invoiceList');
        invoiceList.innerHTML = '';
        
        data.epicor_results.forEach(invoice => {
            const invoiceItem = createInvoiceItem(invoice);
            invoiceList.appendChild(invoiceItem);
        });
    } else {
        document.getElementById('invoiceSection').style.display = 'none';
        document.getElementById('noInvoice').style.display = 'block';
    }
}

function createInvoiceItem(invoice) {
    const item = document.createElement('div');
    item.className = 'invoice-item';
    
    const numberDiv = document.createElement('div');
    numberDiv.className = 'invoice-number';
    numberDiv.textContent = `Invoice: ${invoice.invoice_number}`;
    
    const statusSpan = document.createElement('span');
    statusSpan.className = invoice.found_in_epicor ? 'invoice-status found' : 'invoice-status not-found';
    statusSpan.textContent = invoice.found_in_epicor ? 'Found' : 'Not Found';
    numberDiv.appendChild(statusSpan);
    
    item.appendChild(numberDiv);
    
    if (invoice.found_in_epicor && invoice.invoice_data) {
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'invoice-details';
        
        if (invoice.invoice_data.VendorName) {
            const vendorDiv = document.createElement('div');
            vendorDiv.textContent = `Vendor: ${invoice.invoice_data.VendorName}`;
            detailsDiv.appendChild(vendorDiv);
        }
        
        if (invoice.invoice_data.DocInvoiceAmt !== null && invoice.invoice_data.DocInvoiceAmt !== undefined) {
            const amountDiv = document.createElement('div');
            amountDiv.textContent = `Amount: $${invoice.invoice_data.DocInvoiceAmt.toFixed(2)}`;
            detailsDiv.appendChild(amountDiv);
        }
        
        if (invoice.invoice_data.DocInvoiceBal !== null && invoice.invoice_data.DocInvoiceBal !== undefined) {
            const balanceDiv = document.createElement('div');
            balanceDiv.textContent = `Balance: $${invoice.invoice_data.DocInvoiceBal.toFixed(2)}`;
            detailsDiv.appendChild(balanceDiv);
        }
        
        if (invoice.invoice_data.PaymentStatus) {
            const statusDiv = document.createElement('div');
            statusDiv.textContent = `Status: ${invoice.invoice_data.PaymentStatus}`;
            detailsDiv.appendChild(statusDiv);
        }
        
        item.appendChild(detailsDiv);
        
        if (invoice.epicor_url) {
            const button = document.createElement('button');
            button.className = 'epicor-button';
            button.textContent = 'Open in Epicor';
            button.onclick = function() {
                window.open(invoice.epicor_url, '_blank');
            };
            item.appendChild(button);
        }
    }
    
    return item;
}

function showError(message) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('content').style.display = 'none';
    document.getElementById('error').style.display = 'block';
    document.getElementById('errorText').textContent = message;
}

