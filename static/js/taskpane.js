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

let currentEmailData = null;

function displayEmailData(data) {
    currentEmailData = data;
    
    document.getElementById('loading').style.display = 'none';
    document.getElementById('content').style.display = 'block';
    
    const categoryBadge = document.getElementById('categoryBadge');
    categoryBadge.textContent = data.category.replace('_', ' ');
    categoryBadge.className = `badge ${data.category}`;
    
    const categoryReason = document.getElementById('categoryReason');
    categoryReason.textContent = data.reason;
    
    const shouldShowImport = data.category === 'new_invoice' && 
                             data.extracted_invoice_data && 
                             (!data.has_invoice || !data.epicor_results || 
                              data.epicor_results.some(r => !r.found_in_epicor));
    
    if (shouldShowImport) {
        document.getElementById('invoiceDataSection').style.display = 'block';
        displayInvoiceData(data.extracted_invoice_data);
    } else {
        document.getElementById('invoiceDataSection').style.display = 'none';
    }
    
    if (data.has_invoice && data.epicor_results && data.epicor_results.length > 0) {
        document.getElementById('invoiceSection').style.display = 'block';
        document.getElementById('noInvoice').style.display = 'none';
        
        const invoiceList = document.getElementById('invoiceList');
        invoiceList.innerHTML = '';
        
        data.epicor_results.forEach(invoice => {
            const invoiceItem = createInvoiceItem(invoice);
            invoiceList.appendChild(invoiceItem);
        });
    } else if (!shouldShowImport) {
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

function displayInvoiceData(invoiceData) {
    const vendorSelect = document.getElementById('vendorSelect');
    vendorSelect.innerHTML = '';
    
    if (invoiceData.vendor_matches && invoiceData.vendor_matches.length > 0) {
        invoiceData.vendor_matches.forEach((vendor, index) => {
            const option = document.createElement('option');
            option.value = vendor.vendor_id;
            option.textContent = `${vendor.vendor_name} (${vendor.confidence}%)`;
            if (index === 0) option.selected = true;
            vendorSelect.appendChild(option);
        });
    } else {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No vendor match found';
        vendorSelect.appendChild(option);
    }
    
    document.getElementById('vendorConfidence').innerHTML = renderConfidenceIndicator(invoiceData.vendor_name_confidence);
    
    document.getElementById('invoiceNumber').value = invoiceData.invoice_number || '';
    document.getElementById('invoiceNumberConfidence').innerHTML = renderConfidenceIndicator(invoiceData.invoice_number_confidence);
    
    document.getElementById('invoiceDate').value = invoiceData.invoice_date || '';
    document.getElementById('invoiceDateConfidence').innerHTML = renderConfidenceIndicator(invoiceData.invoice_date_confidence);
    
    document.getElementById('invoiceTotal').value = invoiceData.invoice_total || '';
    document.getElementById('invoiceTotalConfidence').innerHTML = renderConfidenceIndicator(invoiceData.invoice_total_confidence);
    
    const lineItems = invoiceData.line_items || [];
    document.getElementById('lineItemCount').textContent = lineItems.length;
    
    const lineItemsBody = document.getElementById('lineItemsBody');
    lineItemsBody.innerHTML = '';
    
    lineItems.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="text" value="${item.part_number || ''}" data-line="${index}" data-field="part_number"></td>
            <td><input type="text" value="${item.description || ''}" data-line="${index}" data-field="description"></td>
            <td><input type="number" step="0.01" value="${item.quantity || 1}" data-line="${index}" data-field="quantity"></td>
            <td><input type="number" step="0.01" value="${item.unit_price || 0}" data-line="${index}" data-field="unit_price"></td>
            <td><input type="number" step="0.01" value="${item.line_total || 0}" data-line="${index}" data-field="line_total"></td>
        `;
        lineItemsBody.appendChild(row);
    });
}

function renderConfidenceIndicator(score) {
    let className = 'confidence-low';
    let symbol = '🔴';
    
    if (score >= 90) {
        className = 'confidence-high';
        symbol = '🟢';
    } else if (score >= 70) {
        className = 'confidence-medium';
        symbol = '🟡';
    }
    
    return `<span class="${className}" title="Confidence: ${score}%">${symbol}</span>`;
}

function toggleLineItems() {
    const expanded = document.getElementById('lineItemsExpanded');
    const toggle = document.querySelector('.line-items-toggle');
    
    if (expanded.style.display === 'none') {
        expanded.style.display = 'block';
        toggle.classList.add('expanded');
    } else {
        expanded.style.display = 'none';
        toggle.classList.remove('expanded');
    }
}

function collectInvoiceData() {
    const vendorId = document.getElementById('vendorSelect').value;
    const invoiceNum = document.getElementById('invoiceNumber').value;
    const invoiceDate = document.getElementById('invoiceDate').value;
    const invoiceTotal = parseFloat(document.getElementById('invoiceTotal').value);
    
    const lineItems = [];
    const rows = document.querySelectorAll('#lineItemsBody tr');
    
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        lineItems.push({
            part_number: inputs[0].value || null,
            description: inputs[1].value,
            quantity: parseFloat(inputs[2].value) || 1,
            unit_price: parseFloat(inputs[3].value) || 0,
            line_total: parseFloat(inputs[4].value) || null
        });
    });
    
    return {
        vendor_id: vendorId,
        invoice_num: invoiceNum,
        invoice_date: invoiceDate,
        invoice_total: invoiceTotal,
        line_items: lineItems
    };
}

function importToEpicor() {
    const button = document.getElementById('importToEpicorBtn');
    button.disabled = true;
    button.textContent = 'Importing...';
    
    const invoiceData = collectInvoiceData();
    
    if (!invoiceData.vendor_id) {
        alert('Please select a vendor');
        button.disabled = false;
        button.textContent = 'Import to Epicor';
        return;
    }
    
    if (!invoiceData.invoice_num || !invoiceData.invoice_date || !invoiceData.invoice_total) {
        alert('Please fill in all required fields');
        button.disabled = false;
        button.textContent = 'Import to Epicor';
        return;
    }
    
    fetch('https://localhost:5000/api/invoice/import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(invoiceData)
    })
    .then(response => response.json())
    .then(result => {
        button.disabled = false;
        button.textContent = 'Import to Epicor';
        
        if (result.success) {
            showSuccessModal(result.epicor_url);
        } else {
            alert('Import failed: ' + result.error);
        }
    })
    .catch(error => {
        button.disabled = false;
        button.textContent = 'Import to Epicor';
        alert('Import failed: ' + error.message);
    });
}

function showSuccessModal(epicorUrl) {
    const modal = document.createElement('div');
    modal.className = 'success-modal';
    modal.innerHTML = `
        <div class="success-modal-content">
            <h3>✅ Invoice Imported Successfully!</h3>
            <p>The invoice has been created in Epicor as a draft. Click below to review it.</p>
            <button onclick="window.open('${epicorUrl}', '_blank')">Open in Epicor</button>
            <button onclick="this.parentElement.parentElement.remove()">Close</button>
        </div>
    `;
    document.body.appendChild(modal);
}

