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
    
    sidebarCloseBtn.addEventListener('click', function() {
        hideSidebar();
    });

    sidebarOpenBtn.addEventListener('click', function() {
        showSidebar();
    });

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
        sidebarOpenBtn.style.display = 'none';
        sidebarVisible = true;
    }

    function resetChatSession() {
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

        setupPresetButtons();
        messageInput.value = '';

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

        displayMessage(message, 'user');
        messageInput.value = '';

        const loadingElement = displayMessage('답변을 생성중입니다...', 'bot', true);

        fetch('/chatbot/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                message: message
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
                console.log('리다이렉트 요청 감지, 로그인 페이지로 이동합니다.');
                window.location.href = data.redirect_url;
                return;
            }
            else if (data.status === 'token_refreshed') {
                console.log('토큰 갱신 후 재요청 중...');
                const originalMessage = messageInput.value;
                setTimeout(() => {
                    messageInput.value = originalMessage;
                    sendMessage();
                }, 100);
                return;
            }
            else if (data.status === 'success') {
                displayMessage(data.answer, 'bot');
            }
            else {
                displayMessage(data.message || '오류가 발생했습니다.', 'bot');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingElement.remove();
            
            if (error.message === 'Unauthorized') {
                console.log('인증 실패, 로그인 페이지로 이동합니다.');
                window.location.href = '/user/login/';
                return;
            }
            
            displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
        });
    }

    function displayMessage(message, sender, isLoading = false) {
        if (chatContainer.querySelector('.text-center')) {
            chatContainer.innerHTML = '<div id="chat-messages" class="flex-grow overflow-y-auto p-4 space-y-4"></div>';
        }

        const messagesContainer = document.getElementById('chat-messages') || chatContainer;
        const messageElement = document.createElement('div');
        
        if (sender === 'user') {
            messageElement.className = 'flex justify-end';
            messageElement.innerHTML = `
                <div class="bg-blue-500 text-white p-3 rounded-lg max-w-xl">
                    ${escapeHtml(message)}
                </div>
            `;
        } else {
            messageElement.className = 'flex justify-center';
            const processedMessage = isLoading ? message : message;
            messageElement.innerHTML = `
                <div class="bg-slate-100 text-slate-800 p-3 rounded-lg ${isLoading ? 'animate-pulse' : ''}">
                    ${processedMessage}
                </div>
            `;
        }

        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        if (sender === 'bot' && message.includes('policy-card')) {
            setTimeout(setupPolicyCardButtons, 0);
        }
        
        return messageElement;
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

    function setupPolicyCardButtons() {
        const policyCardButtons = document.querySelectorAll('.policy-card');
        policyCardButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault();
                const policyId = this.dataset.policyId;
                displayPolicyModal(policyId);
            });
        });
    }

    function displayPolicyModal(policyId) {
        let modalContent = '';
        let title = '';
        let supportType = '';
        let applyUrl = '';

        switch(policyId) {
            case 'youth-tomorrow-success-project':
                title = '청년내일채움공제';
                supportType = '취업지원';
                modalContent = `
                    <p style="margin-bottom: 10px;">청년내일채움공제 상세 정보입니다.</p>
                    <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.6;">
                        <li style="margin-bottom: 8px;"><strong>정책 지원 내용:</strong> 중소기업 취업 청년에게 2년간 장기근속과 목돈 마련을 지원합니다.</li>
                        <li style="margin-bottom: 8px;"><strong>정책 신청 방법:</strong> 청년내일채움공제 홈페이지에서 신청</li>
                        <li style="margin-bottom: 8px;"><strong>제출 서류 내용:</strong> 근로계약서, 재직증명서 등</li>
                        <li style="margin-bottom: 8px;"><strong>신청 기간:</strong> 상시</li>
                    </ul>
                `;
                applyUrl = 'https://www.work.go.kr/youngTomorrowJob/index.do';
                break;
            case 'youth-jeonse-loan':
                title = '청년 전세임대주택';
                supportType = '주거지원';
                modalContent = `
                    <p style="margin-bottom: 10px;">청년 전세임대주택 상세 정보입니다.</p>
                    <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.6;">
                        <li style="margin-bottom: 8px;"><strong>정책 지원 내용:</strong> 만 19~39세 청년에게 시중 시세보다 저렴한 전세임대주택을 지원합니다.</li>
                        <li style="margin-bottom: 8px;"><strong>정책 신청 방법:</strong> LH 청약센터 홈페이지에서 신청</li>
                        <li style="margin-bottom: 8px;"><strong>제출 서류 내용:</strong> 주민등록등본, 가족관계증명서 등</li>
                        <li style="margin-bottom: 8px;"><strong>신청 기간:</strong> 공고에 따라 상이</li>
                    </ul>
                `;
                applyUrl = 'https://apply.lh.or.kr/';
                break;
            case 'youth-startup-academy':
                title = '청년창업사관학교';
                supportType = '창업지원';
                modalContent = `
                    <p style="margin-bottom: 10px;">유망 창업아이템 및 혁신기술을 보유한 우수 창업자를 발굴하여 성공적인 창업사업화 지원</p>
                    <ul style="list-style-type: disc; padding-left: 20px; line-height: 1.6;">
                        <li style="margin-bottom: 8px;"><strong>정책 지원 내용</strong>
                            <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px; line-height: 1.6;">
                                <li style="margin-bottom: 4px;">입교 후 창업 사업화 신청과제 사업 수행지원(정부지원금, 창업 인프라, 교육 및 코칭, 기술지원, 사업화지원, 투자지원 등)</li>
                                <li style="margin-bottom: 4px;">사업화 지원 : 입교 후 창업 사업화 신청과제 사업 수행 지원</li>
                            </ul>
                        </li>
                        <li style="margin-bottom: 8px;"><strong>정책신청방법내용</strong>
                            <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px; line-height: 1.6;">
                                <li style="margin-bottom: 4px;">K-스타트업 홈페이지(www.k-startup.go.kr)에서 온라인 접수</li>
                            </ul>
                        </li>
                        <li style="margin-bottom: 8px;"><strong>제출 서류 내용</strong>
                            <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px; line-height: 1.6;">
                                <li style="margin-bottom: 4px;">2024년 창업성공패키지 지원사업 신청서 1부</li>
                                <li style="margin-bottom: 4px;">개인 및 기업 (신용)정보 수집·이용·제공·조회 동의서 1부</li>
                            </ul>
                        </li>
                        <li style="margin-bottom: 8px;"><strong>신청 기간</strong>
                            <ul style="list-style-type: circle; padding-left: 20px; margin-top: 5px; line-height: 1.6;">
                                <li style="margin-bottom: 4px;">20240115 ~ 20240205</li>
                            </ul>
                        </li>
                    </ul>
                `;
                applyUrl = 'https://www.k-startup.go.kr/';
                break;
            default:
                title = '정책 정보';
                supportType = '';
                modalContent = '<p>선택하신 정책에 대한 정보를 찾을 수 없습니다.</p>';
                applyUrl = '#';
        }

        const modalHtml = `
            <div id="policyModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000;">
                <div style="background-color: white; padding: 30px; border-radius: 10px; max-width: 600px; width: 90%; box-shadow: 0 4px 8px rgba(0,0,0,0.2); position: relative;">
                    <button id="closeModalBtn" style="position: absolute; top: 15px; right: 15px; background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                    <h2 style="font-size: 24px; color: #333; margin-bottom: 10px;">${title}</h2>
                    ${supportType ? `<span style="background-color: #e6f7ed; color: #52c41a; padding: 5px 10px; border-radius: 4px; font-size: 12px; margin-bottom: 20px; display: inline-block;">${supportType}</span>` : ''}
                    <div style="margin-top: 20px; max-height: 400px; overflow-y: auto;">
                        ${modalContent}
                    </div>
                    <div style="text-align: right; margin-top: 20px;">
                        <button id="applyButton" style="background-color: #007bff; color: white; padding: 10px 20px; border-radius: 5px; border: none; cursor: pointer;">신청하기</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        document.getElementById('closeModalBtn').addEventListener('click', function() {
            document.getElementById('policyModal').remove();
        });

        const applyButton = document.getElementById('applyButton');
        if (applyButton) {
            console.log('신청하기 버튼 찾음:', applyButton);
            applyButton.addEventListener('click', function() {
                if (applyUrl && applyUrl !== '#') {
                    window.open(applyUrl, '_blank');
                } else {
                    console.warn('신청 URL이 정의되지 않았습니다.');
                }
                document.getElementById('policyModal').remove();
            });
        } else {
            console.error('신청하기 버튼을 찾을 수 없습니다!');
        }
    }

    setupPresetButtons();
});