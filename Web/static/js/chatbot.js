// JavaScript for the Chatbot page

document.addEventListener('DOMContentLoaded', function() {
    const chatWindow = document.getElementById('chatWindow');
    const messageInput = document.getElementById('messageInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatBubblesArea = document.getElementById('chatBubbles');
    const initialMessage = document.getElementById('initialMessage');
    const suggestedQuestionsArea = document.getElementById('suggestedQuestions');
    const newChatBtn = document.getElementById('newChatBtn');
    const searchHistoryBtn = document.getElementById('searchHistoryBtn');
    const searchHistoryModal = new bootstrap.Modal(document.getElementById('searchHistoryModal'));
    const historySearchInput = document.getElementById('historySearchInput');
    const performHistorySearchBtn = document.getElementById('performHistorySearchBtn');
    const historySearchResults = document.getElementById('historySearchResults');
    const chatHistoryList = document.getElementById('chatHistoryList');

    // Function to add a message bubble to the chat window
    function addMessage(text, sender) {
        // Hide initial message screen when a message is sent/received
        if (initialMessage) {
            initialMessage.style.display = 'none';
        }

        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('chat-bubble', sender);

        // Basic markdown rendering (can be expanded later)
        let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold
        formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic
        formattedText = formattedText.replace(/`(.*?)`/g, '<code>$1</code>'); // Inline code
        formattedText = formattedText.replace(/\n/g, '<br>'); // Newlines

        bubbleDiv.innerHTML = formattedText;
        chatBubblesArea.appendChild(bubbleDiv);

        // Scroll to the bottom
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // 로딩 메시지 추가 함수
    function addLoadingMessage() {
        if (initialMessage) {
            initialMessage.style.display = 'none';
        }

        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('chat-bubble', 'bot', 'loading-message');
        bubbleDiv.innerHTML = '🤖 답변을 생성하고 있습니다... <div class="loading-dots"><span>.</span><span>.</span><span>.</span></div>';
        chatBubblesArea.appendChild(bubbleDiv);

        // 스크롤을 맨 아래로
        chatWindow.scrollTop = chatWindow.scrollHeight;
        
        return bubbleDiv;
    }

    // 로딩 메시지 제거 함수
    function removeLoadingMessage(loadingBubble) {
        if (loadingBubble && loadingBubble.parentNode) {
            loadingBubble.parentNode.removeChild(loadingBubble);
        }
    }

    // Send message function
    function sendMessage() {
        const messageText = messageInput.value.trim();
        if (messageText !== '') {
            addMessage(messageText, 'user');
            messageInput.value = ''; // Clear input
            adjustTextareaHeight(); // Reset height

            // 로딩 메시지 표시
            const loadingBubble = addLoadingMessage();

            // 실제 API 호출
            fetch('/chatbot/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageText
                })
            })
            .then(response => response.json())
            .then(data => {
                // 로딩 메시지 제거
                removeLoadingMessage(loadingBubble);
                
                if (data.status === 'success') {
                    // 봇 응답 추가
                    let botResponse = data.answer;
                    
                    // 관련 정책이 있다면 추가
                    // if (data.related_policies && data.related_policies.length > 0) {
                    //     botResponse += '\n\n📚 **관련 정책:**\n';
                    //     data.related_policies.forEach(policy => {
                    //         botResponse += `• ${policy}\n`;
                    //     });
                    // }
                    
                    addMessage(botResponse, 'bot');
                } else {
                    addMessage(`❌ 오류: ${data.message}`, 'bot');
                }
            })
            .catch(error => {
                // 로딩 메시지 제거
                removeLoadingMessage(loadingBubble);
                console.error('Error:', error);
                addMessage('❌ 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'bot');
            });
        }
    }

    // Event listener for send button
    sendMessageBtn.addEventListener('click', sendMessage);

    // Event listener for Enter key in textarea
    messageInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevent newline
            sendMessage();
        }
    });

    // Auto-adjust textarea height
    function adjustTextareaHeight() {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    }

    messageInput.addEventListener('input', adjustTextareaHeight);

    // Handle suggested questions click
    suggestedQuestionsArea.addEventListener('click', function(event) {
        if (event.target.classList.contains('suggested-question-btn')) {
            const question = event.target.dataset.question;
            messageInput.value = question;
            adjustTextareaHeight(); // Adjust height for the inserted text
            // Optionally, auto-send the message:
            sendMessage();
        }
    });

    // New chat button functionality
    newChatBtn.addEventListener('click', function() {
        // TODO: Implement logic to start a new chat session
        // This might involve clearing chat bubbles, resetting state, and potentially creating a new chat history entry on the backend.
        chatBubblesArea.innerHTML = ''; // Clear current messages
        if (initialMessage) {
             initialMessage.style.display = 'block'; // Show initial message again
        }
        // TODO: Load/create a new chat session ID
        console.log('New chat started (frontend only)');
    });

    // Search history button functionality (opens modal)
    searchHistoryBtn.addEventListener('click', function() {
        // TODO: Implement logic to load chat history into the modal or handle search
        searchHistoryModal.show();
        console.log('Search history modal opened');
    });

    // Perform history search button functionality (inside modal)
    performHistorySearchBtn.addEventListener('click', function() {
        const searchTerm = historySearchInput.value.trim();
        if (searchTerm !== '') {
            // TODO: Implement chat history search logic
            // This will likely involve calling a backend API and displaying results in #historySearchResults
            console.log('Searching history for:', searchTerm);
             historySearchResults.innerHTML = `<p>검색 결과 로딩 중... (${searchTerm})</p>`; // Placeholder
             // Example result display:
             /*
             historySearchResults.innerHTML = `
             <div class="list-group">
                 <a href="#" class="list-group-item list-group-item-action flex-column align-items-start">
                     <div class="d-flex w-100 justify-content-between">
                         <h6 class="mb-1">검색된 채팅 제목</h6>
                         <small>2023-01-01</small>
                     </div>
                     <p class="mb-1">검색어와 일치하는 내용 일부...</p>
                 </a>
             </div>
             `;
             */
        } else {
             historySearchResults.innerHTML = `<p>검색어를 입력해주세요.</p>`;
        }
    });

    // TODO: Implement loading and displaying chat history list on sidebar
    // This will require fetching data from the backend on page load.
    function loadChatHistory(){
        console.log('Loading chat history...');
        // Example of adding a history item (replace with fetched data):
        /*
        const historyItemHtml = `
        <li class="nav-item">
            <a href="#" class="nav-link link-dark" data-chat-id="[CHAT_ID]">
                채팅 제목 ${Date.now()}
                <div class="small">대화 요약...</div>
            </a>
        </li>
        `;
        chatHistoryList.innerHTML += historyItemHtml;
        */
    }

    // TODO: Implement loading selected chat history when a sidebar item is clicked
    chatHistoryList.addEventListener('click', function(event) {
        const targetLink = event.target.closest('.nav-link');
        if(targetLink) {
            event.preventDefault(); // Prevent default link behavior
            const chatId = targetLink.dataset.chatId;
            console.log('Loading chat:', chatId);
            // TODO: Fetch chat messages for chatId from backend and display them in #chatBubblesArea
             chatBubblesArea.innerHTML = ''; // Clear current messages
             if (initialMessage) {
                 initialMessage.style.display = 'none'; // Hide initial message
             }
             // Example of loading messages:
             // addMessage('Previous user message...', 'user');
             // addMessage('Previous bot message...', 'bot');
        }
    });

    // Initial load of chat history
    // loadChatHistory(); // Uncomment when backend is ready

    // TODO: Add sidebar toggle functionality if needed (for small screens)
});

// Basic Markdown rendering function (can be imported or kept here)
// Already included in addMessage function for now.