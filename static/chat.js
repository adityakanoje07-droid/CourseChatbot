// 1. Existing function refactored to handle both manual input and prompt clicks
async function sendMessage(customText = null) {
    // If customText is passed (from button click), use it; otherwise, read from the input box
    const inputField = document.getElementById("userInput");
    const queryText = customText ? customText.trim() : inputField.value.trim();
    
    if (!queryText) return;

    const chatBox = document.getElementById("chatBox");

    // Append User Message to Interface
    chatBox.innerHTML += `<div class="message user-msg">${queryText}</div>`;
    
    // Only clear the input field if the user actually typed something in it
    if (!customText) {
        inputField.value = "";
    }
    
    chatBox.scrollTop = chatBox.scrollHeight;

    // Append Temporary Loading State
    const loadingId = "loading-" + Date.now();
    chatBox.innerHTML += `<div class="message bot-msg" id="${loadingId}">Thinking...</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    // POST request transmitting data directly to Flask Backend endpoint
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: queryText })
        });
        const data = await response.json();
        
        // Replace loading message with actual AI Answer payload
        document.getElementById(loadingId).innerText = data.response;
    } catch (error) {
        document.getElementById(loadingId).innerText = "Error tracking service response.";
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 2. Event Listeners for your new Prompt Buttons
// This will intercept the click, extract the text, and pass it directly into sendMessage()
document.querySelectorAll('.prompt-btn').forEach(button => {
    button.addEventListener('click', () => {
        const promptText = button.textContent;
        
        // OPTION A: Automatically send it right away
        //sendMessage(promptText);
        
         
        // OPTION B: If you prefer to just fill the input box instead of sending automatically:
        // (Comment out "sendMessage(promptText);" above and uncomment the lines below)
        const inputField = document.getElementById("userInput");
        inputField.value = promptText;
        inputField.focus();
        
    });
});

// async function sendMessage() {
//     const inputField = document.getElementById("userInput");
//     const queryText = inputField.value.trim();
//     if (!queryText) return;

//     const chatBox = document.getElementById("chatBox");

//     // Append User Message to Interface
//     chatBox.innerHTML += `<div class="message user-msg">${queryText}</div>`;
//     inputField.value = "";
//     chatBox.scrollTop = chatBox.scrollHeight;

//     // Append Temporary Loading State
//     const loadingId = "loading-" + Date.now();
//     chatBox.innerHTML += `<div class="message bot-msg" id="${loadingId}">Thinking...</div>`;
//     chatBox.scrollTop = chatBox.scrollHeight;

//     // POST request transmitting data directly to Flask Backend endpoint
//     try {
//         const response = await fetch("/chat", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ message: queryText })
//         });
//         const data = await response.json();
        
//         // Replace loading message with actual AI Answer payload
//         document.getElementById(loadingId).innerText = data.response;
//     } catch (error) {
//         document.getElementById(loadingId).innerText = "Error tracking service response.";
//     }
//     chatBox.scrollTop = chatBox.scrollHeight;
// }
