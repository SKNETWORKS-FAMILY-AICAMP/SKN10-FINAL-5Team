document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.querySelector('input[placeholder="메시지 입력..."]');
    const sendButton = document.querySelector('.bg-blue-500');
    const chatContainer = document.querySelector('.flex-grow.flex.flex-col.items-center.justify-center.p-6');

    // 전송 버튼 클릭 이벤트
    sendButton.addEventListener('click', function() {
        sendMessage();
    });

    // Enter 키 입력 이벤트
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // 사용자 메시지 표시
        displayMessage(message, 'user');
        messageInput.value = '';

        // 로딩 표시
        const loadingElement = displayMessage('답변을 생성중입니다...', 'bot', true);

        // API 호출
        fetch('/chatbot/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            // 로딩 메시지 제거
            loadingElement.remove();

            if (data.status === 'success') {
                // 챗봇 응답 표시
                displayMessage(data.answer, 'bot');
                
            } else {
                displayMessage(data.message || '오류가 발생했습니다.', 'bot');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingElement.remove();
            displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
        });
    }

    function displayMessage(message, sender, isLoading = false) {
        // 첫 메시지인 경우 초기 화면을 채팅 화면으로 변경
        if (chatContainer.querySelector('.text-center')) {
            chatContainer.innerHTML = '<div id="chat-messages" class="flex-grow overflow-y-auto p-4 space-y-4"></div>';
        }

        const messagesContainer = document.getElementById('chat-messages') || chatContainer;
        const messageElement = document.createElement('div');
        
        if (sender === 'user') {
            messageElement.className = 'flex justify-end';
            messageElement.innerHTML = `
                <div class="bg-blue-500 text-white p-3 rounded-lg max-w-xs lg:max-w-md">
                    ${escapeHtml(message)}
                </div>
            `;
        } else {
            messageElement.className = 'flex justify-start';
            const processedMessage = isLoading ? message : marked.parse(message);
            messageElement.innerHTML = `
                <div class="bg-slate-100 text-slate-800 p-3 rounded-lg max-w-xs lg:max-w-md prose prose-sm max-w-none ${isLoading ? 'animate-pulse' : ''}">
                    ${processedMessage}
                </div>
            `;
        }

        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageElement;
    }

    // HTML 이스케이프 함수 추가
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 미리 정의된 질문 버튼들 이벤트 처리
    const presetButtons = document.querySelectorAll('.space-y-3 button');
    presetButtons.forEach(button => {
        button.addEventListener('click', function() {
            const question = this.querySelector('span').textContent;
            messageInput.value = question;
            sendMessage();
        });
    });
});