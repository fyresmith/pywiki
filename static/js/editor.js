function saveToFile() {
    // Create a Blob with the content
    let blob = new Blob([document.getElementById('editor').value], { type: 'text/plain' });

    // Create a link element
    let link = document.createElement('a');

    // Set the download attribute and create a URL for the Blob
    link.download = '{{ page }}.txt';
    link.href = URL.createObjectURL(blob);

    // Append the link to the document body
    document.body.appendChild(link);

    // Trigger a click on the link to initiate the download
    link.click();

    // Remove the link from the document body
    document.body.removeChild(link);
}

function saveData() {
    let editor = document.getElementById('editor');
    let page = document.getElementById('page');

    // Create a FormData object and append form data
    let formData = new FormData();
    formData.append('editorContent', editor.value);
    formData.append('page', page.value);

    // Make a POST request using Fetch API
    fetch('/save-file', { method: 'POST', body: formData })
        .then(response => {
            if (response.ok) {
                showMessage('Saved', 'success');
                console.log('POST request successful');
            } else {
                showMessage('Failed to Save, Downloading Backup', 'danger');
                saveToFile()
                console.error('POST request failed');
            }
        })
        .catch(error => {
            showMessage('Failed to Save, Downloading Backup', 'danger');
            saveToFile()
            console.error('Error in POST request:', error);
        });

    return new Promise((resolve, reject) => {
        setTimeout(() => {
            resolve();
        }, 200);
    });
}

document.addEventListener("keydown", function(e) {
    if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        saveData();
    }
});

window.onload = function() {
    window.addEventListener("beforeunload", function (e) {
        if (formSubmitting) {
            return undefined;
        }

        let confirmationMessage = 'It looks like you have been editing something. '
                                + 'If you leave before saving, your changes will be lost.';

        (e || window.event).returnValue = confirmationMessage; //Gecko + IE
        return confirmationMessage; //Gecko + Webkit, Safari, Chrome etc.
    });
};

function returnToPage() {
    saveData().then(() => {
        let page = document.getElementById('page');
        window.location.href = '/page?page=' + page.value;
    }).catch(error => {
        showMessage("There was an error returning to the page.", 'danger')
        console.error(error);
    });
}

function showMessage(text, type) {
    let message = document.getElementById('message');

    if (type === 'danger') {
        message.style.color = "#dc3545";
    } else if (type === 'warning') {
        message.style.color = "#ffc107"
    } else {
        message.style.color = "#28a745";
    }

    message.innerText = text;

    // Set opacity to 1 to initiate fade-in effect
    message.style.opacity = '1';

    // Schedule fade-out after 5 seconds
    setTimeout(function() {
        message.style.opacity = '0';
    }, 1000);
}

function debounce(func, delay) {
    let timeoutId;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(context, args), delay);
    };
}

function updatePageName() {
    let new_page = document.getElementById('page_title');
    let page = document.getElementById('page');
    let page_title = document.getElementById('top_title');

    new_page.value = new_page.value.trim()

    // Create a FormData object and append form data
    let formData = new FormData();
    formData.append('action', 'save');
    formData.append('new_page', new_page.value);
    formData.append('page', page.value);

    // Make a POST request using Fetch API
    fetch('/update-page-name', { method: 'POST', body: formData })
        .then(response => {
            if (response.ok) {
                showMessage('Updated Title', 'success');
                console.log('POST request successful');
                page.value = new_page.value
                page_title.innerText = new_page.value
                history.pushState({}, '', '/editor?page=' + new_page.value);
            } else {
                showMessage('Title Already Exists', 'danger');
                new_page.value = page.value
                console.error('POST request failed');
            }
        })
        .catch(error => {
            showMessage('Failed to Update', 'danger');
            console.error('Error in POST request:', error);
        });
}

function updateCategoryName() {
    let new_category = document.getElementById('page_category');
    let page = document.getElementById('page');
    let category = document.getElementById('category');

    new_category.value = new_category.value.trim()

    // Create a FormData object and append form data
    let formData = new FormData();
    formData.append('action', 'save');
    formData.append('new_category', new_category.value);
    formData.append('page', page.value);

    // Make a POST request using Fetch API
    fetch('/update-page-category', { method: 'POST', body: formData })
        .then(response => {
            if (response.ok) {
                showMessage('Updated Categories', 'success');
                console.log('POST request successful');
                category.value = new_category.value
                history.pushState({}, '', '/editor?page=' + new_category.value);
            } else {
                showMessage('Failed to Update', 'danger');
                new_category.value = category.value
                console.error('POST request failed');
            }
        })
        .catch(error => {
            showMessage('Failed to Update', 'danger');
            console.error('Error in POST request:', error);
        });
}

// document.addEventListener('keydown', function(event) {
//     if ((event.metaKey || event.ctrlKey) && event.key === 'b') {
//         event.preventDefault(); // Prevent the default browser behavior (e.g., bookmark)
//         toggleTextWrapper('**');
//     }
//
//     if ((event.metaKey || event.ctrlKey) && event.key === 'i') {
//         event.preventDefault(); // Prevent the default browser behavior (e.g., undo typing)
//         toggleTextWrapper('*')
//     }
// });

// function toggleTextWrapper(wrapper) {
//     let textarea = document.getElementById('editor');
//     let start = textarea.selectionStart;
//     let end = textarea.selectionEnd;
//
//     if (start !== undefined && end !== undefined) {
//         let textBefore = textarea.value.substring(0, start);
//         let selectedText = textarea.value.substring(start, end);
//         let textAfter = textarea.value.substring(end);
//
//         if (
//             (textBefore.endsWith(wrapper) && textAfter.startsWith(wrapper))
//         ) {
//             // Remove existing wrapper at the beginning of textAfter
//             if (textAfter.startsWith(wrapper)) {
//                 textAfter = textAfter.slice(wrapper.length);
//             }
//
//             // Remove existing wrapper at the end of textBefore
//             if (textBefore.endsWith(wrapper)) {
//                 textBefore = textBefore.slice(0, -wrapper.length);
//             }
//
//             // Remove existing wrapper
//             textarea.value = textBefore + selectedText + textAfter;
//
//             // Adjust the selection to cover the unwrapped text
//             textarea.setSelectionRange(start - wrapper.length, end - wrapper.length);
//         } else if (
//             (selectedText.startsWith(wrapper) && selectedText.endsWith(wrapper))
//         ) {
//             // Remove existing wrapper inside the selection
//             textarea.value = textBefore + selectedText.slice(wrapper.length, -wrapper.length) + textAfter;
//
//             // Adjust the selection to cover the unwrapped text
//             textarea.setSelectionRange(start, end - wrapper.length * 2);
//         } else {
//             // Wrap the text
//             textarea.value = textBefore + wrapper + selectedText + wrapper + textAfter;
//
//             // Adjust the selection to cover the wrapped text
//             textarea.setSelectionRange(start, end + wrapper.length * 2);
//         }
//     }
// }

function monitorTextarea(textareaId) {
    const textarea = document.getElementById(textareaId);
    let typingTimer;
    const doneTypingInterval = 1000; // Adjust this interval as needed (in milliseconds)

    if (!textarea) {
        console.error('Textarea not found. Please check the provided ID.');
        return;
    }

    textarea.addEventListener('input', function () {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(function () {
            updateHighlightedLines(textarea);
        }, doneTypingInterval);
    });
}

function updateHighlightedLines(textarea) {
    const lines = textarea.value.split('\n');
    const updatedLines = lines.map(line =>
        line.startsWith('#') ? line : `${line}`
    );

    textarea.value = updatedLines.join('\n');
}

monitorTextarea('editor');
window.onload = showMessage('Editor Loaded', 'success');
document.getElementById('page_title').addEventListener('input', debounce(updatePageName, 500));
document.getElementById('page_category').addEventListener('input', debounce(updateCategoryName, 500));