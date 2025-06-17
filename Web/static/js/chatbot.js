document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.querySelector('input[placeholder="메시지 입력..."]');
    const sendButton = document.querySelector('.bg-blue-500');
    const chatContainer = document.querySelector('.flex-grow.flex.flex-col.items-center.justify-center.p-6');
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    const sidebarOpenBtn = document.getElementById('sidebar-open-btn');
    const sidebar = document.querySelector('aside');
    const mainContainer = document.querySelector('main');
    const newChatBtn = document.getElementById('new-chat-btn');
    
    let sidebarVisible = true;
    let currentSessionId = null;
    
    sidebarCloseBtn.addEventListener('click', function() {
        hideSidebar();
    });

    sidebarOpenBtn.addEventListener('click', function() {
        showSidebar();
    });

    newChatBtn.addEventListener('click', function() {
        currentSessionId = null;
        resetChatSession();
        loadSessionList();
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
        sidebarOpenBtn.style.display = 'none';
        sidebarVisible = true;
    }

    function resetChatSession() {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) {
            console.error('채팅 컨테이너를 찾을 수 없습니다.');
            return;
        }

        chatContainer.innerHTML = `
            <div class="flex-grow flex flex-col items-center justify-center p-6">
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
            </div>
        `;

        setupPresetButtons();
        messageInput.value = '';

        fetch('/chatbot/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ message: '', session_id: currentSessionId })
        })
        .then(response => response.json())
        .then(data => {
            console.log('새 세션이 생성되었습니다.');
        })
        .catch(error => {
            console.error('세션 생성 중 오류 발생:', error);
        });
    }

    sendButton.addEventListener('click', function() {
        sendMessage();
    });

    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // 첫 메시지 전송 시 안내 메시지 제거
        const chatContainer = document.getElementById('chat-messages');
        if (chatContainer.querySelector('.text-center')) {
            chatContainer.innerHTML = '';
        }

        messageInput.value = '';

        const loadingElement = displayMessage('답변을 생성중입니다...', 'bot', true);

        fetch('/chatbot/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId
            })
        })
        .then(response => {
            if (response.status === 401) {
                throw new Error('Unauthorized');
            }
            return response.json();
        })
        .then(data => {
            loadingElement.remove();
            
            if (data.status === 'redirect') {
                window.location.href = data.redirect_url;
                return;
            }
            else if (data.status === 'token_refreshed') {
                const originalMessage = message;
                fetch('/chatbot/api/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        message: originalMessage,
                        session_id: currentSessionId
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        if (data.messages) {
                            data.messages.forEach(msg => {
                                displayMessage(msg.content, msg.sender, false, msg.created_at);
                            });
                        }
                        // 세션 리스트 새로고침
                        loadSessionList();
                        // 세션이 새로 생성된 경우 session_id 갱신
                        if (data.session_id) {
                            currentSessionId = data.session_id;
                        }
                    } else {
                        displayMessage(data.message || '오류가 발생했습니다.', 'bot');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
                });
                return;
            }
            else if (data.status === 'success') {
                if (data.messages) {
                    data.messages.forEach(msg => {
                        displayMessage(msg.content, msg.sender, false, msg.created_at);
                    });
                }
                // 세션 리스트 새로고침
                loadSessionList();
                // 세션이 새로 생성된 경우 session_id 갱신
                if (data.session_id) {
                    currentSessionId = data.session_id;
                }
            }
            else {
                displayMessage(data.message || '오류가 발생했습니다.', 'bot');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingElement.remove();
            
            if (error.message === 'Unauthorized') {
                window.location.href = '/user/login/';
                return;
            }
            
            displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
        });
    }

    function displayMessage(message, sender, isLoading = false, createdAt = null) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) {
            console.error('채팅 컨테이너를 찾을 수 없습니다.');
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = `flex mb-4 w-full ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
        
        const card = document.createElement('div');
        card.className = (sender === 'user' 
            ? 'bg-blue-100 text-blue-800' 
            : 'bg-slate-100 text-slate-800') + 
            ' rounded-lg shadow p-4 max-w-xs break-words';
        
        card.innerHTML = `
            <div class="font-semibold mb-1">${sender === 'user' ? escapeHtml(message) : message}</div>
            ${createdAt ? `<div class="text-xs text-slate-400 text-right">${createdAt}</div>` : ''}
        `;
        
        wrapper.appendChild(card);
        messagesContainer.appendChild(wrapper);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return wrapper;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

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

    // 세션 리스트 불러오기
    function loadSessionList() {
        console.log('세션 리스트 로드 시작');
        
        fetch('/chatbot/api/sessions/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(res => {
            console.log('서버 응답 상태:', res.status);
            if (res.status === 401) {
                console.log('인증 실패, 로그인 페이지로 이동');
                window.location.href = '/user/login/';
                return;
            }
            if (!res.ok) {
                throw new Error('세션 목록을 불러오는데 실패했습니다.');
            }
            return res.json();
        })
        .then(data => {
            console.log('받은 데이터:', data);
            if (!data) return;
            
            const listContainer = document.getElementById('session-list');
            if (!listContainer) {
                console.error('세션 리스트 컨테이너를 찾을 수 없습니다.');
                return;
            }
            listContainer.innerHTML = '';
            if (data.sessions && data.sessions.length > 0) {
                console.log('세션 목록 렌더링 시작:', data.sessions);
                data.sessions.forEach(session => {
                    const div = document.createElement('div');
                    div.className = 'p-3 rounded-lg hover:bg-slate-50 cursor-pointer';
                    div.innerHTML = `
                        <h3 class="font-semibold text-slate-800 text-sm">${session.name}</h3>
                        <p class="text-xs text-slate-400 mt-1">${session.created_at}</p>
                    `;
                    div.addEventListener('click', () => loadSessionDetail(session.id));
                    listContainer.appendChild(div);
                });
            } else {
                console.log('세션 목록이 비어있음');
                listContainer.innerHTML = '<p class="text-center text-slate-500 text-sm py-4">대화 내역이 없습니다.</p>';
            }
        })
        .catch(error => {
            console.error('세션 목록 로드 중 오류:', error);
            const listContainer = document.getElementById('session-list');
            if (listContainer) {
                listContainer.innerHTML = '<p class="text-center text-red-500 text-sm py-4">세션 목록을 불러오는데 실패했습니다.</p>';
            }
        });
    }

    // 세션 클릭 시 메시지 불러오기
    function loadSessionDetail(sessionId) {
        currentSessionId = sessionId;
        fetch(`/chatbot/api/sessions/${sessionId}/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(res => {
            if (res.status === 401) {
                window.location.href = '/user/login/';
                return;
            }
            if (!res.ok) {
                throw new Error('세션 상세 정보를 불러오는데 실패했습니다.');
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;
            
            const chatContainer = document.getElementById('chat-messages');
            if (!chatContainer) {
                console.error('채팅 컨테이너를 찾을 수 없습니다.');
                return;
            }
            chatContainer.innerHTML = '';
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    displayMessage(msg.content, msg.sender, false, msg.created_at);
                });
                // 스크롤을 항상 아래로
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                chatContainer.innerHTML = '<p class="text-center text-slate-500 text-sm py-4">대화 내용이 없습니다.</p>';
            }
        })
        .catch(error => {
            console.error('세션 상세 정보 로드 중 오류:', error);
            const chatContainer = document.getElementById('chat-messages');
            if (chatContainer) {
                chatContainer.innerHTML = '<p class="text-center text-red-500 text-sm py-4">대화 내용을 불러오는데 실패했습니다.</p>';
            }
        });
    }

    // 페이지 로드 시 초기화
    console.log('페이지 로드 완료, 초기화 시작');
    setupPresetButtons();
    loadSessionList();
    resetChatSession(); // 페이지 로드 시 초기 화면 표시
});