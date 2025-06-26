// DOM이 완전히 로드된 후 실행되는 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    // 메시지 입력 필드 요소 선택 (textarea로 변경)
    const messageInput = document.querySelector('textarea[placeholder="메시지 입력..."]');
    // 전송 버튼 요소 선택
    const sendButton = document.getElementById('send-btn');
    // 채팅 컨테이너 요소 선택
    const chatContainer = document.querySelector('.flex-grow.flex.flex-col.items-center.justify-center.p-6');
    // 사이드바 닫기 버튼 요소 선택
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    // 사이드바 열기 버튼 요소 선택
    const sidebarOpenBtn = document.getElementById('sidebar-open-btn');
    // 사이드바 요소 선택
    const sidebar = document.querySelector('aside');
    // 메인 컨테이너 요소 선택
    const mainContainer = document.querySelector('main');
    // 새 채팅 버튼 요소 선택
    const newChatBtn = document.getElementById('new-chat-btn');
    
    // 검색 모달 관련 요소들
    const searchBtn = document.getElementById('chat-search-btn');
    const searchModal = document.getElementById('search-modal');
    const searchModalClose = document.getElementById('search-modal-close');
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const searchLoading = document.getElementById('search-loading');
    const searchEmpty = document.getElementById('search-empty');
    
    // 사이드바 표시 상태를 추적하는 변수
    let sidebarVisible = true;
    // 현재 활성화된 세션 ID를 저장하는 변수
    let currentSessionId = null;
    // 검색 디바운스 타이머
    let searchDebounceTimer = null;
    // 검색 기록 저장(서버 저장) 디바운스 타이머
    let saveHistoryDebounceTimer = null;
    
    // URL 파라미터에서 메시지 확인 및 자동 입력
    function checkUrlMessage() {
        const urlParams = new URLSearchParams(window.location.search);
        const message = urlParams.get('message');
        if (message) {
            // 메시지 입력창에 자동 입력
            messageInput.value = decodeURIComponent(message);
            // textarea 높이 조절
            messageInput.style.height = 'auto';
            messageInput.style.height = (messageInput.scrollHeight) + 'px';
            if (messageInput.scrollHeight > 120) {
                messageInput.style.overflowY = 'auto';
                messageInput.style.height = '120px';
            } else {
                messageInput.style.overflowY = 'hidden';
            }
            // 버튼 활성화
            sendButton.disabled = false;
            sendButton.classList.remove('opacity-50', 'cursor-not-allowed');
            
            // 잠시 후 자동 전송
            setTimeout(() => {
                sendMessage();
            }, 500);
            
            // URL에서 파라미터 제거
            const newUrl = window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
        }
    }
    
    // 사이드바 닫기 버튼 클릭 이벤트 리스너
    sidebarCloseBtn.addEventListener('click', function() {
        hideSidebar();
    });

    // 사이드바 열기 버튼 클릭 이벤트 리스너
    sidebarOpenBtn.addEventListener('click', function() {
        showSidebar();
    });

    // 새 채팅 버튼 클릭 이벤트 리스너
    newChatBtn.addEventListener('click', function() {
        // 현재 세션 ID를 null로 초기화
        currentSessionId = null;
        // 채팅 세션을 초기화
        resetChatSession();
        // 세션 리스트를 다시 로드
        loadSessionList();
    });

    // 검색 모달 열기 버튼 클릭 이벤트 리스너
    searchBtn.addEventListener('click', function() {
        showSearchModal();
    });

    // 검색 모달 닫기 버튼 클릭 이벤트 리스너
    searchModalClose.addEventListener('click', function() {
        hideSearchModal();
    });

    // 모달 외부 클릭 시 모달 닫기
    searchModal.addEventListener('click', function(e) {
        if (e.target === searchModal) {
            hideSearchModal();
        }
    });

    // 검색 입력 필드 이벤트 리스너
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        // 검색 결과는 바로 보여줌
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            if (query.length >= 1) {
                performSearch(query);
            } else {
                clearSearchResults();
            }
        }, 300);

        // 검색 기록 저장은 2초 디바운스
        clearTimeout(saveHistoryDebounceTimer);
        if (query.length >= 1) {
            saveHistoryDebounceTimer = setTimeout(() => {
                saveSearchHistory(query);
            }, 2000);
        }
    });

    // textarea 자동 높이 조절 및 스크롤 처리 + 버튼 활성/비활성
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.scrollHeight > 120) {
            this.style.overflowY = 'auto';
            this.style.height = '120px';
        } else {
            this.style.overflowY = 'hidden';
        }
        // 버튼 활성/비활성 처리
        if (this.value.trim().length === 0) {
            sendButton.disabled = true;
            sendButton.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            sendButton.disabled = false;
            sendButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    });

    // 페이지 로드시 버튼 비활성화
    sendButton.disabled = true;
    sendButton.classList.add('opacity-50', 'cursor-not-allowed');

    // 사이드바를 숨기는 함수
    function hideSidebar() {
        // 사이드바를 숨김
        sidebar.style.display = 'none';
        // 메인 컨테이너의 왼쪽 마진을 0으로 설정
        mainContainer.style.marginLeft = '0';
        // 메인 컨테이너의 테두리 반경을 0으로 설정
        mainContainer.style.borderRadius = '0';
        // 사이드바 열기 버튼을 표시
        sidebarOpenBtn.style.display = 'block';
        // 사이드바 표시 상태를 false로 설정
        sidebarVisible = false;
    }

    // 사이드바를 표시하는 함수
    function showSidebar() {
        // 사이드바를 표시
        sidebar.style.display = 'flex';
        // 메인 컨테이너의 왼쪽 마진을 -1rem으로 설정
        mainContainer.style.marginLeft = '-1rem';
        // 메인 컨테이너의 테두리 반경을 설정
        mainContainer.style.borderRadius = '1rem 0 0 1rem';
        // 사이드바 열기 버튼을 숨김
        sidebarOpenBtn.style.display = 'none';
        // 사이드바 표시 상태를 true로 설정
        sidebarVisible = true;
    }

    // 채팅 세션을 초기화하는 함수
    function resetChatSession() {
        // 채팅 메시지 컨테이너 요소 선택
        const chatContainer = document.getElementById('chat-messages');
        // 채팅 컨테이너가 없으면 에러 로그 출력 후 함수 종료
        if (!chatContainer) {
            console.error('채팅 컨테이너를 찾을 수 없습니다.');
            return;
        }

        // 초기 안내 메시지와 예시 질문들을 포함한 HTML을 채팅 컨테이너에 설정
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

        // 예시 질문 버튼들에 이벤트 리스너 설정
        setupPresetButtons();
        // 메시지 입력 필드 초기화
        messageInput.value = '';

        // 서버에 새 세션 생성을 요청하는 fetch 요청
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
            // 토큰 재발급 후 재요청 처리
            if (data.status === 'token_refreshed') {
                console.log('토큰이 갱신되었습니다. 새 세션 생성을 다시 요청합니다.');
                resetChatSession(); // 재귀적으로 다시 호출
                return;
            }
            console.log('새 세션이 생성되었습니다.');
            
            // 새 세션 생성 후 사이드바 리스트 업데이트
            loadSessionList();
        })
        .catch(error => {
            console.error('세션 생성 중 오류 발생:', error);
        });
    }

    // 전송 버튼 클릭 이벤트 리스너
    sendButton.addEventListener('click', function() {
        sendMessage();
    });

    // 메시지 입력 필드에서 Enter 키 입력 이벤트 리스너
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // 기본 줄바꿈 동작 막기
            sendMessage();
        }
    });

    // 메시지를 전송하는 함수
    function sendMessage() {
        // 입력된 메시지를 가져와서 앞뒤 공백 제거
        const message = messageInput.value.trim();
        // 메시지가 비어있으면 함수 종료
        if (!message) return;

        // 첫 메시지 전송 시 안내 메시지 제거
        const chatContainer = document.getElementById('chat-messages');
        if (chatContainer.querySelector('.text-center')) {
            chatContainer.innerHTML = '';
        }

        // 사용자 메시지 먼저 출력
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        const formattedNow = `${yyyy}-${mm}-${dd} ${hh}:${min}`;
        displayMessage(message, 'user', false, formattedNow);

        // 메시지 입력 필드 초기화
        messageInput.value = '';

        // '답변을 생성중입니다...' 메시지 출력
        const loadingElement = displayMessage('답변을 생성중입니다...', 'bot', true);

        // 서버에 메시지 전송을 요청하는 fetch 요청
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
            // 401 상태 코드(인증 실패)인 경우 에러 발생
            if (response.status === 401) {
                throw new Error('Unauthorized');
            }
            return response.json();
        })
        .then(data => {
            // 로딩 요소 제거
            loadingElement.remove();

            // 리다이렉트 상태인 경우 해당 URL로 이동
            if (data.status === 'redirect') {
                window.location.href = data.redirect_url;
                return;
            }
            // 토큰 재발급 상태인 경우
            else if (data.status === 'token_refreshed') {
                // 원본 메시지를 저장
                const originalMessage = message;
                // 토큰 재발급 후 원본 메시지로 다시 요청
                // 재요청 시에도 로딩 메시지 표시
                const retryLoadingElement = displayMessage('답변을 생성중입니다...', 'bot', true);
                
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
                    // 재요청의 로딩 요소 제거
                    retryLoadingElement.remove();
                    
                    if (data.status === 'success' && data.messages) {
                        data.messages.forEach(msg => {
                            if (msg.sender === 'chatbot') {
                                displayMessage(msg.content, msg.sender, false, msg.created_at, msg.id, msg.sql_result);
                            }
                        });
                        loadSessionList();
                        if (data.session_id) {
                            currentSessionId = data.session_id;
                        }
                    } else {
                        displayMessage(data.message || '오류가 발생했습니다.', 'bot');
                    }
                })
                .catch(error => {
                    // 재요청 실패 시에도 로딩 요소 제거
                    retryLoadingElement.remove();
                    displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
                });
                return;
            }
            // 성공 상태인 경우
            else if (data.status === 'success') {
                if (data.messages) {
                    data.messages.forEach(msg => {
                        if (msg.sender === 'chatbot') {
                            displayMessage(msg.content, msg.sender, false, msg.created_at, msg.id, msg.sql_result);
                        }
                    });
                }
                loadSessionList();
                if (data.session_id) {
                    currentSessionId = data.session_id;
                }
            }
            else {
                displayMessage(data.message || '오류가 발생했습니다.', 'bot');
            }
        })
        .catch(error => {
            loadingElement.remove();
            if (error.message === 'Unauthorized') {
                window.location.href = '/user/login/';
                return;
            }
            displayMessage('네트워크 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
        });
    }

    // 메시지를 화면에 표시하는 함수
    function displayMessage(message, sender, isLoading = false, createdAt = null, messageId = null, sqlResult = null) {
        // 채팅 메시지 컨테이너 요소 선택
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) {
            console.error('채팅 컨테이너를 찾을 수 없습니다.');
            return;
        }

        // 시간 포맷을 'YYYY-MM-DD HH:MM'으로 맞추는 함수
        function formatDateTime(dt) {
            if (!dt) return '';
            // 이미 'YYYY-MM-DD HH:MM' 포맷이면 그대로 반환
            if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(dt)) return dt;
            // Date 객체로 변환 후 포맷팅
            const dateObj = new Date(dt);
            if (isNaN(dateObj.getTime())) return dt; // 변환 실패 시 원본 반환
            const yyyy = dateObj.getFullYear();
            const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
            const dd = String(dateObj.getDate()).padStart(2, '0');
            const hh = String(dateObj.getHours()).padStart(2, '0');
            const min = String(dateObj.getMinutes()).padStart(2, '0');
            return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
        }

        // 메시지 래퍼 div 요소 생성
        const wrapper = document.createElement('div');
        wrapper.className = `flex mb-4 w-full ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
        if (messageId) {
            wrapper.setAttribute('data-message-id', messageId);
        }

        // 메시지 카드 div 요소 생성
        const card = document.createElement('div');
        card.className = (sender === 'user' 
            ? 'bg-blue-100 text-blue-800' 
            : 'bg-slate-200 text-slate-800 markdown-body bg-slate-200 list-disc pl-6 mb-2') + 
            ' rounded-lg shadow p-4 break-words max-w-2xl sm:max-w-xl md:max-w-2xl lg:max-w-3xl xl:max-w-4xl';

        card.innerHTML = `
            <div class="font-semibold mb-1">
                ${
                    sender === 'user'
                    ? formatUserMessage(message)
                    : marked.parse(removeContentBetweenDashes(message))
                }
            </div>
            ${createdAt ? `<div class="text-xs text-slate-400 text-right">${formatDateTime(createdAt)}</div>` : ''}
        `;
        // sqlResult가 있고 배열인 경우 정책 카드들을 렌더링
        if (sqlResult && sqlResult.length > 0) {
            // lclsf_nm에 따라 정책들을 분류
            const housingPolicies = sqlResult.filter(policy => policy.lclsf_nm === '주거');
            const jobPolicies = sqlResult.filter(policy => policy.lclsf_nm === '일자리');
            const otherPolicies = sqlResult.filter(policy => policy.lclsf_nm !== '주거' && policy.lclsf_nm !== '일자리');
            
            // 텍스트 길이 제한 함수
            const truncateText = (text, limit = 50) => {
                if (!text) return '';
                return text.length > limit ? text.substring(0, limit) + '...' : text;
            };
            
            // 정책 카드 생성 함수
            const createPolicyCards = (policies, categoryColors) => {
                return policies.map((policy, index) => `
                    <div class="w-full md:w-1/2 lg:w-1/3 xl:w-1/4 flex-shrink-0 px-2">
                        <div class="bg-white border border-gray-200 rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow h-full cursor-pointer" 
                            onclick="openPolicyModal('${policy.plcy_no || ''}')">
                            <div class="flex flex-col h-full">
                                <h3 class="text-lg font-semibold text-gray-800 mb-2">${escapeHtml(policy.plcy_nm || '정책명 없음')}</h3>
                                <p class="text-gray-600 text-sm mb-3">${escapeHtml(truncateText(policy.plcy_expln_cn))}</p>
                                <span class="${categoryColors.bg} ${categoryColors.text} text-xs font-medium px-3 py-1 rounded-full w-fit">${escapeHtml(policy.mclsf_nm || '카테고리 없음')}</span>
                                <span class="bg-gray-100 text-gray-700 text-xs font-medium px-3 py-1 rounded-full w-fit">${escapeHtml(policy.zip_cd || '카테고리 없음')}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            };
            
            // 슬라이더 컨테이너 생성 함수
            const createSliderContainer = (policies, title, categoryColors, containerId) => {
                if (policies.length === 0) return '';
                
                const policyCards = createPolicyCards(policies, categoryColors);
                
                return `
                    <div class="mt-6">
                        <h4 class="text-lg font-semibold ${categoryColors.text} mb-3 flex items-center">
                            <span class="w-2 h-2 ${categoryColors.bg} rounded-full mr-2"></span>
                            ${title} (${policies.length}개)
                        </h4>
                        <div class="relative">
                            <div class="overflow-hidden">
                                <div class="flex transition-transform duration-500 ease-in-out" id="${containerId}">
                                    ${policyCards}
                                </div>
                            </div>
                            ${policies.length > 1 ? `
                                <button class="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100" onclick="slidePrev('${containerId}')">
                                    <span class="material-icons">chevron_left</span>
                                </button>
                                <button class="absolute right-0 top-1/2 transform -translate-y-1/2 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100" onclick="slideNext('${containerId}')">
                                    <span class="material-icons">chevron_right</span>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            };
            
            let policyContainers = '';
            
            // 주거 정책 컨테이너
            if (housingPolicies.length > 0) {
                policyContainers += createSliderContainer(
                    housingPolicies, 
                    '주거 정책', 
                    { bg: 'bg-green-100', text: 'text-green-800' },
                    `housingSlider-${messageId}`
                );
            }
            
            // 일자리 정책 컨테이너
            if (jobPolicies.length > 0) {
                policyContainers += createSliderContainer(
                    jobPolicies, 
                    '일자리 정책', 
                    { bg: 'bg-purple-100', text: 'text-purple-800' },
                    `jobSlider-${messageId}`
                );
            }
            
            
            // 기타 정책 컨테이너
            if (otherPolicies.length > 0) {
                policyContainers += createSliderContainer(
                    otherPolicies, 
                    '기타 정책', 
                    { bg: 'bg-blue-100', text: 'text-blue-800' },
                    `otherSlider-${messageId}`
                );
            }
            
            card.innerHTML += `<div class="mt-4">${policyContainers}</div>`;
        }
        
        // 래퍼에 카드 추가
        wrapper.appendChild(card);
        // 메시지 컨테이너에 래퍼 추가
        messagesContainer.appendChild(wrapper);
        // 스크롤을 맨 아래로 이동
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // 생성된 래퍼 요소 반환
        return wrapper;
    }

    // HTML 특수 문자를 이스케이프하는 함수
    function escapeHtml(text) {
        // 임시 div 요소 생성
        const div = document.createElement('div');
        // 텍스트 내용 설정 (자동으로 HTML 이스케이프됨)
        div.textContent = text;
        // 이스케이프된 HTML 반환
        return div.innerHTML;
    }

    // 예시 질문 버튼들에 이벤트 리스너를 설정하는 함수
    function setupPresetButtons() {
        // 예시 질문 버튼들을 모두 선택
        const presetButtons = document.querySelectorAll('.space-y-3 button');
        // 각 버튼에 클릭 이벤트 리스너 추가
        presetButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 버튼의 텍스트 내용을 가져와서 메시지 입력 필드에 설정
                const question = this.querySelector('span').textContent;
                messageInput.value = question;
                // 메시지 전송
                sendMessage();
            });
        });
    }

    // 세션 리스트를 불러오는 함수
    function loadSessionList() {
        console.log('세션 리스트 로드 시작');
        
        // 서버에서 세션 목록을 요청하는 fetch 요청
        fetch('/chatbot/api/sessions/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(res => {
            console.log('서버 응답 상태:', res.status);
            // 401 상태 코드(인증 실패)인 경우 로그인 페이지로 이동
            if (res.status === 401) {
                console.log('인증 실패, 로그인 페이지로 이동');
                window.location.href = '/user/login/';
                return;
            }
            // 응답이 성공적이지 않으면 에러 발생
            if (!res.ok) {
                throw new Error('세션 목록을 불러오는데 실패했습니다.');
            }
            return res.json();
        })
        .then(data => {
            console.log('받은 데이터:', data);
            // 데이터가 없으면 함수 종료
            if (!data) return;
            
            // 토큰 재발급 후 재요청 처리
            if (data.status === 'token_refreshed') {
                console.log('토큰이 갱신되었습니다. 세션 목록을 다시 요청합니다.');
                loadSessionList(); // 재귀적으로 다시 호출
                return;
            }
            
            // 세션 리스트 컨테이너 요소 선택
            const listContainer = document.getElementById('session-list');
            // 세션 리스트 컨테이너가 없으면 에러 로그 출력 후 함수 종료
            if (!listContainer) {
                console.error('세션 리스트 컨테이너를 찾을 수 없습니다.');
                return;
            }
            // 세션 리스트 컨테이너 내용 초기화
            listContainer.innerHTML = '';
            // 세션이 있고 개수가 0보다 크면
            if (data.sessions && data.sessions.length > 0) {
                console.log('세션 목록 렌더링 시작:', data.sessions);
                // 각 세션에 대해 HTML 요소 생성
                data.sessions.forEach(session => {
                    // 세션 div 요소 생성
                    const div = document.createElement('div');
                    
                    // 현재 활성화된 세션인지 확인
                    const isActiveSession = currentSessionId === session.id;
                    
                    // 현재 세션인 경우 강조 스타일 적용
                    if (isActiveSession) {
                        div.className = 'p-3 rounded-lg bg-blue-50 border-l-4 border-blue-500 cursor-pointer relative';
                        div.innerHTML = `
                            <h3 class="font-semibold text-blue-800 text-sm">${session.name}</h3>
                            <p class="text-xs text-blue-600 mt-1">${session.created_at}</p>
                        `;
                    } else {
                        div.className = 'p-3 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors';
                        div.innerHTML = `
                            <h3 class="font-semibold text-slate-800 text-sm">${session.name}</h3>
                            <p class="text-xs text-slate-400 mt-1">${session.created_at}</p>
                        `;
                    }
                    
                    // 세션 클릭 시 해당 세션의 상세 정보를 불러오는 이벤트 리스너 추가
                    div.addEventListener('click', () => loadSessionDetail(session.id));
                    // 세션 리스트 컨테이너에 세션 div 추가
                    listContainer.appendChild(div);
                });
            } else {
                console.log('세션 목록이 비어있음');
                // 세션이 없을 때 표시할 메시지
                listContainer.innerHTML = '<p class="text-center text-slate-500 text-sm py-4">대화 내역이 없습니다.</p>';
            }
        })
        .catch(error => {
            console.error('세션 목록 로드 중 오류:', error);
            // 세션 리스트 컨테이너 요소 선택
            const listContainer = document.getElementById('session-list');
            // 세션 리스트 컨테이너가 있으면 에러 메시지 표시
            if (listContainer) {
                listContainer.innerHTML = '<p class="text-center text-red-500 text-sm py-4">세션 목록을 불러오는데 실패했습니다.</p>';
            }
        });
    }

    // 세션 클릭 시 메시지를 불러오는 함수
    function loadSessionDetail(sessionId) {
        // 현재 세션 ID를 클릭된 세션 ID로 설정
        currentSessionId = sessionId;
        // 서버에서 특정 세션의 상세 정보를 요청하는 fetch 요청
        fetch(`/chatbot/api/sessions/${sessionId}/`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(res => {
            // 401 상태 코드(인증 실패)인 경우 로그인 페이지로 이동
            if (res.status === 401) {
                window.location.href = '/user/login/';
                return;
            }
            // 응답이 성공적이지 않으면 에러 발생
            if (!res.ok) {
                throw new Error('세션 상세 정보를 불러오는데 실패했습니다.');
            }
            return res.json();
        })
        .then(data => {
            // 데이터가 없으면 함수 종료
            if (!data) return;
            
            // 토큰 재발급 후 재요청 처리
            if (data.status === 'token_refreshed') {
                console.log('토큰이 갱신되었습니다. 세션 상세 정보를 다시 요청합니다.');
                loadSessionDetail(sessionId); // 재귀적으로 다시 호출
                return;
            }
            
            // 채팅 메시지 컨테이너 요소 선택
            const chatContainer = document.getElementById('chat-messages');
            // 채팅 컨테이너가 없으면 에러 로그 출력 후 함수 종료
            if (!chatContainer) {
                console.error('채팅 컨테이너를 찾을 수 없습니다.');
                return;
            }
            // 채팅 컨테이너 내용 초기화
            chatContainer.innerHTML = '';
            // 메시지가 있고 개수가 0보다 크면
            if (data.messages && data.messages.length > 0) {
                // 각 메시지를 화면에 표시
                data.messages.forEach(msg => {
                    displayMessage(msg.content, msg.sender, false, msg.created_at, msg.id, msg.sql_result);
                });
                // 스크롤을 항상 아래로 이동
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                // 메시지가 없을 때 표시할 메시지
                chatContainer.innerHTML = '<p class="text-center text-slate-500 text-sm py-4">대화 내용이 없습니다.</p>';
            }
            
            // 사이드바 세션 리스트 업데이트 (현재 세션 강조 표시)
            loadSessionList();
        })
        .catch(error => {
            console.error('세션 상세 정보 로드 중 오류:', error);
            // 채팅 메시지 컨테이너 요소 선택
            const chatContainer = document.getElementById('chat-messages');
            // 채팅 컨테이너가 있으면 에러 메시지 표시
            if (chatContainer) {
                chatContainer.innerHTML = '<p class="text-center text-red-500 text-sm py-4">대화 내용을 불러오는데 실패했습니다.</p>';
            }
        });
    }

    // 검색 모달을 표시하는 함수
    function showSearchModal() {
        searchModal.classList.remove('hidden');
        searchInput.focus();
        clearSearchResults();
    }

    // 검색 모달을 숨기는 함수
    function hideSearchModal() {
        searchModal.classList.add('hidden');
        searchInput.value = '';
        clearSearchResults();
    }

    // 검색 결과를 초기화하는 함수
    function clearSearchResults() {
        searchResults.innerHTML = '';
        searchLoading.classList.add('hidden');
        searchEmpty.classList.add('hidden');
    }

    // 검색을 수행하는 함수
    function performSearch(query) {
        clearSearchResults();
        searchLoading.classList.remove('hidden');

        // 서버에 검색 요청
        fetch('/chatbot/api/search/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => {
            if (response.status === 401) {
                throw new Error('Unauthorized');
            }
            return response.json();
        })
        .then(data => {
            searchLoading.classList.add('hidden');
            
            if (data.status === 'token_refreshed') {
                console.log('토큰이 갱신되었습니다. 검색을 다시 요청합니다.');
                performSearch(query);
                return;
            }
            
            if (data.status === 'success' && data.results && data.results.length > 0) {
                displaySearchResults(data.results);
            } else {
                searchEmpty.classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('검색 중 오류 발생:', error);
            searchLoading.classList.add('hidden');
            if (error.message === 'Unauthorized') {
                window.location.href = '/user/login/';
                return;
            }
            searchEmpty.classList.remove('hidden');
        });
    }

    // 검색 결과를 화면에 표시하는 함수
    function displaySearchResults(results) {
        searchResults.innerHTML = '';
        
        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = 'bg-slate-50 rounded-lg p-4 hover:bg-slate-100 cursor-pointer transition-colors';
            
            resultItem.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <h3 class="font-semibold text-slate-800 text-sm mb-1">${escapeHtml(result.session_name)}</h3>
                        <p class="text-xs text-slate-500 mb-2">${result.session_date}</p>
                        <div class="bg-white rounded p-3 border-l-4 border-blue-500">
                            <p class="text-sm text-slate-700 leading-relaxed">${highlightSearchTerm(result.message_content, result.search_term)}</p>
                        </div>
                    </div>
                    <span class="material-icons text-slate-400 ml-2">arrow_forward_ios</span>
                </div>
            `;
            
            resultItem.addEventListener('click', () => {
                loadSessionWithScroll(result.session_id, result.message_id);
                hideSearchModal();
            });
            
            searchResults.appendChild(resultItem);
        });
    }

    // 검색어를 하이라이트하는 함수
    function highlightSearchTerm(content, searchTerm) {
        if (!searchTerm) return escapeHtml(content);
        
        const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
        return escapeHtml(content).replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>');
    }

    // 정규식 특수 문자를 이스케이프하는 함수
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // 특정 메시지로 스크롤하여 세션을 로드하는 함수
    function loadSessionWithScroll(sessionId, messageId) {
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
            
            if (data.status === 'token_refreshed') {
                console.log('토큰이 갱신되었습니다. 세션 상세 정보를 다시 요청합니다.');
                loadSessionWithScroll(sessionId, messageId);
                return;
            }
            
            const chatContainer = document.getElementById('chat-messages');
            if (!chatContainer) {
                console.error('채팅 컨테이너를 찾을 수 없습니다.');
                return;
            }
            
            chatContainer.innerHTML = '';
            
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach((msg, index) => {
                    displayMessage(msg.content, msg.sender, false, msg.created_at, msg.id, msg.sql_result);
                });
                
                // 타겟 메시지를 찾아서 스크롤
                setTimeout(() => {
                    const targetMessageElement = document.querySelector(`[data-message-id="${messageId}"]`);
                    
                    if (targetMessageElement) {
                        targetMessageElement.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center' 
                        });
                        
                        // 하이라이트 효과 추가
                        targetMessageElement.style.backgroundColor = '#fef3c7';
                        setTimeout(() => {
                            targetMessageElement.style.backgroundColor = '';
                        }, 2000);
                    } else {
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                }, 100);
            } else {
                chatContainer.innerHTML = '<p class="text-center text-slate-500 text-sm py-4">대화 내용이 없습니다.</p>';
            }
            
            // 사이드바 세션 리스트 업데이트 (현재 세션 강조 표시)
            loadSessionList();
        })
        .catch(error => {
            console.error('세션 상세 정보 로드 중 오류:', error);
            const chatContainer = document.getElementById('chat-messages');
            if (chatContainer) {
                chatContainer.innerHTML = '<p class="text-center text-red-500 text-sm py-4">대화 내용을 불러오는데 실패했습니다.</p>';
            }
        });
    }

    // 검색 기록 저장(서버 저장) 함수
    function saveSearchHistory(query) {
        fetch('/chatbot/api/search/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ query })
        });
    }

    // 페이지 로드 시 초기화
    console.log('페이지 로드 완료, 초기화 시작');
    // 예시 질문 버튼들에 이벤트 리스너 설정
    setupPresetButtons();
    // 세션 리스트 로드
    loadSessionList();
    // 페이지 로드 시 초기 화면 표시
    resetChatSession();
    // URL 파라미터에서 메시지 확인 및 자동 입력
    checkUrlMessage();

    function formatUserMessage(text) {
        return escapeHtml(text)
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;') // 탭을 4칸 공백으로
            .replace(/  /g, '&nbsp;&nbsp;')             // 연속 공백 보존
            .replace(/\n/g, '<br>');                   // 줄바꿈
    }

    // --- 사이의 내용을 제거하는 함수
    function removeContentBetweenDashes(text) {
        if (!text) return '';
        // ---로 시작해서 다음 ---까지의 내용을 모두 제거 (각 블록을 개별적으로 처리)
        return text.replace(/---[\s\S]*?(?=---|$)/g, '').trim();
    }
});

// 슬라이더 관련 전역 함수들
let currentSlideIndex = {};

function slidePrev(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    
    if (!currentSlideIndex[sliderId]) {
        currentSlideIndex[sliderId] = 0;
    }
    
    const slides = slider.children;
    const totalSlides = slides.length;
    
    if (totalSlides <= 1) return;
    
    currentSlideIndex[sliderId] = (currentSlideIndex[sliderId] - 1 + totalSlides) % totalSlides;
    updateSliderPosition(sliderId);
}

function slideNext(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    
    if (!currentSlideIndex[sliderId]) {
        currentSlideIndex[sliderId] = 0;
    }
    
    const slides = slider.children;
    const totalSlides = slides.length;
    
    if (totalSlides <= 1) return;
    
    currentSlideIndex[sliderId] = (currentSlideIndex[sliderId] + 1) % totalSlides;
    updateSliderPosition(sliderId);
}

function updateSliderPosition(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    
    const slideWidth = slider.children[0].offsetWidth;
    const translateX = -currentSlideIndex[sliderId] * slideWidth;
    slider.style.transform = `translateX(${translateX}px)`;
}
