document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.querySelector('input[placeholder="메시지 입력..."]');
    const sendButton = document.querySelector('.bg-blue-500');
    const chatContainer = document.querySelector('.flex-grow.flex.flex-col.items-center.justify-center.p-6');    // 사이드바 토글 기능 추가
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    const sidebarOpenBtn = document.getElementById('sidebar-open-btn');
    const sidebar = document.querySelector('aside');
    const mainContainer = document.querySelector('main');
    const newChatBtn = document.getElementById('new-chat-btn');
    
    let sidebarVisible = true;
    
    // 사이드바 닫기 버튼
    sidebarCloseBtn.addEventListener('click', function() {
        hideSidebar();
    });
    // 사이드바 열기 버튼
    sidebarOpenBtn.addEventListener('click', function() {
        showSidebar();
    });

    // 새 채팅 버튼 - 세션 초기화
    newChatBtn.addEventListener('click', function() {
        resetChatSession();
    });

    function hideSidebar() {
        sidebar.style.display = 'none';
        mainContainer.style.marginLeft = '0';
        mainContainer.style.borderRadius = '0';
        sidebarOpenBtn.style.display = 'block';
        sidebarVisible = false;
    }

    function showSidebar() {
        sidebar.style.display = 'flex';
        mainContainer.style.marginLeft = '-1rem';
        mainContainer.style.borderRadius = '1rem 0 0 1rem';
        sidebarOpenBtn.style.display = 'none';        sidebarVisible = true;
    }

    // 세션 초기화 함수
    function resetChatSession() {
        // 채팅 화면을 초기 상태로 되돌리기
        chatContainer.innerHTML = `
            <div class="text-center max-w-md">
                <h2 class="text-xl font-semibold text-slate-800 mb-4">청년 정책 문의 챗봇 입니다! 무엇을 도와드릴까요?</h2>
                <p class="text-slate-600 mb-8 text-sm">이런 질문을 자주 해요</p>
                <div class="space-y-3">
                    <button class="w-full flex items-center justify-between text-left bg-slate-50 hover:bg-slate-100 text-slate-700 py-3 px-4 rounded-lg text-sm transition-colors">
                        <span>청년 지원금 신청 방법이 궁금해요.</span>
                        <span class="material-icons text-slate-400 text-lg">arrow_forward_ios</span>
                    </button>
                    <button class="w-full flex items-center justify-between text-left bg-slate-50 hover:bg-slate-100 text-slate-700 py-3 px-4 rounded-lg text-sm transition-colors">
                        <span>청년 창업 지원 정책을 알고 싶어요.</span>
                        <span class="material-icons text-slate-400 text-lg">arrow_forward_ios</span>
                    </button>
                    <button class="w-full flex items-center justify-between text-left bg-slate-50 hover:bg-slate-100 text-slate-700 py-3 px-4 rounded-lg text-sm transition-colors">
                        <span>제가 혜택 받을 수 있는 청년정책을 찾아주세요.</span>
                        <span class="material-icons text-slate-400 text-lg">arrow_forward_ios</span>
                    </button>
                </div>
            </div>
        `;

        // 미리 정의된 질문 버튼들에 이벤트 재등록
        setupPresetButtons();

        // 입력창 초기화
        messageInput.value = '';

        // 서버에 세션 초기화 요청 (선택사항)
        fetch('/chatbot/api/reset-session/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('세션이 초기화되었습니다.');
        })
        .catch(error => {
            console.error('세션 초기화 중 오류 발생:', error);
        });
    }

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
    }    // 미리 정의된 질문 버튼들 이벤트 처리 함수
    function setupPresetButtons() {
        const presetButtons = document.querySelectorAll('.space-y-3 button');
        presetButtons.forEach(button => {
            button.addEventListener('click', function() {
                const question = this.querySelector('span').textContent;
                messageInput.value = question;
                sendMessage();
            });
        });
    }

    // 초기 로드 시 미리 정의된 질문 버튼들 이벤트 처리
    setupPresetButtons();
});